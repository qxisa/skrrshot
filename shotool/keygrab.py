import ctypes
import ctypes.util
import re

import gi

gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib

from .hotkey import normalize

SHIFT, LOCK, CONTROL, MOD1, MOD2, MOD4 = 1, 2, 4, 8, 16, 64
MASKS = {"shift": SHIFT, "ctrl": CONTROL, "alt": MOD1, "super": MOD4}
LOCKS = (0, LOCK, MOD2, LOCK | MOD2)
KEY_PRESS = 2

ERROR_HANDLER = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)


class XEvent(ctypes.Union):
    _fields_ = [("type", ctypes.c_int), ("pad", ctypes.c_long * 24)]


class KeyGrabber:
    def __init__(self, callback):
        self.callback = callback
        self.failed = False
        self.keycode = 0
        self.mask = 0
        self.handler = ERROR_HANDLER(self.on_error)

        x = ctypes.CDLL(ctypes.util.find_library("X11") or "libX11.so.6")
        void, integer, uint, ulong = ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_ulong
        x.XOpenDisplay.restype, x.XOpenDisplay.argtypes = void, [ctypes.c_char_p]
        x.XDefaultRootWindow.restype, x.XDefaultRootWindow.argtypes = ulong, [void]
        x.XKeysymToKeycode.restype, x.XKeysymToKeycode.argtypes = integer, [void, ulong]
        x.XGrabKey.argtypes = [void, integer, uint, ulong, integer, integer, integer]
        x.XUngrabKey.argtypes = [void, integer, uint, ulong]
        x.XConnectionNumber.argtypes = [void]
        x.XPending.argtypes = [void]
        x.XNextEvent.argtypes = [void, void]
        x.XSync.argtypes = [void, integer]
        x.XSetErrorHandler.restype, x.XSetErrorHandler.argtypes = void, [void]
        self.x = x

        self.display = x.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("cannot open the X display")
        self.root = x.XDefaultRootWindow(self.display)
        GLib.io_add_watch(x.XConnectionNumber(self.display), GLib.IO_IN, self.on_ready)

    def on_error(self, _display, _event):
        self.failed = True
        return 0

    def on_ready(self, *_args):
        event = XEvent()
        while self.x.XPending(self.display):
            self.x.XNextEvent(self.display, ctypes.byref(event))
            if event.type == KEY_PRESS:
                self.callback()
        return True

    def unbind(self):
        if self.keycode:
            for lock in LOCKS:
                self.x.XUngrabKey(self.display, self.keycode, self.mask | lock, self.root)
            self.x.XSync(self.display, 0)
        self.keycode = self.mask = 0

    def bind(self, accel):
        self.unbind()
        mods, _ = normalize(accel)
        name = re.sub(r"<\w+>", "", accel)
        keysym = Gdk.keyval_from_name(name)
        keycode = self.x.XKeysymToKeycode(self.display, keysym) if keysym else 0
        if not keycode:
            return False
        mask = sum(MASKS.get(m, 0) for m in mods)

        self.failed = False
        previous = self.x.XSetErrorHandler(ctypes.cast(self.handler, ctypes.c_void_p))
        for lock in LOCKS:
            self.x.XGrabKey(self.display, keycode, mask | lock, self.root, 1, 1, 1)
        self.x.XSync(self.display, 0)
        self.x.XSetErrorHandler(previous)

        self.keycode, self.mask = keycode, mask
        if self.failed:
            self.unbind()
            return False
        return True
