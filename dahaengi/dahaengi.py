"""다행이 데스크톱 펫.

작업 표시줄 위를 걸어다니는 도트 다람쥐.
- 왼쪽 드래그: 들어서 옮기기 / 왼쪽 클릭: 깡충
- 오른쪽 클릭: 알람 설정 (최대 5개), 종료
- 알람 시간이 되면 말풍선으로 설정한 말을 해 준다.
"""

import datetime
import json
import math
import os
import random
import sys
import traceback
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desktop  # noqa: E402
import sprites  # noqa: E402

KEY = "#ff00fe"          # 투명 처리용 색
TICK_MS = 50
MAX_ALARMS = 5
BUBBLE_SECONDS = 60      # 알람 말풍선 자동 닫힘
DEFAULT_MESSAGE = "알람 시간이에요!"
TEXT = sprites.OUT
SUBTEXT = "#9a7b62"

CONFIG_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Dahaengi")
CONFIG_PATH = os.path.join(CONFIG_DIR, "alarms.json")


# ---------------------------------------------------------------- 환경 유틸

def set_dpi_awareness():
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def work_area(root):
    """작업 표시줄을 뺀 화면 영역 (left, top, right, bottom)."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
                return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            pass
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight() - 40


def beep(root):
    if sys.platform == "win32":
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            return
        except Exception:
            pass
    root.bell()


def make_transparent(win):
    win.configure(bg=KEY)
    try:
        win.attributes("-transparentcolor", KEY)
    except tk.TclError:
        pass  # Windows 외 환경에서는 지원 안 됨


# ---------------------------------------------------------------- 알람 저장

def default_alarms():
    alarms = [{"enabled": False, "hour": 9, "minute": 0, "message": "", "daily": True}
              for _ in range(MAX_ALARMS)]
    alarms[0].update(hour=12, minute=0, message="점심 먹을 시간이에요! 맛있게 드세요")
    alarms[1].update(hour=18, minute=0, message="오늘 하루도 수고했어요. 퇴근해요!")
    return alarms


def load_alarms():
    alarms = default_alarms()
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        for i, a in enumerate(saved[:MAX_ALARMS]):
            alarms[i] = {
                "enabled": bool(a.get("enabled", False)),
                "hour": int(a.get("hour", 9)) % 24,
                "minute": int(a.get("minute", 0)) % 60,
                "message": str(a.get("message", "")),
                "daily": bool(a.get("daily", True)),
            }
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return alarms


def save_alarms(alarms):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(alarms, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- 말풍선

class Bubble:
    """도트 스타일 말풍선. 여러 개가 겹치면 차례로 보여준다."""

    def __init__(self, app):
        self.app = app
        self.win = None
        self.queue = []
        self.after_id = None
        self.tail_x = 0
        self.size = (0, 0)

    @property
    def showing(self):
        return self.win is not None

    def say(self, text, title=None, seconds=6, alarm=False):
        self.queue.append((text, title, seconds, alarm))
        if not self.showing:
            self._next()

    def dismiss(self, _event=None):
        if self.after_id:
            self.app.root.after_cancel(self.after_id)
            self.after_id = None
        if self.win:
            self.win.destroy()
            self.win = None
        self._next()

    def _next(self):
        if not self.queue:
            self.app.on_bubble_done()
            return
        text, title, seconds, alarm = self.queue.pop(0)
        self._build(text, title)
        if alarm:
            self.app.celebrate(seconds)
            beep(self.app.root)
        self.after_id = self.app.root.after(seconds * 1000, self.dismiss)

    def _build(self, text, title):
        app = self.app
        p = app.scale
        win = tk.Toplevel(app.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        make_transparent(win)
        cv = tk.Canvas(win, bg=KEY, highlightthickness=0, bd=0)
        cv.pack()

        body_font = (app.font_family, 11, "bold")
        title_font = (app.font_family, 9)
        maxw = int(260 * app.ui)

        def measure(t, f):
            item = cv.create_text(0, 0, text=t, font=f, width=maxw, anchor="nw", justify="center")
            x0, y0, x1, y1 = cv.bbox(item)
            cv.delete(item)
            return x1 - x0, y1 - y0

        tw, th = measure(text, body_font)
        hw, hh = measure(title, title_font) if title else (0, 0)
        gap = p if title else 0
        pad = 4 * p

        def snap(v):
            return int(math.ceil(v / p) * p)

        bw = snap(max(tw, hw, 10 * p) + 2 * pad)
        bh = snap(th + hh + gap + 2 * pad)
        self.size = (bw, bh)

        # 말풍선 꼬리가 다행이 머리를 가리키도록
        left, _, right, _ = app.area
        cx = app.head_x()
        bx = min(max(cx - bw // 2, left), right - bw)
        c = snap(cx - bx - p / 2)
        self.tail_x = min(max(c, 3 * p), bw - 4 * p)

        def rounded(x0, y0, x1, y1, color):
            cv.create_rectangle(x0 + 2 * p, y0, x1 - 2 * p, y1, fill=color, width=0)
            cv.create_rectangle(x0 + p, y0 + p, x1 - p, y1 - p, fill=color, width=0)
            cv.create_rectangle(x0, y0 + 2 * p, x1, y1 - 2 * p, fill=color, width=0)

        def px(x0, x1, row, color):
            cv.create_rectangle(x0, bh + row * p, x1, bh + (row + 1) * p, fill=color, width=0)

        rounded(0, 0, bw, bh, TEXT)
        rounded(p, p, bw - p, bh - p, sprites.WHITE)
        t = self.tail_x
        px(t - p, t + 2 * p, -1, sprites.WHITE)
        px(t - 2 * p, t - p, 0, TEXT)
        px(t - p, t + 2 * p, 0, sprites.WHITE)
        px(t + 2 * p, t + 3 * p, 0, TEXT)
        px(t - p, t, 1, TEXT)
        px(t, t + p, 1, sprites.WHITE)
        px(t + p, t + 2 * p, 1, TEXT)
        px(t, t + p, 2, TEXT)

        y = pad
        if title:
            cv.create_text(bw // 2, y, text=title, font=title_font, fill=SUBTEXT,
                           width=maxw, anchor="n", justify="center")
            y += hh + gap
        cv.create_text(bw // 2, y, text=text, font=body_font, fill=TEXT,
                       width=maxw, anchor="n", justify="center")

        cv.configure(width=bw, height=bh + 3 * p)
        cv.bind("<Button-1>", self.dismiss)
        self.win = win
        self.follow()

    def follow(self):
        if not self.win:
            return
        app = self.app
        p = app.scale
        bw, bh = self.size
        left, top, right, _ = app.area
        bx = int(app.head_x() - self.tail_x - p / 2)
        bx = min(max(bx, left), right - bw)
        by = int(app.y + 2 * p - (bh + 3 * p))
        by = max(by, top)
        self.win.geometry(f"+{bx}+{by}")


# ---------------------------------------------------------------- 알람 설정 창

class AlarmDialog:
    def __init__(self, app):
        self.app = app
        top = self.top = tk.Toplevel(app.root)
        top.title("다행이 알람 설정")
        top.attributes("-topmost", True)
        top.resizable(False, False)
        top.protocol("WM_DELETE_WINDOW", self.close)

        frm = ttk.Frame(top, padding=14)
        frm.grid()
        ttk.Label(frm, text=f"알람은 최대 {MAX_ALARMS}개까지 설정할 수 있어요.\n"
                            "시간이 되면 다행이가 말풍선으로 알려줘요.",
                  justify="left").grid(row=0, column=0, columnspan=8, sticky="w", pady=(0, 10))

        for col, name in enumerate(("사용", "시", "", "분", "할 말", "매일 반복", "")):
            ttk.Label(frm, text=name).grid(row=1, column=col, padx=3, sticky="w")

        self.rows = []
        for i, a in enumerate(app.alarms):
            r = i + 2
            v = {
                "enabled": tk.BooleanVar(value=a["enabled"]),
                "hour": tk.StringVar(value=f"{a['hour']:02d}"),
                "minute": tk.StringVar(value=f"{a['minute']:02d}"),
                "message": tk.StringVar(value=a["message"]),
                "daily": tk.BooleanVar(value=a["daily"]),
            }
            ttk.Checkbutton(frm, variable=v["enabled"]).grid(row=r, column=0, padx=3, pady=3)
            ttk.Spinbox(frm, from_=0, to=23, width=3, wrap=True, format="%02.0f",
                        textvariable=v["hour"]).grid(row=r, column=1, padx=2)
            ttk.Label(frm, text=":").grid(row=r, column=2)
            ttk.Spinbox(frm, from_=0, to=59, width=3, wrap=True, format="%02.0f",
                        textvariable=v["minute"]).grid(row=r, column=3, padx=2)
            ttk.Entry(frm, width=32, textvariable=v["message"]).grid(row=r, column=4, padx=3)
            ttk.Checkbutton(frm, variable=v["daily"]).grid(row=r, column=5)
            ttk.Button(frm, text="미리보기", width=8,
                       command=lambda v=v: self.preview(v)).grid(row=r, column=6, padx=3)
            self.rows.append(v)

        btns = ttk.Frame(frm)
        btns.grid(row=MAX_ALARMS + 2, column=0, columnspan=8, sticky="e", pady=(12, 0))
        ttk.Button(btns, text="저장", command=self.save).grid(row=0, column=0, padx=4)
        ttk.Button(btns, text="취소", command=self.close).grid(row=0, column=1)

        top.update_idletasks()
        x = (top.winfo_screenwidth() - top.winfo_width()) // 2
        y = (top.winfo_screenheight() - top.winfo_height()) // 3
        top.geometry(f"+{x}+{y}")
        top.focus_force()

    def _parse(self, v, i):
        try:
            hour = int(v["hour"].get())
            minute = int(v["minute"].get())
        except ValueError:
            hour = minute = -1
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            messagebox.showwarning("다행이", f"{i + 1}번 알람의 시간을 확인해 주세요.\n"
                                            "(시: 0~23, 분: 0~59)", parent=self.top)
            return None
        return {
            "enabled": v["enabled"].get(),
            "hour": hour,
            "minute": minute,
            "message": v["message"].get().strip(),
            "daily": v["daily"].get(),
        }

    def preview(self, v):
        a = self._parse(v, self.rows.index(v))
        if a:
            self.app.ring(a, preview=True)

    def save(self):
        alarms = []
        for i, v in enumerate(self.rows):
            a = self._parse(v, i)
            if a is None:
                return
            alarms.append(a)
        self.app.alarms = alarms
        try:
            save_alarms(alarms)
        except OSError as e:
            messagebox.showerror("다행이", f"알람을 저장하지 못했어요.\n{e}", parent=self.top)
            return
        self.close()
        on = [a for a in alarms if a["enabled"]]
        self.app.bubble.say(f"알람 {len(on)}개를 기억했어요!" if on else "알람을 모두 껐어요.",
                            seconds=3)

    def close(self):
        self.top.destroy()
        self.app.dialog = None


# ---------------------------------------------------------------- 다행이

class Dahaengi:
    def __init__(self):
        set_dpi_awareness()
        self.root = root = tk.Tk()
        root.title("다행이")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        make_transparent(root)

        self.ui = root.winfo_fpixels("1i") / 96
        self.scale = max(2, round(3 * self.ui))
        families = set(tkfont.families(root))
        self.font_family = next((f for f in ("Malgun Gothic", "맑은 고딕", "Apple SD Gothic Neo",
                                             "NanumGothic", "Noto Sans CJK KR") if f in families),
                                "TkDefaultFont")

        self.images = self._load_images()
        root.iconphoto(True, self.images[("idle", 1)][0])
        self.w = sprites.W * self.scale
        self.h = sprites.H * self.scale
        self.label = tk.Label(root, bg=KEY, bd=0, highlightthickness=0)
        self.label.pack()

        self.area = work_area(root)
        self.surface = None       # 서 있는 창 (None이면 작업 표시줄)
        self.surface_rect = None
        left, _, right, _ = self.area
        self.x = random.randint(left, max(left, right - self.w))
        self.y = self.ground()
        self.dir = random.choice((1, -1))
        self.speed = self.scale * 0.5
        self.state = "walk"
        self.timer = 0
        self.vy = 0.0
        self.air_face = "happy"
        self.stay = tk.BooleanVar(value=False)
        self.t = 0
        self.press = None
        self.dragging = False

        self.alarms = load_alarms()
        self.fired = {}
        self.dialog = None
        self.bubble = Bubble(self)

        for widget in (self.label,):
            widget.bind("<ButtonPress-1>", self.on_press)
            widget.bind("<B1-Motion>", self.on_motion)
            widget.bind("<ButtonRelease-1>", self.on_release)
            widget.bind("<Button-3>", self.on_menu)

        self.render()
        root.after(TICK_MS, self.tick)
        root.after(1000, self.check_alarms)
        root.after(600, lambda: self.bubble.say(
            "안녕하세요! 다행이에요.\n오른쪽 클릭으로 알람을 맞춰 보세요.", seconds=5))

    # -- 그래픽

    def _photo(self, frame):
        img = tk.PhotoImage(width=sprites.W, height=sprites.H)
        for y, row in enumerate(frame):
            x = 0
            while x < sprites.W:
                c = row[x]
                if c is None:
                    x += 1
                    continue
                x2 = x
                while x2 < sprites.W and row[x2] == c:
                    x2 += 1
                img.put(c, to=(x, y, x2, y + 1))
                x = x2
        return img.zoom(self.scale)

    def _load_images(self):
        images = {}
        for name, frames in sprites.make_frames().items():
            images[(name, 1)] = [self._photo(f) for f in frames]
            images[(name, -1)] = [self._photo(sprites.flip(f)) for f in frames]
        return images

    def ground(self):
        if self.surface_rect:
            return self.surface_rect[1] - self.h
        return self.area[3] - self.h

    def foot_x(self):
        return self.x + 22 * self.scale

    def x_bounds(self):
        left, _, right, _ = self.area
        lo, hi = left, right - self.w
        if self.surface_rect:  # 발이 창 윗변 위에 있는 동안만
            l, _, r, _ = self.surface_rect
            m = 22 * self.scale
            lo = max(lo, l - m + 4 * self.scale)
            hi = min(hi, r - m - 4 * self.scale)
        return lo, hi

    def fits(self, rect):
        """창 윗변에 다행이가 올라설 공간이 있는지 (최대화/전체화면 창은 제외)."""
        l, t, r, _ = rect
        return (t - self.h >= self.area[1] and t < self.area[3]
                and r - l >= 16 * self.scale)

    def head_x(self):
        return self.x + (24 if self.dir == 1 else 20) * self.scale

    def render(self):
        st = self.state
        dy = 0
        if st == "walk":
            name, i = "walk", (self.t // 3) % 4
        elif st == "idle":
            name, i = "idle", 1 if self.t % 60 in (0, 1, 2) else 0
        elif st == "happy":
            name, i = "happy", (self.t // 5) % 2
            if i == 0:
                dy = -3 * self.scale
        elif st == "air":
            name, i = self.air_face, (self.t // 4) % 2
        else:  # drag
            name, i = "drag", (self.t // 4) % 2
        self.label.configure(image=self.images[(name, self.dir)][i])
        self.root.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y + dy)}")
        self.bubble.follow()

    # -- 행동

    def set_idle(self, ticks=None):
        self.state = "idle"
        self.timer = ticks if ticks is not None else random.randint(40, 120)

    def tick(self):
        self.t += 1
        st = self.state

        if st in ("walk", "idle", "happy") and self.surface:
            self.check_surface()
            st = self.state

        if st == "walk":
            if self.stay.get():
                self.set_idle()
            else:
                lo, hi = self.x_bounds()
                self.x += self.dir * self.speed
                if self.x <= lo:
                    self.x, self.dir = lo, 1
                elif self.x >= hi:
                    self.x, self.dir = hi, -1
                if random.random() < 0.004:
                    self.set_idle()
        elif st == "idle":
            self.timer -= 1
            if self.timer <= 0 and not self.stay.get():
                self.state = "walk"
                if random.random() < 0.5:
                    self.dir = -self.dir
        elif st == "air":
            prev_bottom = self.y + self.h
            self.vy += self.scale * 0.35
            self.y += self.vy
            hit = self.find_landing(prev_bottom, self.y + self.h) if self.vy > 0 else None
            if hit:
                self.surface, self.surface_rect = hit
            if hit or self.y >= self.ground():
                self.y, self.vy = self.ground(), 0.0
                self.set_idle(random.randint(20, 60))
        elif st == "happy":
            self.timer -= 1
            if self.timer <= 0:
                self.set_idle()

        if self.t % 100 == 0:  # 화면/작업 표시줄 변화 반영, 항상 위 유지
            self.area = work_area(self.root)
            if self.state in ("walk", "idle", "happy"):
                self.y = self.ground()
            self.root.attributes("-topmost", True)
            self.root.lift()

        self.render()
        self.root.after(TICK_MS, self.tick)

    def fall(self, face="drag"):
        self.surface = self.surface_rect = None
        self.state, self.vy, self.air_face = "air", 0.0, face

    def find_landing(self, y0, y1):
        """이번 틱에 발이 지나간 [y0, y1] 사이에 있는 창 윗변 중 가장 위의 것."""
        fx = self.foot_x()
        m = 4 * self.scale
        wins = desktop.list_windows()
        best = None
        for hwnd, r in wins:
            l, t, rr, _ = r
            if (y0 <= t <= y1 and l + m <= fx <= rr - m and self.fits(r)
                    and (best is None or t < best[1][1])
                    and desktop.visible_at(wins, hwnd, fx, t + 3)):
                best = (hwnd, r)
        return best

    def check_surface(self):
        """서 있는 창을 따라가고, 창이 사라지거나 가려지면 떨어진다."""
        if self.t % 2 == 0:
            r = desktop.window_rect(self.surface)
            if r is None or not self.fits(r):
                self.fall()
                return
            old = self.surface_rect
            if r != old:
                if r[2] - r[0] == old[2] - old[0]:  # 창을 옮기면 같이 이동
                    self.x += r[0] - old[0]
                self.surface_rect = r
                self.y = self.ground()
                lo, hi = self.x_bounds()
                if hi < lo:
                    self.fall()
                    return
                self.x = min(max(self.x, lo), hi)
        if self.t % 10 == 5:
            wins = desktop.list_windows()
            if not desktop.visible_at(wins, self.surface, self.foot_x(), self.surface_rect[1] + 3):
                self.fall()

    def celebrate(self, seconds):
        if self.state in ("drag", "air"):
            return
        self.y = self.ground()
        self.state = "happy"
        self.timer = seconds * 1000 // TICK_MS

    def on_bubble_done(self):
        if self.state == "happy":
            self.set_idle()

    # -- 마우스

    def on_press(self, e):
        self.press = (e.x_root, e.y_root, self.x, self.y)
        self.dragging = False

    def on_motion(self, e):
        if not self.press:
            return
        px, py, sx, sy = self.press
        dx, dy = e.x_root - px, e.y_root - py
        if not self.dragging and abs(dx) + abs(dy) > 4:
            self.dragging = True
            self.state = "drag"
            self.surface = self.surface_rect = None
        if self.dragging:
            left, top, right, _ = self.area
            self.x = min(max(sx + dx, left), right - self.w)
            self.y = min(max(sy + dy, top), self.ground())

    def on_release(self, _e):
        if self.dragging:
            self.fall()
        elif self.bubble.showing:
            self.bubble.dismiss()
        elif self.state in ("walk", "idle"):
            self.fall("happy")
            self.vy = -self.scale * 2.4
        self.press = None
        self.dragging = False

    def on_menu(self, e):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="알람 설정...", command=self.open_dialog)
        menu.add_separator()
        on = [a for a in self.alarms if a["enabled"]]
        if on:
            for a in sorted(on, key=lambda a: (a["hour"], a["minute"])):
                msg = a["message"] or DEFAULT_MESSAGE
                if len(msg) > 18:
                    msg = msg[:18] + "…"
                repeat = "매일" if a["daily"] else "한 번"
                menu.add_command(label=f"{a['hour']:02d}:{a['minute']:02d} ({repeat})  {msg}",
                                 state="disabled")
        else:
            menu.add_command(label="켜진 알람이 없어요", state="disabled")
        menu.add_separator()
        menu.add_checkbutton(label="가만히 있기", variable=self.stay)
        menu.add_command(label="종료", command=self.quit)
        try:
            menu.tk_popup(e.x_root, e.y_root)
        finally:
            menu.grab_release()

    def open_dialog(self):
        if self.dialog and self.dialog.top.winfo_exists():
            self.dialog.top.lift()
            self.dialog.top.focus_force()
            return
        self.dialog = AlarmDialog(self)

    def quit(self):
        self.root.destroy()

    # -- 알람

    def ring(self, alarm, preview=False):
        title = f"{alarm['hour']:02d}:{alarm['minute']:02d} 알람"
        if preview:
            title += " (미리보기)"
        self.bubble.say(alarm["message"] or DEFAULT_MESSAGE, title=title,
                        seconds=5 if preview else BUBBLE_SECONDS, alarm=True)

    def check_alarms(self):
        now = datetime.datetime.now()
        stamp = now.strftime("%Y-%m-%d %H:%M")
        changed = False
        for i, a in enumerate(self.alarms):
            if (a["enabled"] and a["hour"] == now.hour and a["minute"] == now.minute
                    and self.fired.get(i) != stamp):
                self.fired[i] = stamp
                self.ring(a)
                if not a["daily"]:
                    a["enabled"] = False
                    changed = True
        if changed:
            try:
                save_alarms(self.alarms)
            except OSError:
                pass
        self.root.after(1000, self.check_alarms)

    def run(self):
        self.root.mainloop()


def selftest(log_path):
    """빌드 확인용: 창, 말풍선, 설정 창을 띄우고, 열린 창이 있으면 그 위에 떨어뜨려 본다.
    오류가 있으면 종료 코드 1."""
    errors, notes = [], []
    app = Dahaengi()
    root = app.root
    root.report_callback_exception = lambda *exc: errors.append("".join(traceback.format_exception(*exc)))
    root.after(1500, app.bubble.dismiss)
    root.after(1600, lambda: app.ring({"hour": 12, "minute": 0, "daily": True,
                                       "message": "점심 먹을 시간이에요! 맛있게 드세요"}, preview=True))
    root.after(2000, app.open_dialog)

    def start_window_test():
        wins = desktop.list_windows()
        notes.append(f"windows: {[desktop.window_class(h) for h, _ in wins]}")
        target = next((h for h, _ in wins if desktop.window_class(h) == "Notepad"), None)
        if target is None:
            notes.append("window test skipped (no Notepad window)")
            return
        desktop.place_window(target, 300, 400, 700, 400)
        root.after(500, lambda: drop(target))

    def drop(target):
        r = desktop.window_rect(target)
        notes.append(f"target rect: {r}")
        app.x = (r[0] + r[2]) // 2 - 22 * app.scale
        app.y = 50
        app.fall()
        root.after(3000, lambda: check_landed(target))

    def check_landed(target):
        if app.surface != target or int(app.y) != app.surface_rect[1] - app.h:
            errors.append(f"did not land on window: surface={app.surface} y={app.y} state={app.state}")
            return
        notes.append("landed on window")
        desktop.place_window(target, 420, 520, 700, 400)
        root.after(1000, lambda: check_follow(target))

    def check_follow(target):
        r = app.surface_rect
        if app.surface != target or r[1] < 500 or int(app.y) != r[1] - app.h:
            errors.append(f"did not follow window: surface={app.surface} rect={r} y={app.y}")
            return
        notes.append("followed moved window")
        desktop.minimize(target)
        root.after(2000, check_fell)

    def check_fell():
        if app.surface is not None or int(app.y) != app.area[3] - app.h:
            errors.append(f"did not fall after minimize: surface={app.surface} y={app.y}")
            return
        notes.append("fell to taskbar after minimize")

    root.after(2500, start_window_test)
    root.after(12000, app.quit)
    app.run()
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(notes + errors + ([] if errors else ["ok"])))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--selftest":
        selftest(sys.argv[2])
    else:
        Dahaengi().run()
