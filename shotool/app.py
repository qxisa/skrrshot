import os
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk

from . import config
from .batch import Batch
from .hotkey import pretty
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
        self.note = None
        self.card = None
        self.shot = None
        self.grabber = None
        self.batch = Batch()

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

    def batch_size(self):
        return len(self.batch)

    def notify(self, text):
        if self.note:
            self.note.close()
        self.note = Toast(text)
        self.note.show()

    def card_closed(self, window):
        if self.card is window:
            self.card = None
        self.busy = False

    def open_card(self, card):
        from .cards import CardWindow

        if self.card:
            self.card.close()
        self.card = CardWindow(self, card)
        self.card.show_all()

    def capture(self):
        if self.busy:
            return
        self.busy = True
        if self.note:
            self.note.close()
            self.note = None
        if self.card:
            self.card.close()
            self.busy = True
        GLib.timeout_add(SETTLE_MS, self.begin)

    def begin(self):
        try:
            self.shot = Shot()
        except Exception as error:
            print(f"shotool: {error}", file=sys.stderr)
            self.busy = False
            return False
        Overlay(self.shot, self.on_selected, len(self.batch)).open()
        return False

    def on_selected(self, result):
        shot, self.shot = self.shot, None
        if result == "batch":
            from .cards import batch_card

            self.busy = False
            self.open_card(batch_card(self))
        elif result:
            from .cards import capture_card

            pixbuf = shot.crop(result)
            self.copy(pixbuf)
            self.busy = False
            self.open_card(capture_card(self, pixbuf))
        else:
            self.busy = False

    def copy(self, pixbuf):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_image(pixbuf)
        clipboard.store()

    def act(self, name, payload):
        self.busy = True
        try:
            getattr(self, f"act_{name}")(payload)
        except Exception as error:
            self.notify(f"Could not finish: {error}")
        finally:
            self.busy = False

    def folder(self):
        saved = config.get("save_dir")
        if saved and os.path.isdir(saved):
            return saved
        return GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) or os.path.expanduser("~")

    def ask(self, action, name=None):
        saving = action == Gtk.FileChooserAction.SAVE
        dialog = Gtk.FileChooserNative.new("Save screenshot" if saving else "Choose a folder",
                                           None, action, "Save" if saving else "Select", "Cancel")
        dialog.set_current_folder(self.folder())
        if saving:
            dialog.set_do_overwrite_confirmation(True)
            dialog.set_current_name(name)
        accepted = dialog.run() == Gtk.ResponseType.ACCEPT
        path = dialog.get_filename() if accepted else None
        dialog.destroy()
        return path

    def settings(self):
        from . import export

        fmt = config.get("format", "png")
        return (fmt if fmt in export.formats() else "png"), config.get("quality", 85)

    def act_save(self, pixbuf):
        from . import export

        fmt, quality = self.settings()
        path = self.ask(Gtk.FileChooserAction.SAVE, export.filename("shot", fmt))
        if not path:
            return
        path = export.with_ext(path, fmt)
        data = export.encode(pixbuf, fmt, quality)
        with open(path, "wb") as handle:
            handle.write(data)
        config.put(save_dir=os.path.dirname(path))
        self.notify(f"Saved  {os.path.basename(path)}  {export.human(len(data))}")

    def act_batch(self, pixbuf):
        if not self.batch.add(pixbuf):
            self.notify("Batch is full")
            return
        self.notify(f"Added to batch ({len(self.batch)})   {pretty(config.hotkey())} for more")

    def act_save_batch(self, _payload):
        from . import export

        fmt, quality = self.settings()
        if fmt == "pdf":
            path = self.ask(Gtk.FileChooserAction.SAVE, export.filename("shots", "pdf"))
            if not path:
                return
            path = export.with_ext(path, "pdf")
            data = export.encode_pdf(self.batch.pixbufs())
            with open(path, "wb") as handle:
                handle.write(data)
            config.put(save_dir=os.path.dirname(path))
            self.notify(f"Saved  {os.path.basename(path)}  {export.human(len(data))}")
        else:
            folder = self.ask(Gtk.FileChooserAction.SELECT_FOLDER)
            if not folder:
                return
            total = count = 0
            for pixbuf in self.batch.pixbufs():
                count += 1
                path = export.unique(os.path.join(folder, export.filename("shot", fmt, count)))
                data = export.encode(pixbuf, fmt, quality)
                with open(path, "wb") as handle:
                    handle.write(data)
                total += len(data)
            config.put(save_dir=folder)
            self.notify(f"Saved {count} files to {os.path.basename(folder)}  {export.human(total)}")
        self.batch.clear()

    def act_discard(self, _payload):
        self.batch.clear()
        self.notify("Batch discarded")


def run(argv):
    return Shotool().run(argv)
