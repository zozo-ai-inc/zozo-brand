"""The list of everything the build writes, apart from the sheet."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import config, raster, svg
from .config import COLORS
from .wordmark import brand_wordmark


@dataclass
class Asset:
    """One SVG, with the PNGs to make from it.

    Each raster is (file-name suffix, {"width": px} or {"height": px}, colour).
    A colour is given for drawings that take the page's colour, which has to
    be fixed before they can be rendered; None renders the SVG as it is.
    """

    path: str  # relative to the output folder, without extension
    svg: str
    rasters: list = field(default_factory=list)

    def files(self, with_rasters=True):
        """Every (relative path, bytes) this asset produces."""
        yield f"{self.path}.svg", (self.svg + "\n").encode()
        for suffix, size, color in self.rasters if with_rasters else ():
            source = self.svg.replace("currentColor", COLORS[color]) if color else self.svg
            yield f"{self.path}{suffix}.png", raster.png(source, **size)


def slug(name):
    return name.replace(" ", "-")


def all_assets() -> list[Asset]:
    square = [(f"-{px}", {"width": px}, None) for px in config.PNG_SQUARE_SIZES]
    text = [(f"-{c}-h{px}", {"height": px}, c) for c in config.TEXT_COLORS for px in config.PNG_TEXT_HEIGHTS]
    wide = [(f"-w{px}", {"width": px}, None) for px in config.PNG_HERO_WIDTHS]
    tall = [(f"-h{px}", {"height": px}, None) for px in config.PNG_TEXT_HEIGHTS]

    out = [Asset("symbol/symbol", svg.symbol())]
    out += [Asset(f"symbol/symbol-{c}", svg.symbol(COLORS[c]), square) for c in config.SYMBOL_COLORS]
    out += [Asset(f"icon/{key}", svg.icon(**spec), square) for key, spec in config.ICONS.items()]
    out.append(Asset("favicon/favicon", svg.favicon()))
    for name in config.NAMES:
        mark = brand_wordmark(name)
        out.append(Asset(f"wordmark/{slug(name)}", svg.wordmark(mark), text))
        out.append(Asset(f"lockup/{slug(name)}", svg.lockup(mark), text))
        for suffix, spec in config.HEROES.items():
            out.append(Asset(f"hero/{slug(name)}{suffix}", svg.hero(mark, **spec), wide))
            out.append(Asset(f"hero/{slug(name)}{suffix}-tight", svg.hero(mark, **spec, tight=True), tall))
    return out


def favicon_fallbacks():
    """The tile versions of the favicon, as (relative path, bytes)."""
    tile = svg.icon(**config.ICONS["icon"])
    yield "favicon/favicon.ico", raster.ico([raster.png(tile, width=px) for px in config.FAVICON_ICO_SIZES])
    # the phone rounds the corners itself, so this one is a full square
    square = svg.icon(**config.ICONS["icon"], radius=0)
    yield "favicon/apple-touch-icon.png", raster.png(square, width=config.TOUCH_ICON_SIZE)


def color_files():
    """The palette for other codebases, as (relative path, bytes)."""
    lines = "\n".join(f"  --zozo-{name}: {value};" for name, value in COLORS.items())
    yield "colors.css", f"/* Zozo brand colours. Generated; edit zozo_brand/config.py. */\n:root {{\n{lines}\n}}\n".encode()
    yield "colors.json", (json.dumps(COLORS, indent=2) + "\n").encode()
