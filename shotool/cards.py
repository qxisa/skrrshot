import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from . import config, export
from .draw import draw_text, rounded_rect

CARD_W = 300
PAD = 14
ROW_H = 34
HOLD_MS = 6000
LEAVE_MS = 2500
EDGE = 24
QUALITIES = (100, 95, 90, 85, 80, 70, 60, 50, 40, 30)
BLOCKING = Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.MOD1_MASK | Gdk.ModifierType.SUPER_MASK


def fit(pixbuf, max_w, max_h):
    scale = min(max_w / pixbuf.get_width(), max_h / pixbuf.get_height(), 1)
    return pixbuf.scale_simple(max(1, int(pixbuf.get_width() * scale)),
                               max(1, int(pixbuf.get_height() * scale)),
                               GdkPixbuf.InterpType.HYPER)


class Row:
    def __init__(self, id, label, key="", options=None, index=0, enabled=True, off_text=""):
        self.id, self.label, self.key = id, label, key
        self.options, self.index = options, index
        self.enabled, self.off_text = enabled, off_text

    @property
    def value(self):
        return self.options[self.index][0]

    @property
    def text(self):
        return self.options[self.index][1]


class Card:
    def __init__(self, title, subtitle, rows, handler, thumbs=(), more=0,
                 footer=None, hint="", active=False):
        self.title, self.subtitle = title, subtitle
        self.rows, self.handler = rows, handler
        self.thumbs, self.more = list(thumbs), more
        self.footer, self.hint, self.active = footer, hint, active
        self.index = next((i for i, r in enumerate(rows) if r.enabled), 0)
        self.rows_y = 0

    def size(self):
        y = PAD + 44
        self.thumbs_y = y
        if self.thumbs:
            y += max(t.get_height() for t in self.thumbs) + 12
        self.rows_y = y
        y += len(self.rows) * ROW_H
        if self.footer is not None:
            y += 22
        y += 22
        return CARD_W, y + PAD - 6

    def row_rect(self, i):
        return (PAD, self.rows_y + i * ROW_H, CARD_W - 2 * PAD, ROW_H - 4)

    def row_at(self, x, y):
        for i in range(len(self.rows)):
            rx, ry, rw, rh = self.row_rect(i)
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return i
        return None

    def move(self, delta):
        for _ in range(len(self.rows)):
            self.index = (self.index + delta) % len(self.rows)
            if self.rows[self.index].enabled:
                return

    def change(self, delta):
        row = self.rows[self.index]
        if not row.options or not row.enabled:
            return None
        row.index = (row.index + delta) % len(row.options)
        return self.handler(self, ("change", row))

    def activate(self, i):
        row = self.rows[i]
        if not row.enabled:
            return None
        if row.options:
            return self.change(1)
        return self.handler(self, ("activate", row))

    def hover(self, x, y):
        i = self.row_at(x, y)
        if i is not None and self.rows[i].enabled:
            self.index = i

    def click(self, x, y):
        i = self.row_at(x, y)
        if i is None or not self.rows[i].enabled:
            return None
        self.index = i
        return self.activate(i)

    def key(self, key):
        if key == Gdk.KEY_Escape:
            return self.handler(self, ("back", None))
        if key == Gdk.KEY_Up:
            self.move(-1)
        elif key in (Gdk.KEY_Down, Gdk.KEY_Tab):
            self.move(1)
        elif key == Gdk.KEY_Left:
            return self.change(-1)
        elif key == Gdk.KEY_Right:
            return self.change(1)
        elif key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            return self.activate(self.index)
        else:
            name = (Gdk.keyval_name(key) or "").lower()
            for i, row in enumerate(self.rows):
                if len(name) == 1 and row.key.lower() == name:
                    self.index = i
                    return self.activate(i)
        return None

    def draw(self, cr):
        w, h = self.size()
        rounded_rect(cr, 0.5, 0.5, w - 1, h - 1, 18)
        cr.set_source_rgba(0.08, 0.08, 0.1, 0.88)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.18)
        cr.set_line_width(1)
        cr.stroke()

        draw_text(cr, self.title, PAD, PAD + 15, 14, 0.95, bold=True)
        draw_text(cr, self.subtitle, PAD, PAD + 34, 11, 0.55)

        if self.thumbs:
            x = PAD if len(self.thumbs) > 1 else (CARD_W - self.thumbs[0].get_width()) / 2
            for thumb in self.thumbs:
                cr.save()
                rounded_rect(cr, x, self.thumbs_y, thumb.get_width(), thumb.get_height(), 8)
                cr.clip()
                Gdk.cairo_set_source_pixbuf(cr, thumb, x, self.thumbs_y)
                cr.paint()
                cr.restore()
                x += thumb.get_width() + 6
            if self.more:
                draw_text(cr, f"+{self.more}", x + 2, self.thumbs_y + thumb.get_height() / 2 + 5, 13, 0.7)

        for i, row in enumerate(self.rows):
            rx, ry, rw, rh = self.row_rect(i)
            selected = i == self.index and row.enabled
            if selected:
                rounded_rect(cr, rx, ry, rw, rh, 10)
                cr.set_source_rgba(1, 1, 1, 0.14)
                cr.fill_preserve()
                cr.set_source_rgba(1, 1, 1, 0.35)
                cr.set_line_width(1)
                cr.stroke()
            alpha = 0.95 if selected else (0.75 if row.enabled else 0.35)
            draw_text(cr, row.label, rx + 12, ry + 21, 13, alpha)
            if row.options and row.enabled:
                draw_text(cr, f"\u2039  {row.text}  \u203a", rx + rw - 12, ry + 21, 13, alpha, right=True)
            elif row.options:
                draw_text(cr, row.off_text, rx + rw - 12, ry + 21, 13, 0.4, right=True)
            elif row.key:
                draw_text(cr, row.key, rx + rw - 12, ry + 21, 11, 0.45, right=True)

        y = self.rows_y + len(self.rows) * ROW_H
        if self.footer is not None:
            draw_text(cr, self.footer, PAD, y + 15, 11, 0.6)
            y += 22
        draw_text(cr, self.hint, CARD_W / 2, y + 14, 10, 0.4, center=True)


def capture_card(app, pixbuf):
    rows = [Row("save", "Save", "S"), Row("batch", "Add to batch", "B"),
            Row("convert", "Convert or compress", "C"), Row("close", "Close", "Esc")]

    def handler(card, event):
        kind, row = event
        if kind == "back" or (kind == "activate" and row.id == "close"):
            return ("close",)
        if kind == "activate":
            if row.id == "convert":
                return ("screen", convert_card(app, pixbuf, False, [], 0,
                                               lambda: capture_card(app, pixbuf)))
            return ("act", row.id, pixbuf)
        return None

    return Card("Copied to clipboard", f"{pixbuf.get_width()} \u00d7 {pixbuf.get_height()}",
                rows, handler, thumbs=[fit(pixbuf, CARD_W - 2 * PAD, 140)],
                hint="Click, or hover and use the keyboard")


def convert_card(app, sample, is_batch, thumbs, more, back):
    ids = export.formats()
    saved_format = config.get("format", "png")
    saved_quality = config.get("quality", 85)
    format_options = [(i, "PDF (one file)" if i == "pdf" and is_batch else export.LABELS[i]) for i in ids]
    quality_options = [(q, str(q)) for q in QUALITIES]
    format_index = ids.index(saved_format) if saved_format in ids else 0
    quality_index = min(range(len(QUALITIES)), key=lambda i: abs(QUALITIES[i] - saved_quality))

    rows = [Row("format", "Format", options=format_options, index=format_index),
            Row("quality", "Quality", options=quality_options, index=quality_index,
                enabled=export.is_lossy(ids[format_index]), off_text="Lossless"),
            Row("save", "Save all" if is_batch else "Save", "S")]
    if is_batch:
        rows.append(Row("discard", "Discard batch", "D"))
    rows.append(Row("back", "Back" if back else "Close", "Esc"))

    def estimate():
        try:
            size = len(export.encode(sample, rows[0].value, rows[1].value))
        except Exception:
            return ""
        return f"About {export.human(size)}" + (" per image" if is_batch else "")

    def handler(card, event):
        kind, row = event
        if kind == "change":
            rows[1].enabled = export.is_lossy(rows[0].value)
            config.put(format=rows[0].value, quality=rows[1].value)
            card.footer = estimate()
        elif kind == "back" or (kind == "activate" and row.id == "back"):
            return ("screen", back()) if back else ("close",)
        elif kind == "activate":
            if row.id == "save":
                return ("act", "save_batch" if is_batch else "save", None if is_batch else sample)
            if row.id == "discard":
                return ("act", "discard", None)
        return None

    if is_batch:
        title, subtitle = f"Batch: {app.batch_size()} screenshots", "Choose a format, then save all"
    else:
        title, subtitle = "Convert or compress", f"{sample.get_width()} \u00d7 {sample.get_height()}"
    card = Card(title, subtitle, rows, handler, thumbs=thumbs, more=more,
                footer="", hint="Arrows change   Enter select   Esc back", active=True)
    card.footer = estimate()
    return card


def batch_card(app):
    batch = app.batch
    return convert_card(app, batch.first(), True, batch.thumbs(3), max(0, len(batch) - 3), None)


class CardWindow(Gtk.Window):
    def __init__(self, app, card):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.app = app
        self.card = None
        self.alive = True
        self.grabbed = False
        self.source = 0
        self.tries = 0
        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual is not None:
            self.set_visual(visual)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK
                        | Gdk.EventMask.KEY_PRESS_MASK | Gdk.EventMask.ENTER_NOTIFY_MASK
                        | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.connect("draw", self.on_draw)
        self.connect("key-press-event", self.on_key)
        self.connect("button-press-event", self.on_press)
        self.connect("motion-notify-event", self.on_motion)
        self.connect("enter-notify-event", self.on_enter)
        self.connect("leave-notify-event", self.on_leave)
        self.set_card(card)

    def set_card(self, card):
        self.card = card
        w, h = card.size()
        display = Gdk.Display.get_default()
        _, px, py = display.get_default_seat().get_pointer().get_position()
        area = display.get_monitor_at_point(px, py).get_workarea()
        self.resize(w, h)
        self.move(area.x + area.width - w - EDGE, area.y + area.height - h - EDGE)
        self.cancel()
        self.set_opacity(1)
        if card.active:
            self.app.busy = True
            self.request_grab()
        else:
            self.release()
            self.schedule(HOLD_MS)
        self.queue_draw()

    def schedule(self, ms):
        self.cancel()
        self.source = GLib.timeout_add(ms, self.start_fade)

    def cancel(self):
        if self.source:
            GLib.source_remove(self.source)
            self.source = 0

    def start_fade(self):
        self.source = GLib.timeout_add(16, self.fade)
        return False

    def fade(self):
        opacity = self.get_opacity() - 0.07
        if opacity <= 0:
            self.source = 0
            self.close()
            return False
        self.set_opacity(opacity)
        return True

    def request_grab(self):
        if not self.grabbed:
            self.tries = 0
            GLib.timeout_add(30, self.try_grab)

    def try_grab(self):
        if not self.alive or self.grabbed:
            return False
        seat = self.get_display().get_default_seat()
        status = seat.grab(self.get_window(), Gdk.SeatCapabilities.KEYBOARD, True, None, None, None, None)
        self.tries += 1
        if status == Gdk.GrabStatus.SUCCESS:
            self.grabbed = True
            return False
        return self.tries < 30

    def release(self):
        if self.grabbed:
            self.get_display().get_default_seat().ungrab()
            self.grabbed = False

    def on_enter(self, _widget, event):
        if not self.card.active:
            self.cancel()
            self.set_opacity(1)
            self.request_grab()
        return False

    def on_leave(self, _widget, event):
        if not self.card.active and event.mode == Gdk.CrossingMode.NORMAL:
            self.release()
            self.schedule(LEAVE_MS)
        return False

    def on_draw(self, _widget, cr):
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        self.card.draw(cr)
        return True

    def on_motion(self, _widget, event):
        self.card.hover(event.x, event.y)
        self.queue_draw()
        return True

    def on_press(self, _widget, event):
        if event.button == 1:
            self.run(self.card.click(event.x, event.y))
        elif event.button == 3:
            self.run(self.card.handler(self.card, ("back", None)))
        self.queue_draw()
        return True

    def on_key(self, _widget, event):
        if not event.state & BLOCKING:
            self.run(self.card.key(event.keyval))
            self.queue_draw()
        return True

    def run(self, command):
        if not command:
            return
        if command[0] == "screen":
            self.set_card(command[1])
        elif command[0] == "close":
            self.close()
        elif command[0] == "act":
            self.close()
            self.app.act(command[1], command[2])

    def close(self):
        if not self.alive:
            return
        self.alive = False
        self.cancel()
        self.release()
        self.app.card_closed(self)
        self.destroy()
