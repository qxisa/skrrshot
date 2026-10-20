import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from .draw import draw_text, rounded_rect, text_width

HEIGHT = 40
HOLD_MS = 1600
FADE_STEP = 0.07


class Toast(Gtk.Window):
    def __init__(self, text):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.text = text
        self.alive = True
        self.set_app_paintable(True)
        self.set_accept_focus(False)
        visual = self.get_screen().get_rgba_visual()
        if visual is not None:
            self.set_visual(visual)

        probe = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
        self.width = int(text_width(probe, text, 13)) + 40
        self.set_default_size(self.width, HEIGHT)
        self.place()

        self.connect("draw", self.on_draw)
        self.connect("realize", self.on_realize)

    def place(self):
        display = Gdk.Display.get_default()
        _, px, py = display.get_default_seat().get_pointer().get_position()
        area = display.get_monitor_at_point(px, py).get_workarea()
        self.move(area.x + (area.width - self.width) // 2, area.y + area.height - HEIGHT - 64)

    def on_realize(self, _widget):
        self.get_window().input_shape_combine_region(cairo.Region(), 0, 0)

    def on_draw(self, _widget, cr):
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        rounded_rect(cr, 0.5, 0.5, self.width - 1, HEIGHT - 1, 14)
        cr.set_source_rgba(0.08, 0.08, 0.1, 0.8)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.16)
        cr.set_line_width(1)
        cr.stroke()
        draw_text(cr, self.text, self.width / 2, HEIGHT / 2 + 4.5, 13, 0.92, center=True)
        return True

    def show(self):
        self.show_all()
        GLib.timeout_add(HOLD_MS, self.start_fade)

    def start_fade(self):
        if self.alive:
            GLib.timeout_add(16, self.fade)
        return False

    def fade(self):
        if not self.alive:
            return False
        opacity = self.get_opacity() - FADE_STEP
        if opacity <= 0:
            self.close()
            return False
        self.set_opacity(opacity)
        return True

    def close(self):
        if self.alive:
            self.alive = False
            self.destroy()
