"""The symbol: a lotus seen from above, drawn as a pinwheel."""

from __future__ import annotations

import cmath
import math
from functools import lru_cache

import pathops
from pathops import LineCap, LineJoin, PathOp

from . import config
from .geometry import bounds, contours_path, path_contours, path_data, round_shape, seg_point, signed_area
from .wordmark import BrandError

CENTRE = complex(config.SYMBOL_SIZE / 2, config.SYMBOL_SIZE / 2)


def turn(deg):
    """Unit vector pointing up the page, rotated clockwise by deg."""
    return -1j * cmath.exp(1j * math.radians(deg))


def petal(base, direction, length, width, lo, hi, taper):
    """A pointed lens from base to base + length * direction.

    lo and hi place the side handles along the length: lo near 0 gives a
    rounded base, a higher hi a later-closing tip. taper below 1 pulls the
    upper handles in, which narrows the tip to a sharper point.
    """
    side = direction * 1j
    h = width / 2 / 0.75  # a cubic with both handles at h bulges to 0.75 h

    def at(x, y):
        return base + side * x + direction * y

    tip = at(0, length)
    return contours_path([[
        (base, at(h, lo * length), at(h * taper, hi * length), tip),
        (tip, at(-h * taper, hi * length), at(-h, lo * length), base),
    ]])


def grow(path, amount):
    """The shape made larger by amount on every side."""
    outline = pathops.Path()
    outline.addPath(path)
    outline.stroke(2 * amount, LineCap.ROUND_CAP, LineJoin.ROUND_JOIN, 4)
    outline.convertConicsToQuads()
    outline = pathops.simplify(outline, fix_winding=True)
    return pathops.op(path, outline, PathOp.UNION, fix_winding=True)


def outlines_cross(a, b, samples=240):
    """Whether the outline of shape a passes through shape b."""
    for contour in path_contours(a):
        inside = [b.contains((p.real, p.imag)) for seg in contour for p in (seg_point(seg, i / samples) for i in range(samples))]
        if any(inside) and not all(inside):
            return True
    return False


def pinwheel(petals, inner, outer, slant, width, lo, hi, taper, gap):
    """The flower as one pathops shape, before scaling and rounding."""
    shapes = []
    for k in range(petals):
        angle = 360 / petals * k
        base = CENTRE + inner * turn(angle - slant)
        tip = CENTRE + outer * turn(angle)
        axis = tip - base
        shapes.append(petal(base, axis / abs(axis), abs(axis), width, lo, hi, taper))
    # Each petal is cut back only by the one before it, so the weave is wrong
    # if a petal also reaches the one after next.
    if petals > 3 and any(outlines_cross(shapes[k], shapes[(k + 2) % petals]) for k in range(petals)):
        raise BrandError("pinwheel: petals overlap beyond their neighbours; reduce width or slant")
    out = None
    for k in range(petals):
        piece = pathops.op(shapes[k], grow(shapes[k - 1], gap), PathOp.DIFFERENCE, fix_winding=True)
        out = piece if out is None else pathops.op(out, piece, PathOp.UNION, fix_winding=True)
    return out


@lru_cache(maxsize=None)
def symbol_path() -> str:
    """SVG path data for the symbol on its square, corners rounded."""
    size, margin = config.SYMBOL_SIZE, config.SYMBOL_MARGIN
    contours = [c for c in path_contours(pinwheel(**config.PINWHEEL)) if abs(signed_area(c)) > 40]
    if not contours:
        raise BrandError("pinwheel: nothing left to draw")
    x0, y0, x1, y1 = bounds(contours)
    scale = (size - 2 * margin) / max(x1 - x0, y1 - y0)
    shift = complex(size / 2, size / 2) - complex(x0 + x1, y0 + y1) / 2 * scale
    contours = [[tuple(p * scale + shift for p in seg) for seg in c] for c in contours]
    return path_data(round_shape(contours, config.ROUND_OUTER, config.ROUND_INNER), digits=1)
