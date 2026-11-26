"""Windows mouse and physical-key output backed by SendInput."""

import ctypes
from ctypes import wintypes
import sys

MOVE = 0x0001
BUTTONS = {"left": (0x0002, 0x0004), "right": (0x0008, 0x0010)}
WHEEL = 0x0800
ESCAPE = 0x1B
KEY_SCAN = 0x0008
KEY_UP = 0x0002
KEY_EXTENDED = 0x0001
KEY_HOLD = 0.045
KEYS = {key: first + index for first, row in
        ((0x02, "1234567890"), (0x10, "QWERTYUIOP"), (0x1E, "ASDFGHJKL"), (0x2C, "ZXCVBNM"))
        for index, key in enumerate(row)}
KEYS.update({"Space": 0x39, "Enter": 0x1C, "Tab": 0x0F, "Backspace": 0x0E,
             "Left": 0xE04B, "Right": 0xE04D, "Up": 0xE048, "Down": 0xE050,
             "Insert": 0xE052, "Delete": 0xE053, "Home": 0xE047, "End": 0xE04F,
             "Page Up": 0xE049, "Page Down": 0xE051, "Ctrl": 0x1D, "Shift": 0x2A, "Alt": 0x38,
             "-": 0x0C, "=": 0x0D, "[": 0x1A, "]": 0x1B, "\\": 0x2B, ";": 0x27, "'": 0x28,
             ",": 0x33, ".": 0x34, "/": 0x35, "`": 0x29, "F11": 0x57, "F12": 0x58})
KEYS.update({f"F{i}": 0x3A + i for i in range(1, 11)})


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD), ("time", wintypes.DWORD), ("extraInfo", ctypes.c_size_t),
    ]


class KeyboardInput(ctypes.Structure):
    _fields_ = [("vk", wintypes.WORD), ("scan", wintypes.WORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("extraInfo", ctypes.c_size_t)]


class InputPayload(ctypes.Union):
    _fields_ = [("mouse", MouseInput), ("keyboard", KeyboardInput)]


class Input(ctypes.Structure):
    _anonymous_ = ("payload",)
    _fields_ = [("type", wintypes.DWORD), ("payload", InputPayload)]


class WindowsMouse:
    def __init__(self):
        self.api = None
        if sys.platform == "win32":
            self.api = ctypes.WinDLL("user32", use_last_error=True)
            self.api.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int)
            self.api.SendInput.restype = wintypes.UINT
            self.api.GetAsyncKeyState.argtypes = (ctypes.c_int,)
            self.api.GetAsyncKeyState.restype = ctypes.c_short
        self.held = {}
        self.reset()

    def reset(self):
        self.x = self.y = 0.0

    def escape_pressed(self):
        return bool(self.api and self.api.GetAsyncKeyState(ESCAPE) & 0x8000)

    def apply(self, action):
        self.x += action.dx
        self.y += action.dy
        dx, dy = int(self.x), int(self.y)
        self.x -= dx
        self.y -= dy
        events = []
        if dx or dy:
            events.append(Input(0, InputPayload(mouse=MouseInput(dx, dy, 0, MOVE))))
        if action.wheel:
            events.append(Input(0, InputPayload(mouse=MouseInput(0, 0, (120 * action.wheel) & 0xFFFFFFFF, WHEEL))))
        if action.click:
            events.extend(Input(0, InputPayload(mouse=MouseInput(0, 0, 0, flag))) for flag in BUTTONS[action.click])
        if not events:
            return
        batch = (Input * len(events))(*events)
        sent = self.api.SendInput(len(events), batch, ctypes.sizeof(Input))
        if sent != len(events):
            if action.click and sent == len(events) - 1:
                self.api.SendInput(1, ctypes.byref(events[-1]), ctypes.sizeof(Input))
            raise OSError("Windows отклонила команду мыши")

    def _key_event(self, key, *, release=False):
        scan = KEYS[key]
        flags = KEY_SCAN | (KEY_EXTENDED if scan > 0xFF else 0) | (KEY_UP if release else 0)
        event = Input(1, InputPayload(keyboard=KeyboardInput(0, scan & 0xFF, flags)))
        if self.api.SendInput(1, ctypes.byref(event), ctypes.sizeof(Input)) != 1:
            raise OSError(f"Windows отклонила клавишу {key}")

    def tap(self, key, now):
        if key in self.held:
            self.release(key)
        self._key_event(key)
        self.held[key] = now + KEY_HOLD

    def release(self, key):
        self._key_event(key, release=True)
        self.held.pop(key)

    def flush_keys(self, now=None):
        error = None
        for key, until in tuple(self.held.items()):
            if now is None or now >= until:
                try:
                    self.release(key)
                except OSError as exc:
                    error = exc
        if error is not None:
            raise error
