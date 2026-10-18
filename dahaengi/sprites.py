"""다행이 도트 스프라이트 생성기.

이미지 파일 없이 코드로 픽셀 아트를 그린다.
각 프레임은 H x W 2차원 리스트이며 값은 '#rrggbb' 색상 문자열 또는 None(투명).
"""

W, H = 44, 36

# 팔레트 (따뜻하고 부드러운 감성 톤)
OUT = "#3b2a20"      # 외곽선 (순수 검정 대신 짙은 갈색)
FUR = "#f6ca62"      # 기본 털색
FUR_LIGHT = "#fde39a"
FUR_SHADE = "#e3a94a"
STRIPE = "#7b4a2a"   # 갈색 줄무늬
STRIPE_DARK = "#5e3720"
EYE = "#2a1c14"
WHITE = "#ffffff"
NOSE = "#6a3d24"
BLUSH = "#f4a08c"
MOUTH_IN = "#c8574a"
BADGE_RED = "#d8263c"
BADGE_BLUE = "#1f3f7a"
STRING = "#4a6fa5"


def _ellipse(cx, cy, rx, ry):
    pts = set()
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            dx = (x + 0.5 - cx) / rx
            dy = (y + 0.5 - cy) / ry
            if dx * dx + dy * dy <= 1.0:
                pts.add((x, y))
    return pts


class _Canvas:
    def __init__(self):
        self.px = [[None] * W for _ in range(H)]

    def set(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.px[y][x] = c

    def part(self, mask, fill):
        """mask 영역을 칠하고 가장자리는 외곽선으로. fill은 색 또는 (x, y)->색 함수."""
        for (x, y) in mask:
            edge = any((x + dx, y + dy) not in mask
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge:
                self.set(x, y, OUT)
            else:
                self.set(x, y, fill(x, y) if callable(fill) else fill)


def _shaded(cx, cy, rx, ry):
    def f(x, y):
        dx = (x + 0.5 - cx) / rx
        dy = (y + 0.5 - cy) / ry
        if dy > 0.55 or (dy > 0.25 and abs(dx) > 0.75):
            return FUR_SHADE
        if dy < -0.45 and dx < -0.25 and dx * dx + dy * dy < 0.72:
            return FUR_LIGHT
        return FUR
    return f


def build(eyes="open", mouth="w", lift=(0, 0), bob=0, tail_dx=0, arms="down"):
    """오른쪽을 바라보는 프레임 하나를 만든다."""
    c = _Canvas()
    o = -bob  # 상체 y 오프셋

    # 꼬리 (가장 뒤)
    tcx, tcy, trx, try_ = 10 + tail_dx, 20 + o, 8.5, 9.5
    tail_shade = _shaded(tcx, tcy, trx, try_)

    def tail_fill(x, y):
        dx = (x + 0.5 - tcx) / trx
        dy = (y + 0.5 - tcy) / try_
        if dx * dx + dy * dy > 0.5 and dy < -0.2 and dx < 0.35:
            return STRIPE
        return tail_shade(x, y)
    c.part(_ellipse(tcx, tcy, trx, try_), tail_fill)

    # 귀
    for ex in (13.5, 34.5):
        ear = _ellipse(ex, 5.5 + o, 3.6, 4.2)
        c.part(ear, FUR)
        for y in range(int(4 + o), int(8 + o)):
            c.set(int(ex), y, FUR_SHADE)

    # 다리 (지면 고정, 걸을 때 들림)
    for i, lx in enumerate((21, 28)):
        c.part(_ellipse(lx, 33.6 - lift[i], 2.4, 2.6), FUR_SHADE)

    # 몸통
    bcx, bcy = 24.5, 29 + o
    c.part(_ellipse(bcx, bcy, 6.8, 5.2), _shaded(bcx, bcy, 6.8, 5.2))

    # 팔
    if arms == "up":
        arm_pos = ((16, 25 + o), (33, 25 + o))
    else:
        arm_pos = ((17.5, 28 + o), (31.5, 28 + o))
    for ax, ay in arm_pos:
        c.part(_ellipse(ax, ay, 2.8, 2.4), FUR)

    # 목걸이 사원증
    c.set(21, int(26 + o), STRING)
    c.set(22, int(27 + o), STRING)
    c.set(27, int(26 + o), STRING)
    c.set(26, int(27 + o), STRING)
    for y in range(28, 33):
        for x in range(22, 27):
            edge = x in (22, 26) or y in (28, 32)
            c.set(x, int(y + o), OUT if edge else WHITE)
    c.set(24, int(29 + o), BADGE_RED)
    c.set(24, int(30 + o), BADGE_BLUE)
    c.set(23, int(30 + o), BADGE_BLUE)
    c.set(25, int(29 + o), BADGE_RED)

    # 머리 (가장 앞)
    hcx, hcy, hrx, hry = 24, 14.5 + o, 15.6, 11.2
    c.part(_ellipse(hcx, hcy, hrx, hry), _shaded(hcx, hcy, hrx, hry))

    # 머리 줄무늬
    for sx, length in ((19, 4), (24, 6), (29, 4)):
        for y in range(4, 4 + length):
            yy = int(y + o)
            if c.px[yy][sx] not in (None, OUT):
                c.set(sx, yy, STRIPE)
            if c.px[yy][sx + 1] not in (None, OUT):
                c.set(sx + 1, yy, STRIPE_DARK if y == 3 + length else STRIPE)

    # 얼굴 (진행 방향으로 살짝 치우침)
    fx = 1
    ey = int(12 + o)
    for exl in (19 + fx, 28 + fx):
        if eyes == "open":
            for yy in range(ey, ey + 3):
                c.set(exl, yy, EYE)
                c.set(exl + 1, yy, EYE)
            c.set(exl, ey, WHITE)
        elif eyes == "blink":
            c.set(exl, ey + 2, EYE)
            c.set(exl + 1, ey + 2, EYE)
        elif eyes == "happy":  # ^ ^
            c.set(exl - 1, ey + 2, EYE)
            c.set(exl, ey + 1, EYE)
            c.set(exl + 1, ey + 1, EYE)
            c.set(exl + 2, ey + 2, EYE)
        elif eyes == "wide":  # 놀란 눈
            for yy in range(ey - 1, ey + 3):
                c.set(exl, yy, EYE)
                c.set(exl + 1, yy, EYE)
            c.set(exl, ey - 1, WHITE)
            c.set(exl + 1, ey + 1, WHITE)

    # 볼터치
    by = int(15 + o)
    for bx in (16 + fx, 17 + fx, 31 + fx, 32 + fx):
        c.set(bx, by, BLUSH)

    # 코
    ny = int(14 + o)
    c.set(23 + fx, ny, NOSE)
    c.set(24 + fx, ny, NOSE)

    # 입
    my = ny + 1
    if mouth == "w":
        for (x, y) in ((21, 0), (22, 1), (23, 0), (24, 0), (25, 1), (26, 0)):
            c.set(x + fx, my + y, EYE)
    elif mouth == "open":
        for (x, y) in ((22, 0), (23, 1), (24, 1), (25, 0)):
            c.set(x + fx, my + y, EYE)
        c.set(23 + fx, my, MOUTH_IN)
        c.set(24 + fx, my, MOUTH_IN)
    elif mouth == "o":
        c.set(23 + fx, my, EYE)
        c.set(24 + fx, my, EYE)
        c.set(23 + fx, my + 1, EYE)
        c.set(24 + fx, my + 1, EYE)

    return c.px


def flip(frame):
    return [list(reversed(row)) for row in frame]


def make_frames():
    """{동작: [프레임...]} (오른쪽 방향 기준)"""
    return {
        "walk": [
            build(lift=(0, 0), bob=0, tail_dx=0),
            build(lift=(0, 1), bob=1, tail_dx=-1),
            build(lift=(0, 0), bob=0, tail_dx=0),
            build(lift=(1, 0), bob=1, tail_dx=1),
        ],
        "idle": [build(), build(eyes="blink")],
        "happy": [
            build(eyes="happy", mouth="open", arms="up", bob=1),
            build(eyes="happy", mouth="open", arms="down", tail_dx=1),
        ],
        "drag": [
            build(eyes="wide", mouth="o", lift=(1, 1), tail_dx=-1),
            build(eyes="wide", mouth="o", lift=(1, 1), tail_dx=1),
        ],
    }
