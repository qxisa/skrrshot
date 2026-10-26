import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from .draw import draw_text, rounded_rect

ITEMS = [("region", "Region"), ("window", "Window"), ("full", "Full screen")]
ITEM_W, ITEM_H, PAD, GAP, HINT_H = 104, 84, 10, 6, 22
MIN_DRAG = 5
HINT = "Enter to pick   |   drag to select   |   Esc to cancel"


def make_blur(shot, factor=14):
    w = max(1, shot.width // factor)
    h = max(1, shot.height // factor)
    small = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
    cr = cairo.Context(small)
    cr.scale(w / shot.width, h / shot.height)
    cr.set_source_surface(shot.surface, 0, 0)
    cr.get_source().set_filter(cairo.FILTER_BEST)
    cr.paint()
    return small


def glyph_region(cr, cx, cy):
    cr.set_dash([4, 3])
    cr.rectangle(cx - 14, cy - 10, 28, 20)
    cr.stroke()
    cr.set_dash([])


def glyph_window(cr, cx, cy):
    cr.rectangle(cx - 14, cy - 10, 28, 20)
    cr.stroke()
    cr.move_to(cx - 14, cy - 4)
    cr.line_to(cx + 14, cy - 4)
    cr.stroke()


def glyph_full(cr, cx, cy):
    cr.rectangle(cx - 16, cy - 11, 32, 22)
    cr.stroke()
    rounded_rect(cr, cx - 11, cy - 6, 22, 12, 2)
    cr.stroke()


def glyph_batch(cr, cx, cy):
    cr.rectangle(cx - 6, cy - 11, 22, 16)
    cr.stroke()
    cr.rectangle(cx - 16, cy - 5, 22, 16)
    cr.stroke()


GLYPHS = {"region": glyph_region, "window": glyph_window, "full": glyph_full, "batch": glyph_batch}


class Overlay(Gtk.Window):
    def __init__(self, shot, on_done, batch_count=0):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.shot = shot
        self.on_done = on_done
        self.blur = make_blur(shot)
        self.items = [i for i in ITEMS if i[0] != "window" or shot.active_rect]
        if batch_count:
            self.items.append(("batch", f"Batch ({batch_count})"))
        self.index = 0
        self.menu_visible = True
        self.menu_dismissed = False
        self.start = None
        self.sel = None
        self.finished = False
        self.tries = 0
        self.cursor_name = None

        self.menu_rect = self.compute_menu_rect()

        self.set_app_paintable(True)
        self.set_can_focus(True)
        self.set_default_size(shot.width, shot.height)
        self.move(0, 0)
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.KEY_PRESS_MASK
        )
        self.connect("draw", self.on_draw)
        self.connect("key-press-event", self.on_key)
        self.connect("button-press-event", self.on_press)
        self.connect("button-release-event", self.on_release)
        self.connect("motion-notify-event", self.on_motion)
        self.connect("realize", lambda _w: self.set_cursor("crosshair"))

    def open(self):
        self.show_all()
        GLib.timeout_add(30, self.start_grab)

    def compute_menu_rect(self):
        seat = Gdk.Display.get_default().get_default_seat()
        _, px, py = seat.get_pointer().get_position()
        n = len(self.items)
        w = PAD * 2 + n * ITEM_W + (n - 1) * GAP
        h = PAD * 2 + ITEM_H + HINT_H
        x = min(max(px - w // 2, 8), self.shot.width - w - 8)
        y = py + 24
        if y + h > self.shot.height - 8:
            y = py - 24 - h
        return (x, max(y, 8), w, h)

    def item_rect(self, i):
        mx, my, _, _ = self.menu_rect
        return (mx + PAD + i * (ITEM_W + GAP), my + PAD, ITEM_W, ITEM_H)

    def item_at(self, x, y):
        for i in range(len(self.items)):
            ix, iy, iw, ih = self.item_rect(i)
            if ix <= x <= ix + iw and iy <= y <= iy + ih:
                return i
        return None

    def set_cursor(self, name):
        if name == self.cursor_name or self.get_window() is None:
            return
        self.cursor_name = name
        self.get_window().set_cursor(Gdk.Cursor.new_from_name(self.get_display(), name))

    def start_grab(self):
        seat = self.get_display().get_default_seat()
        status = seat.grab(self.get_window(), Gdk.SeatCapabilities.ALL, False, None, None, None, None)
        self.tries += 1
        if status == Gdk.GrabStatus.SUCCESS:
            return False
        if self.tries >= 50:
            self.finish(None)
            return False
        return True

    def finish(self, rect):
        if self.finished:
            return
        self.finished = True
        self.get_display().get_default_seat().ungrab()
        self.destroy()
        GLib.idle_add(self.on_done, rect)

    def choose(self, i):
        kind = self.items[i][0]
        if kind == "region":
            self.menu_visible = False
            self.menu_dismissed = True
            self.set_cursor("crosshair")
            self.queue_draw()
        elif kind == "batch":
            self.finish("batch")
        elif kind == "window":
            self.finish(self.shot.active_rect)
        else:
            self.finish((0, 0, self.shot.width, self.shot.height))

    def on_key(self, _widget, event):
        key = event.keyval
        if key == Gdk.KEY_Escape:
            self.finish(None)
        elif not self.menu_visible or self.start:
            return True
        elif key in (Gdk.KEY_Left, Gdk.KEY_Up):
            self.index = (self.index - 1) % len(self.items)
        elif key in (Gdk.KEY_Right, Gdk.KEY_Down, Gdk.KEY_Tab):
            self.index = (self.index + 1) % len(self.items)
        elif key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            self.choose(self.index)
        elif Gdk.KEY_1 <= key <= Gdk.KEY_9 and key - Gdk.KEY_1 < len(self.items):
            self.choose(key - Gdk.KEY_1)
        self.queue_draw()
        return True

    def on_press(self, _widget, event):
        if event.button == 3:
            self.finish(None)
        elif event.button == 1:
            hit = self.item_at(event.x, event.y) if self.menu_visible else None
            if hit is not None:
                self.choose(hit)
            else:
                self.start = (event.x, event.y)
                self.menu_visible = False
        return True

    def on_motion(self, _widget, event):
        if self.start:
            x0, y0 = self.start
            self.sel = (int(min(x0, event.x)), int(min(y0, event.y)),
                        int(abs(event.x - x0)), int(abs(event.y - y0)))
        elif self.menu_visible:
            hit = self.item_at(event.x, event.y)
            if hit is not None:
                self.index = hit
            self.set_cursor("default" if hit is not None else "crosshair")
        self.queue_draw()
        return True

    def on_release(self, _widget, event):
        if event.button != 1 or not self.start:
            return True
        self.start = None
        sel = self.sel
        if sel and sel[2] >= MIN_DRAG and sel[3] >= MIN_DRAG:
            self.finish(sel)
        else:
            self.sel = None
            self.menu_visible = not self.menu_dismissed
            self.queue_draw()
        return True

    def on_draw(self, _widget, cr):
        cr.set_source_surface(self.shot.surface, 0, 0)
        cr.paint()
        cr.set_source_rgba(0, 0, 0, 0.5 if self.sel else 0.3)
        cr.paint()
        if self.sel:
            self.draw_selection(cr)
        elif self.menu_visible:
            self.draw_menu(cr)
        return True

    def draw_selection(self, cr):
        x, y, w, h = self.sel
        cr.save()
        cr.rectangle(x, y, w, h)
        cr.clip()
        cr.set_source_surface(self.shot.surface, 0, 0)
        cr.paint()
        cr.restore()

        cr.set_source_rgba(1, 1, 1, 0.9)
        cr.set_line_width(1)
        cr.rectangle(x + 0.5, y + 0.5, w - 1, h - 1)
        cr.stroke()

        scale = self.shot.scale
        label = f"{w * scale} x {h * scale}"
        chip_w, chip_h = len(label) * 7 + 16, 22
        cy = y - chip_h - 6 if y > chip_h + 10 else y + 6
        rounded_rect(cr, x, cy, chip_w, chip_h, 8)
        cr.set_source_rgba(0.06, 0.06, 0.08, 0.7)
        cr.fill()
        draw_text(cr, label, x + 8, cy + 15, 12, 0.95)

    def draw_menu(self, cr):
        mx, my, mw, mh = self.menu_rect
        cr.save()
        rounded_rect(cr, mx, my, mw, mh, 18)
        cr.clip()
        cr.save()
        cr.scale(self.shot.width / self.blur.get_width(), self.shot.height / self.blur.get_height())
        cr.set_source_surface(self.blur, 0, 0)
        cr.get_source().set_filter(cairo.FILTER_BILINEAR)
        cr.paint()
        cr.restore()
        cr.set_source_rgba(0, 0, 0, 0.38)
        cr.paint()
        cr.set_source_rgba(1, 1, 1, 0.07)
        cr.paint()
        cr.restore()

        rounded_rect(cr, mx + 0.5, my + 0.5, mw - 1, mh - 1, 18)
        cr.set_source_rgba(1, 1, 1, 0.22)
        cr.set_line_width(1)
        cr.stroke()

        for i, (kind, label) in enumerate(self.items):
            ix, iy, iw, ih = self.item_rect(i)
            active = i == self.index
            if active:
                rounded_rect(cr, ix, iy, iw, ih, 12)
                cr.set_source_rgba(1, 1, 1, 0.16)
                cr.fill_preserve()
                cr.set_source_rgba(1, 1, 1, 0.45)
                cr.set_line_width(1)
                cr.stroke()
            alpha = 0.97 if active else 0.7
            cr.set_source_rgba(1, 1, 1, alpha)
            cr.set_line_width(1.6)
            GLYPHS[kind](cr, ix + iw / 2, iy + 31)
            draw_text(cr, label, ix + iw / 2, iy + ih - 14, 13, alpha, center=True)

        draw_text(cr, HINT, mx + mw / 2, my + mh - 10, 10, 0.5, center=True)
