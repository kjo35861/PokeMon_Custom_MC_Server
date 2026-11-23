"""Windows capture geometry and focus-checked scan-code Space input."""
import ctypes
from ctypes import wintypes as wt
import time

user32 = ctypes.WinDLL('user32', use_last_error=True)
try:
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except (AttributeError, OSError):
    user32.SetProcessDPIAware()

user32.GetForegroundWindow.restype = wt.HWND
user32.IsWindow.argtypes = [wt.HWND]
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetClientRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.ClientToScreen.argtypes = [wt.HWND, ctypes.POINTER(wt.POINT)]
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = wt.SHORT
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowThreadProcessId.restype = wt.DWORD


def title(hwnd):
    text = ctypes.create_unicode_buffer(user32.GetWindowTextLengthW(hwnd)+1)
    user32.GetWindowTextW(hwnd, text, len(text))
    return text.value


def client_rect(hwnd):
    rect, point = wt.RECT(), wt.POINT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise OSError('게임 창의 크기를 읽을 수 없습니다.')
    if not user32.ClientToScreen(hwnd, ctypes.byref(point)):
        raise OSError('게임 창의 위치를 읽을 수 없습니다.')
    return (point.x, point.y, rect.right, rect.bottom)


def minecraft_windows():
    found = []
    callback_type = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def visit(hwnd, _):
        name = title(hwnd)
        if user32.IsWindowVisible(hwnd) and 'minecraft' in name.lower():
            found.append((hwnd, name))
        return True
    callback = callback_type(visit)
    user32.EnumWindows(callback, 0)
    return found


def foreground_is(hwnd):
    return bool(hwnd and user32.IsWindow(hwnd)
                and user32.GetForegroundWindow() == hwnd
                and 'minecraft' in title(hwnd).lower())


def process_id(hwnd):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def focused_game(hwnd, pid):
    """Follow a recreated GLFW window only within the originally bound game."""
    current = user32.GetForegroundWindow()
    if foreground_is(current) and (current == hwnd or process_id(current) == pid):
        return current
    return None


def key_down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', wt.WORD), ('wScan', wt.WORD), ('dwFlags', wt.DWORD),
                ('time', wt.DWORD), ('dwExtraInfo', ctypes.c_size_t)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', wt.LONG), ('dy', wt.LONG), ('mouseData', wt.DWORD),
                ('dwFlags', wt.DWORD), ('time', wt.DWORD),
                ('dwExtraInfo', ctypes.c_size_t)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [('uMsg', wt.DWORD), ('wParamL', wt.WORD), ('wParamH', wt.WORD)]


class INPUT_UNION(ctypes.Union):
    _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT), ('hi', HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ('value',)
    _fields_ = [('type', wt.DWORD), ('value', INPUT_UNION)]


user32.SendInput.argtypes = [wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wt.UINT


def _space(up=False):
    event = INPUT(type=1)
    event.ki = KEYBDINPUT(0, 0x39, 0x0008 | (0x0002 if up else 0), 0, 0)
    return event


def tap_space(hwnd, duration=.010, on_down=None):
    # Do not steal focus or post input into a background app.
    if not foreground_is(hwnd) or key_down(0x20):
        return False
    down, up = _space(), _space(True)
    if user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT)) != 1:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if on_down is not None:
            on_down(time.perf_counter())
        time.sleep(duration)
    finally:
        if user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT)) != 1:
            raise ctypes.WinError(ctypes.get_last_error())
    return True
