"""바탕화면에 열린 창 정보 (다행이가 창 위를 걸을 수 있도록).

Windows 전용. 다른 OS에서는 창 목록이 비어 있어 작업 표시줄 위만 걷는다.
좌표는 모두 화면 픽셀 기준 (left, top, right, bottom).
"""

import os
import sys


def visible_at(windows, hwnd, x, y):
    """windows(위에 있는 창부터)에서 hwnd 창의 (x, y) 지점이 다른 창에 가려지지 않았는지."""
    for h, (l, t, r, b) in windows:
        if h == hwnd:
            return True
        if l <= x < r and t <= y < b:
            return False
    return False


if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi

    GWL_EXSTYLE = -20
    WS_EX_TRANSPARENT = 0x20
    WS_EX_TOOLWINDOW = 0x80
    WS_EX_LAYERED = 0x80000
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    DWMWA_CLOAKED = 14
    SWP_NOACTIVATE = 0x10
    SW_MINIMIZE = 6
    IGNORED_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}
    _PID = os.getpid()

    _EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [_EnumProc, wintypes.LPARAM]
    for _name in ("IsWindow", "IsWindowVisible", "IsIconic", "GetWindowTextLengthW"):
        getattr(user32, _name).argtypes = [wintypes.HWND]
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                             ctypes.c_void_p, wintypes.DWORD]

    def window_class(hwnd):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        return buf.value

    def _rect(hwnd):
        # 그림자/투명 테두리를 뺀 실제로 보이는 창 영역
        r = wintypes.RECT()
        if dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS,
                                        ctypes.byref(r), ctypes.sizeof(r)) != 0:
            if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
                return None
        if r.right <= r.left or r.bottom <= r.top:
            return None
        return (r.left, r.top, r.right, r.bottom)

    def _usable(hwnd):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return False
        if user32.GetWindowTextLengthW(hwnd) == 0:
            return False
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if ex & WS_EX_TOOLWINDOW or (ex & WS_EX_LAYERED and ex & WS_EX_TRANSPARENT):
            return False
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == _PID:
            return False
        if window_class(hwnd) in IGNORED_CLASSES:
            return False
        cloaked = wintypes.DWORD()  # 다른 가상 데스크톱 / 숨겨진 앱 창
        if dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED,
                                        ctypes.byref(cloaked), ctypes.sizeof(cloaked)) == 0:
            if cloaked.value:
                return False
        return True

    def list_windows():
        """보이는 일반 창 [(hwnd, rect)], 화면 맨 위에 있는 창부터."""
        out = []

        def cb(hwnd, _lparam):
            try:
                if _usable(hwnd):
                    r = _rect(hwnd)
                    if r:
                        out.append((hwnd, r))
            except Exception:
                pass
            return True

        user32.EnumWindows(_EnumProc(cb), 0)
        return out

    def window_rect(hwnd):
        """창이 아직 보이면 rect, 닫혔거나 최소화/숨김이면 None."""
        if not user32.IsWindow(hwnd) or not _usable(hwnd):
            return None
        return _rect(hwnd)

    def place_window(hwnd, left, top, width, height):
        user32.SetWindowPos(hwnd, None, left, top, width, height, SWP_NOACTIVATE)

    def minimize(hwnd):
        user32.ShowWindow(hwnd, SW_MINIMIZE)

else:
    def window_class(hwnd):
        return ""

    def list_windows():
        return []

    def window_rect(hwnd):
        return None

    def place_window(hwnd, left, top, width, height):
        pass

    def minimize(hwnd):
        pass
