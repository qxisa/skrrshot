import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk

from . import config
from .keygrab import KeyGrabber
from .overlay import Overlay
from .screen import Shot
from .toast import Toast

APP_ID = "io.github.shotool.Shotool"
SETTLE_MS = 120


class Shotool(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.busy = False
        self.toast = None
        self.shot = None
        self.grabber = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.hold()
        self.grabber = KeyGrabber(self.capture)
        self.bind_hotkey()

    def do_command_line(self, cmdline):
        args = cmdline.get_arguments()[1:]
        if "--quit" in args:
            self.quit()
        elif "--reload" in args:
            return 0 if self.bind_hotkey() else 1
        elif "--daemon" not in args:
            self.capture()
        return 0

    def bind_hotkey(self):
        accel = config.hotkey()
        if self.grabber.bind(accel):
            return True
        print(f"shotool: could not grab {accel}, it may be in use", file=sys.stderr)
        return False

    def capture(self):
        if self.busy:
            return
        self.busy = True
        if self.toast:
            self.toast.close()
            self.toast = None
        GLib.timeout_add(SETTLE_MS, self.begin)

    def begin(self):
        try:
            self.shot = Shot()
        except Exception as error:
            print(f"shotool: {error}", file=sys.stderr)
            self.busy = False
            return False
        Overlay(self.shot, self.on_selected).open()
        return False

    def on_selected(self, rect):
        if rect:
            pixbuf = self.shot.crop(rect)
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_image(pixbuf)
            clipboard.store()
            self.toast = Toast(f"Copied to clipboard   {pixbuf.get_width()} \u00d7 {pixbuf.get_height()}")
            self.toast.show()
        self.shot = None
        self.busy = False


def run(argv):
    return Shotool().run(argv)
