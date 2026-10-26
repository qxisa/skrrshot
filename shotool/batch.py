import gi

from gi.repository import GdkPixbuf

MAX_ITEMS = 40
THUMB_H, THUMB_W = 52, 76


def decode(data):
    loader = GdkPixbuf.PixbufLoader.new_with_type("png")
    loader.write(data)
    loader.close()
    return loader.get_pixbuf()


class Batch:
    def __init__(self):
        self.items = []

    def __len__(self):
        return len(self.items)

    def add(self, pixbuf):
        if len(self.items) >= MAX_ITEMS:
            return False
        ok, data = pixbuf.save_to_bufferv("png", ["compression"], ["1"])
        if not ok:
            return False
        scale = min(THUMB_H / pixbuf.get_height(), THUMB_W / pixbuf.get_width(), 1)
        thumb = pixbuf.scale_simple(max(1, int(pixbuf.get_width() * scale)),
                                    max(1, int(pixbuf.get_height() * scale)),
                                    GdkPixbuf.InterpType.HYPER)
        self.items.append((bytes(data), thumb))
        return True

    def thumbs(self, limit):
        return [thumb for _, thumb in self.items[:limit]]

    def first(self):
        return decode(self.items[0][0])

    def pixbufs(self):
        for data, _ in self.items:
            yield decode(data)

    def clear(self):
        self.items.clear()
