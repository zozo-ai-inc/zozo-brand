"""Set a name in Geist and return it as rounded outlines."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import pathops
import uharfbuzz as hb
from fontTools.ttLib import TTFont

from . import config
from .geometry import bounds, contours_path, path_contours, path_data, round_shape

# Glyphs whose stock outlines set the vertical box: top of the ascenders and
# bottom of the descenders. Every wordmark gets this same box whatever letters
# it contains, so all the names sit on one baseline at one size.
BOX_REFERENCE = "hg"


class BrandError(Exception):
    """A design setting that cannot be drawn."""


@lru_cache(maxsize=None)
def _font():
    data = config.FONT_PATH.read_bytes()
    return TTFont(config.FONT_PATH), hb.Face(data)


@lru_cache(maxsize=None)
def glyph_contours(glyph_name, weight):
    """Outline of one glyph at a weight, overlaps merged, as closed contours."""
    ttfont, _ = _font()
    glyph_set = ttfont.getGlyphSet(location={"wght": weight})
    path = pathops.Path()
    glyph_set[glyph_name].draw(path.getPen(glyphSet=glyph_set))
    # Variable-font glyphs are drawn as overlapping pieces. Merge them so the
    # only corners left are ones you can see.
    path = pathops.simplify(path, fix_winding=True, keep_starting_points=True)
    return path_contours(path, glyph_set)


def shape(text, weight, spacing, features):
    """Lay text out with HarfBuzz: glyph names and positions in font units."""
    ttfont, face = _font()
    font = hb.Font(face)
    font.set_variations({"wght": weight})
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    # Browsers switch optional ligatures off when letter-spacing is non-zero.
    ligatures = spacing == 0
    hb.shape(font, buf, {"kern": True, "liga": ligatures, "clig": ligatures, **{tag: True for tag in features}})
    x, placed = 0.0, []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        placed.append((ttfont.getGlyphName(info.codepoint), x + pos.x_offset, pos.y_offset))
        x += pos.x_advance + spacing * face.upem
    return placed


@dataclass
class Wordmark:
    text: str
    glyphs: list  # contours per glyph, already positioned, y up
    x_min: float
    x_max: float
    top: float  # ascender height above the baseline
    bottom: float  # descender depth, negative
    x_height: float
    notes: list = field(default_factory=list)

    @property
    def width(self):
        return self.x_max - self.x_min

    @property
    def height(self):
        return self.top - self.bottom

    def path_data(self):
        """SVG path data, y down, origin at the box's top left."""
        place = lambda p: complex(p.real - self.x_min, self.top - p.imag)
        return "".join(path_data(contours, place) for contours in self.glyphs)


def build(
    text,
    *,
    weight=config.WEIGHT,
    tail_weight=None,
    spacing=config.LETTER_SPACING,
    round_outer=config.ROUND_OUTER,
    round_inner=config.ROUND_INNER,
    dotless_i=config.DOTLESS_I,
    features=config.FEATURES,
) -> Wordmark:
    """Outline `text`. tail_weight sets every word after the first at another
    weight, keeping the position the first weight gave it."""
    ttfont, _ = _font()
    shown = text.replace("i", "ı") if dotless_i else text
    cmap = ttfont.getBestCmap()
    missing = sorted({c for c in shown if ord(c) not in cmap})
    if missing:
        raise BrandError(f"the font has no glyph for: {' '.join(missing)}")

    placed = [(g, weight) for g in shape(shown, weight, spacing, features)]
    if tail_weight is not None and " " in shown:
        head = shown.index(" ") + 1
        start = placed[head][0][1]
        tail = shape(shown[head:], tail_weight, spacing, features)
        placed = placed[:head] + [((n, x + start, y), tail_weight) for n, x, y in tail]

    notes, glyphs, names, spans = [], [], [], []
    for (name, gx, gy), glyph_weight in placed:
        contours = glyph_contours(name, glyph_weight)
        if not contours:
            continue
        contours = round_shape(contours, round_outer, round_inner)
        offset = complex(gx, gy)
        contours = [[tuple(p + offset for p in seg) for seg in c] for c in contours]
        glyphs.append(contours)
        names.append(name)
        spans.append(bounds(contours))
    if not glyphs:
        raise BrandError(f"nothing to draw for {text!r}")

    for i in range(len(glyphs) - 1):
        if spans[i + 1][0] < spans[i][2]:  # boxes overlap, so check the ink itself
            shared = pathops.op(contours_path(glyphs[i]), contours_path(glyphs[i + 1]), pathops.PathOp.INTERSECTION)
            if abs(shared.area) > 0.5:
                notes.append(f"{names[i]} and {names[i + 1]} touch")

    ref = {ch: bounds(glyph_contours(cmap[ord(ch)], weight)) for ch in BOX_REFERENCE + "x"}
    top = max(ref[c][3] for c in BOX_REFERENCE)
    bottom = min(ref[c][1] for c in BOX_REFERENCE)
    if min(s[1] for s in spans) < bottom - 0.5 or max(s[3] for s in spans) > top + 0.5:
        notes.append("ink extends outside the shared vertical box")
    return Wordmark(
        text=text,
        glyphs=glyphs,
        x_min=min(s[0] for s in spans),
        x_max=max(s[2] for s in spans),
        top=top,
        bottom=bottom,
        x_height=ref["x"][3],
        notes=notes,
    )


@lru_cache(maxsize=None)
def brand_wordmark(name) -> Wordmark:
    """A name as the identity sets it: the company in one weight, a product
    with its second word lighter."""
    return build(name, tail_weight=None if name == config.COMPANY else config.PRODUCT_WEIGHT)
