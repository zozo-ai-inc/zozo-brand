"""Compose the outlines into SVG documents.

Every function returns a complete <svg> element as a string. `attrs` is extra
markup for the opening tag; the default makes a standalone file, and the sheet
passes sizes instead to embed the same drawing in HTML.
"""

from __future__ import annotations

from xml.sax.saxutils import quoteattr

from . import config
from .config import COLORS
from .symbol import symbol_path
from .wordmark import Wordmark

XMLNS = ' xmlns="http://www.w3.org/2000/svg"'
SIZE = config.SYMBOL_SIZE


def _label(text):
    return f' role="img" aria-label={quoteattr(text)}'


def symbol(fill="currentColor", attrs=XMLNS):
    return f'<svg{attrs} viewBox="0 0 {SIZE} {SIZE}" fill="{fill}"><path d="{symbol_path()}"/></svg>'


def icon(ground, ink, edge=None, radius=config.ICON_RADIUS, attrs=XMLNS):
    """The flower on a tile. radius 0 gives a full square for platforms that
    cut the corners themselves."""
    rx = f' rx="{radius}"' if radius else ""
    rect = f'<rect width="{SIZE}" height="{SIZE}"{rx} fill="{COLORS[ground]}"/>'
    if edge:
        w = config.ICON_EDGE
        rect += (
            f'<rect x="{w / 2:g}" y="{w / 2:g}" width="{SIZE - w}" height="{SIZE - w}" rx="{radius - w / 2:g}"'
            f' fill="none" stroke="{COLORS[edge]}" stroke-width="{w}"/>'
        )
    inset = SIZE * (1 - config.ICON_FILL) / 2
    return (
        f'<svg{attrs} viewBox="0 0 {SIZE} {SIZE}">{rect}'
        f'<path fill="{COLORS[ink]}" transform="translate({inset:g} {inset:g}) scale({config.ICON_FILL})" d="{symbol_path()}"/></svg>'
    )


def favicon():
    """The bare flower, changing colour with the system theme."""
    light, dark = COLORS[config.FAVICON["light"]], COLORS[config.FAVICON["dark"]]
    return (
        f'<svg{XMLNS} viewBox="0 0 {SIZE} {SIZE}"><style>path{{fill:{light}}}'
        f'@media (prefers-color-scheme:dark){{path{{fill:{dark}}}}}</style><path d="{symbol_path()}"/></svg>'
    )


def wordmark(mark: Wordmark, fill="currentColor", attrs=XMLNS):
    return (
        f'<svg{attrs} viewBox="0 0 {mark.width:.2f} {mark.height:.2f}" fill="{fill}"{_label(mark.text)}>'
        f'<path d="{mark.path_data()}"/></svg>'
    )


def _lockup_parts(mark: Wordmark, text_fill=None):
    """Flower and wordmark side by side, the flower centred on the x-height.

    Returns the two paths as markup with the box they occupy (x, y, w, h).
    """
    size = config.LOCKUP_SYMBOL * mark.x_height
    top = mark.top - mark.x_height / 2 - size / 2
    x = size + config.LOCKUP_GAP * mark.x_height
    fill = f' fill="{text_fill}"' if text_fill else ""
    paths = (
        f'<path transform="translate(0 {top:.1f}) scale({size / SIZE:.4f})" d="{symbol_path()}"/>'
        f'<path{fill} transform="translate({x:.1f} 0)" d="{mark.path_data()}"/>'
    )
    y = min(top, 0)
    return paths, (0, y, x + mark.width, mark.height - y)


def lockup(mark: Wordmark, fill="currentColor", attrs=XMLNS):
    paths, (x, y, w, h) = _lockup_parts(mark)
    return f'<svg{attrs} viewBox="{x:g} {y:.1f} {w:.1f} {h:.1f}" fill="{fill}"{_label(mark.text)}>{paths}</svg>'


def hero(mark: Wordmark, ground, ink, text=None, attrs=XMLNS):
    """A lockup on a full field of colour, with the field as part of the artwork."""
    paths, (x, _, w, _) = _lockup_parts(mark, COLORS[text] if text else None)
    # pad around the lowercase letters rather than the box, which has empty
    # ascender or descender space on some names
    pad = config.HERO_PAD * mark.x_height
    top, bottom = mark.top - mark.x_height - pad, mark.top + pad
    box = f'{x - pad:.1f} {top:.1f} {w + 2 * pad:.1f} {bottom - top:.1f}'
    return (
        f'<svg{attrs} viewBox="{box}"{_label(mark.text)}>'
        f'<rect x="{x - pad:.1f}" y="{top:.1f}" width="{w + 2 * pad:.1f}" height="{bottom - top:.1f}" fill="{COLORS[ground]}"/>'
        f'<g fill="{COLORS[ink]}">{paths}</g></svg>'
    )
