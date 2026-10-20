import gi

gi.require_version("Gdk", "3.0")
from gi.repository import Gdk


def active_window_rect(width, height):
    window = Gdk.Screen.get_default().get_active_window()
    if window is None:
        return None
    frame = window.get_frame_extents()
    x, y = max(frame.x, 0), max(frame.y, 0)
    w = min(frame.x + frame.width, width) - x
    h = min(frame.y + frame.height, height) - y
    return (x, y, w, h) if w > 0 and h > 0 else None


class Shot:
    def __init__(self):
        root = Gdk.get_default_root_window()
        self.width = root.get_width()
        self.height = root.get_height()
        self.pixbuf = Gdk.pixbuf_get_from_window(root, 0, 0, self.width, self.height)
        if self.pixbuf is None:
            raise RuntimeError("could not read the screen")
        self.scale = max(1, round(self.pixbuf.get_width() / self.width))
        self.surface = Gdk.cairo_surface_create_from_pixbuf(self.pixbuf, self.scale, None)
        self.active_rect = active_window_rect(self.width, self.height)

    def crop(self, rect):
        full_w, full_h = self.pixbuf.get_width(), self.pixbuf.get_height()
        x, y, w, h = (round(v * self.scale) for v in rect)
        x, y = max(0, min(x, full_w - 1)), max(0, min(y, full_h - 1))
        w, h = max(1, min(w, full_w - x)), max(1, min(h, full_h - y))
        return self.pixbuf.new_subpixbuf(x, y, w, h).copy()
