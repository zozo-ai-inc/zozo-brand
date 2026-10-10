# Zozo brand

The Zozo identity as code. This repository holds the program that draws the
brand assets; it does not hold the assets. Running it writes every SVG, PNG,
favicon and the brand sheet to `dist/`, which is never committed.

## Use

    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt

    .venv/bin/python -m zozo_brand                # build everything into dist/
    .venv/bin/python -m zozo_brand build --sheet-png   # also a PNG of the brand sheet
    .venv/bin/python -m unittest                  # run the tests

Open `dist/brand-sheet.html` to see the whole identity. The sheet PNG is the
only step that needs something outside Python: Chromium or Chrome on the PATH.

To try a piece of text without touching the identity:

    .venv/bin/python -m zozo_brand wordmark "zozo labs" --tail-weight 300 -o labs.svg

## What it writes

| Folder | Contents |
|---|---|
| `symbol/` | The flower alone. `symbol.svg` takes the page's text colour; the others are fixed colours, with PNGs. |
| `icon/` | The flower on a tile, for app icons: `icon` (normal) and `icon-alt` (alternate), with PNGs. |
| `favicon/` | `favicon.svg` (the bare flower, switching with the system theme), `favicon.ico` and `apple-touch-icon.png` (tile fallbacks). |
| `wordmark/` | Each name as text only. The SVG takes the page's colour; PNGs come in ink and white. |
| `lockup/` | Flower + name, same colours as the wordmarks. |
| `hero/` | A lockup on a full field of brand colour: normal and `-night`. |
| `colors.css`, `colors.json` | The palette. |
| `brand-sheet.html` | Everything on one page, with mockups. |

PNG names end in their size: `-512` is 512 pixels a side, `-h128` is 128 pixels
tall, `-w1200` is 1200 pixels wide.

## Changing the design

Every decision is a value in `zozo_brand/config.py`: names, weights, spacing,
corner radii, the flower's geometry, colours, proportions and export sizes.
Edit, rebuild, look at the sheet.

| File | Role |
|---|---|
| `config.py` | The decisions. |
| `geometry.py` | Bezier helpers and corner rounding. |
| `wordmark.py` | Sets a name in Geist and outlines it. |
| `symbol.py` | Draws the flower. |
| `svg.py` | Composes outlines into SVG documents: symbol, icon, favicon, wordmark, lockup, hero. |
| `raster.py` | SVG to PNG and ICO. |
| `assets.py` | The list of files to write. A new kind of asset is added here. |
| `sheet.py` | The brand sheet. |
| `build.py`, `__main__.py` | Writing the output folder, and the command line. |

## Usage rules

- **Symbol or icon.** The symbol is the logo. Use it wherever it can sit
  directly on a surface: site header, in-app, documents, the browser tab. The
  icon is the symbol in a container; use it only where a platform demands an
  opaque square: phone home screen, dock, app stores, avatars.
- **Colour.** Lockups and wordmarks are ink or white only. Violet and lilac
  belong to the symbol on its own, the icons and the hero fields. Violet goes
  on light backgrounds and lilac on dark; the reverse is illegible.
- **Names.** "zozo ai" is the company. Inside a product, use that product's
  name.

## Favicon

Copy the three files in `dist/favicon/` to the site root and add:

    <link rel="icon" href="/favicon.ico" sizes="32x32">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    <link rel="apple-touch-icon" href="/apple-touch-icon.png">

## How the artwork is made

Text is shaped with HarfBuzz, so the font's kerning applies, and letter-spacing
is added after each glyph as CSS does. Each glyph's overlapping pieces are
merged into one outline. A product name sets its second word at a lighter
weight from the position the first weight gave it.

Rounding works on individual corners. A corner is cut back along both of its
edges and bridged with an arc of the requested radius; everything between
corners is left exactly as drawn. Outside corners and notches take separate
radii. A radius is a maximum: where an edge is too short for it, the corners
on that edge shrink to fit. The flower gets the same rounding as the letters.

Every wordmark shares one vertical box, from the top of the ascenders to the
bottom of the descenders, and is cropped to the ink horizontally. Set the same
height on any two and they match in size.

## Font

`fonts/Geist[wght].ttf` is from <https://github.com/vercel/geist-font> at
commit `10dc7658`, version 1.800, unmodified, under the SIL Open Font License
1.1 (`fonts/OFL.txt`). The licence covers the font file. It does not cover the
artwork made with it.
