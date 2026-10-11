"""Every design decision in one place.

Change a value here and rebuild; nothing else needs editing. Lengths that
describe letterforms or the symbol are in font units, 1000 to the em, unless
a comment says otherwise.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "fonts" / "Geist[wght].ttf"

# ---- Names. The company comes first; every other name is a product.
COMPANY = "zozo ai"
PRODUCTS = ("zozo suite", "zozo chat", "zozo studio", "zozo agent")
NAMES = (COMPANY, *PRODUCTS)

# ---- Type: Geist, lowercase, outlined.
WEIGHT = 600  # the company name, and "zozo" in every product name
PRODUCT_WEIGHT = 300  # the second word of a product name
LETTER_SPACING = -0.035  # em, as CSS letter-spacing
DOTLESS_I = True  # set i as the dotless glyph
FEATURES = ("ss01",)  # OpenType features; ss01 is Geist's a without a tail

# ---- Corner rounding, shared by the letters and the symbol. For scale, the
# vertical stems at weight 600 are 128 wide.
ROUND_OUTER = 30  # corners that point out of the shape
ROUND_INNER = 12  # notches where strokes meet

# ---- Symbol: a lotus from above as a pinwheel, each petal tucked under the
# one before it. Drawn on a 1000 square.
SYMBOL_SIZE = 1000
SYMBOL_MARGIN = 30  # the flower is scaled to fill the square up to this margin
PINWHEEL = dict(
    petals=6,
    inner=200,  # radius at which the petals start
    outer=470,  # radius of the tips
    slant=90,  # degrees each petal's base is turned back from its tip
    width=380,
    lo=0.2,  # where the lower side handles sit along the petal, 0 to 1
    hi=0.9,  # where the upper side handles sit
    taper=0.5,  # below 1 narrows the tip to a sharper point
    gap=44,  # the cut between a petal and the one over it
)

# ---- Colour. These are the only colours the identity uses.
COLORS = {
    "violet": "#491385",  # primary brand colour
    "lilac": "#c69af2",  # the brand colour for dark backgrounds
    "ink": "#15111c",  # black: text on light, and the alternate icon's ground
    "white": "#ffffff",  # white: text on dark and on violet
    "mist": "#f7f6f9",  # light page background
    "night": "#0b0910",  # dark page background
    "edge": "#3d3549",  # hairline around the alternate icon
}
# Rule: lockups and wordmarks are set in ink or white only. Violet and lilac
# belong to the flower on its own, the icons and the hero fields.
TEXT_COLORS = ("ink", "white")
SYMBOL_COLORS = ("violet", "lilac", "ink", "white")
# Foreground on background pairs the identity relies on, kept legible by a test.
PAIRINGS = (("white", "violet"), ("lilac", "ink"), ("violet", "mist"), ("lilac", "night"), ("ink", "mist"), ("white", "night"))
MIN_CONTRAST = 4.5

# ---- Lockup proportions, in units of the wordmark's x-height.
LOCKUP_SYMBOL = 1.5  # flower height
LOCKUP_GAP = 0.42  # space between flower and text
HERO_PAD = 1.5  # field around a hero lockup, on every side

# ---- Icons: the flower on a rounded tile. Sizes are out of 1000.
ICON_FILL = 0.72  # share of the tile the flower fills
ICON_RADIUS = 230
ICON_EDGE = 14
ICONS = {
    "icon": dict(ground="violet", ink="white"),  # normal
    "icon-alt": dict(ground="ink", ink="lilac", edge="edge"),  # alternate
}

# ---- Heroes: a lockup on a full field of colour. "text" colours the name
# separately from the flower. The key is the file-name suffix. Each is also
# written as a "-tight" version: the same colours, no field, cropped to the
# lockup, for a client that paints the "ground" colour itself.
HEROES = {
    "": dict(ground="violet", ink="white"),
    "-night": dict(ground="night", ink="lilac", text="white"),
}

# ---- Favicon: the bare flower, switching colour with the system theme. The
# normal icon is the fallback for anything that cannot switch, and for the
# phone home screen, which needs an opaque square.
FAVICON = dict(light="violet", dark="lilac")
FAVICON_ICO_SIZES = (16, 32, 48)
TOUCH_ICON_SIZE = 180

# ---- Raster exports, in pixels.
PNG_SQUARE_SIZES = (16, 32, 48, 64, 128, 180, 192, 256, 512, 1024)  # symbol and icons, per side
PNG_TEXT_HEIGHTS = (64, 128, 256)  # wordmarks and lockups, by height
PNG_HERO_WIDTHS = (1200, 2400)  # heroes, by width
