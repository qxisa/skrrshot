import math

import cairo


def rounded_rect(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def text_width(cr, text, size):
    cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size)
    return cr.text_extents(text).x_advance


def draw_text(cr, text, x, y, size, alpha=1.0, center=False):
    width = text_width(cr, text, size)
    if center:
        x -= width / 2
    cr.move_to(x, y)
    cr.set_source_rgba(1, 1, 1, alpha)
    cr.show_text(text)
    return width
