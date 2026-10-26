import io
import os
import time

import cairo
import gi

gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf

LOSSY = ("jpeg", "webp", "avif")
EXT = {"png": ".png", "jpeg": ".jpg", "webp": ".webp", "avif": ".avif", "pdf": ".pdf"}
LABELS = {"png": "PNG", "jpeg": "JPEG", "webp": "WebP", "avif": "AVIF", "pdf": "PDF"}
POINTS_PER_PIXEL = 0.75


def formats():
    writable = {f.get_name() for f in GdkPixbuf.Pixbuf.get_formats() if f.is_writable()}
    return ["png", "jpeg"] + [f for f in ("webp", "avif") if f in writable] + ["pdf"]


def is_lossy(fmt):
    return fmt in LOSSY


def encode(pixbuf, fmt, quality=85):
    if fmt == "pdf":
        return encode_pdf([pixbuf])
    keys, values = [], []
    if fmt in LOSSY:
        keys, values = ["quality"], [str(quality)]
    elif fmt == "png":
        keys, values = ["compression"], ["6"]
    ok, data = pixbuf.save_to_bufferv(fmt, keys, values)
    if not ok:
        raise RuntimeError(f"could not encode {fmt}")
    return bytes(data)


def encode_pdf(pixbufs):
    buffer = io.BytesIO()
    surface = cr = None
    for pixbuf in pixbufs:
        width = pixbuf.get_width() * POINTS_PER_PIXEL
        height = pixbuf.get_height() * POINTS_PER_PIXEL
        if surface is None:
            surface = cairo.PDFSurface(buffer, width, height)
            cr = cairo.Context(surface)
        else:
            surface.set_size(width, height)
        cr.save()
        cr.scale(POINTS_PER_PIXEL, POINTS_PER_PIXEL)
        cr.set_source_surface(Gdk.cairo_surface_create_from_pixbuf(pixbuf, 1, None), 0, 0)
        cr.paint()
        cr.restore()
        cr.show_page()
    if surface is None:
        raise RuntimeError("nothing to export")
    surface.finish()
    return buffer.getvalue()


def filename(prefix, fmt, number=None):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    suffix = f"-{number:02d}" if number else ""
    return f"{prefix}-{stamp}{suffix}{EXT[fmt]}"


def with_ext(path, fmt):
    lower = path.lower()
    if lower.endswith(EXT[fmt]) or (fmt == "jpeg" and lower.endswith(".jpeg")):
        return path
    return path + EXT[fmt]


def unique(path):
    base, ext = os.path.splitext(path)
    candidate, count = path, 1
    while os.path.exists(candidate):
        candidate = f"{base}-{count}{ext}"
        count += 1
    return candidate


def human(size):
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size / 1048576:.1f} MB"
