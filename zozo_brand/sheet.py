"""The brand sheet: one HTML page showing the whole identity."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import config, svg
from .config import COLORS, FAVICON, HEROES, ICONS
from .wordmark import brand_wordmark

WIDTH = 1600  # the page's content width in CSS pixels
PADDING = 32
SMALL_PX = 22  # lockup height that stands in for a sidebar header

CSS = """
* { box-sizing: border-box; }
body { margin: 0; padding: %(pad)dpx; background: #d9d9de; width: %(width)dpx; font: 13px/1.4 ui-sans-serif, system-ui, sans-serif; color: #333; }
h1 { font-size: 15px; margin: 34px 0 12px; }
h1:first-child { margin-top: 0; }
h1 span { font-weight: 400; opacity: .7; }
svg { display: block; }
.row { display: grid; gap: 16px; }
.panel { padding: 36px 40px; border-radius: 6px; }
.cap { font: 11px/1.3 ui-monospace, monospace; opacity: .6; margin-top: 10px; }
.swatches { display: grid; grid-template-columns: repeat(7, 1fr); gap: 16px; }
.swatch { height: 96px; border-radius: 6px; border: 1px solid rgba(0,0,0,.12); }
.items { display: flex; gap: 44px; align-items: flex-end; flex-wrap: wrap; }
.stack svg { margin-bottom: 30px; }
.stack svg:last-child { margin-bottom: 0; }
.small { display: flex; flex-wrap: wrap; gap: 18px 36px; margin-top: 40px; }
.heroes { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.heroes svg { width: 100%%; height: auto; border-radius: 6px; }
.uses { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.use { padding: 36px 40px; border-radius: 6px; display: grid; grid-template-columns: max-content max-content; gap: 32px 36px; justify-content: center; }
.use.light { background: #e9e8ee; color: #15111c; }
.use.dark { background: #1b1922; color: #ece8f2; }
.phone { width: 236px; height: 480px; border-radius: 38px; padding: 16px 16px 12px; display: flex; flex-direction: column; border: 5px solid #26232d; }
.light .phone { background: linear-gradient(160deg, #f4f1fa, #d9d4e6 60%%, #c9c6dc); border-color: #c9c6d2; }
.dark .phone { background: linear-gradient(160deg, #1a1622, #0d0b12 60%%, #15101f); }
.status { display: flex; justify-content: space-between; font: 600 10px/1 ui-sans-serif, system-ui, sans-serif; padding: 2px 8px 16px; opacity: .8; }
.apps { display: grid; grid-template-columns: repeat(4, 42px); justify-content: space-between; gap: 14px 0; }
.app { display: grid; justify-items: center; gap: 4px; font: 500 8px/1 ui-sans-serif, system-ui, sans-serif; white-space: nowrap; }
.app i { display: block; width: 42px; height: 42px; border-radius: 23%%; }
.app b { display: block; width: 26px; height: 4px; border-radius: 2px; background: currentColor; opacity: .28; margin-top: 2px; }
.tray { margin-top: auto; display: grid; grid-template-columns: repeat(4, 36px); justify-content: space-between; padding: 10px 12px; border-radius: 20px; }
.tray i { display: block; width: 36px; height: 36px; border-radius: 23%%; }
.light .tray, .light .dock { background: rgba(255,255,255,.55); }
.dark .tray, .dark .dock { background: rgba(255,255,255,.1); }
.dock { display: flex; gap: 10px; padding: 9px 11px; border-radius: 16px; width: max-content; }
.dock i { display: block; width: 40px; height: 40px; border-radius: 23%%; }
.tabs { display: flex; align-items: flex-end; height: 34px; padding: 0 8px; border-radius: 8px 8px 0 0; font: 11px/1 ui-sans-serif, system-ui, sans-serif; width: max-content; }
.light .tabs { background: #dee1e6; }
.dark .tabs { background: #35363a; }
.tab { display: flex; align-items: center; gap: 7px; height: 27px; padding: 0 22px 0 10px; border-radius: 7px 7px 0 0; }
.light .tab.on { background: #fff; }
.dark .tab.on { background: #202124; }
.tab.off { opacity: .7; }
.tab s { display: block; width: 16px; height: 16px; border-radius: 4px; background: currentColor; opacity: .3; }
.note { font: 11px/1.3 ui-monospace, monospace; opacity: .6; }
""" % dict(pad=PADDING, width=WIDTH)

# Stand-ins for other apps in the mockups: plain tiles, no real brands.
OTHER_APPS = ["#e5484d", "#f5a524", "#30a46c", "#0091ff", "#8e8e93", "#e93d82", "#12a594", "#3e63dd", "#f76b15", "#6e56cf", "#46a758"]
ZOZO_SLOT = 5  # where the Zozo icon sits among the others on a home screen


def _sized(px):
    return f' width="{px}" height="{px}"'


def _panel(ground, ink, body):
    return f'<div class="panel" style="background:{COLORS[ground]};color:{COLORS[ink]}">{body}</div>'


def _phone(spec):
    """A phone home screen with the icon among other apps and in the tray."""
    cells = []
    for i in range(12):
        if i == ZOZO_SLOT:
            cells.append(f'<div class="app">{svg.icon(**spec, attrs=_sized(42))}Zozo Chat</div>')
        else:
            cells.append(f'<div class="app"><i style="background:{OTHER_APPS[i % len(OTHER_APPS)]}"></i><b></b></div>')
    tray = "".join(f'<i style="background:{c}"></i>' for c in OTHER_APPS[3:6]) + svg.icon(**spec, attrs=_sized(36))
    return (
        '<div class="phone"><div class="status"><span>9:41</span><span>●●●</span></div>'
        f'<div class="apps">{"".join(cells)}</div><div class="tray">{tray}</div></div>'
    )


def _dock(key, spec):
    """A desktop dock with the icon in place."""
    others = [f'<i style="background:{c}"></i>' for c in OTHER_APPS[:5]]
    row = "".join(others[:2]) + svg.icon(**spec, attrs=_sized(40)) + "".join(others[2:])
    return f'<div><div class="note" style="margin-bottom:8px">icon/{key}.svg</div><div class="dock">{row}</div></div>'


def _tab_strip(theme):
    """A browser tab strip with the favicon as it shows in that theme."""
    favicon = svg.symbol(COLORS[FAVICON[theme]], attrs=_sized(16))
    tabs = (
        '<div class="tab off"><s></s>Inbox</div>'
        f'<div class="tab on">{favicon}Zozo Chat</div>'
        '<div class="tab off"><s></s>Docs</div>'
    )
    return f'<div style="grid-column:1/-1"><div class="note" style="margin-bottom:8px">favicon/favicon.svg</div><div class="tabs">{tabs}</div></div>'


def html() -> str:
    marks = [brand_wordmark(name) for name in config.NAMES]
    out = ["<h1>Colours</h1>", '<div class="swatches">']
    for name, value in COLORS.items():
        out.append(f'<div><div class="swatch" style="background:{value}"></div><div class="cap"><b>{name}</b><br>{value.upper()}</div></div>')
    out.append("</div>")

    out.append("<h1>Icon <span>· the flower on a tile, with its own colours. Normal and alternate.</span></h1>")
    out.append('<div class="row" style="grid-template-columns:1fr 1fr">')
    for ground, ink in (("mist", "ink"), ("night", "white")):
        items = ""
        for key, spec in ICONS.items():
            sizes = "".join(svg.icon(**spec, attrs=_sized(px)) for px in (140, 48, 32, 16))
            items += f'<div><div class="items" style="gap:18px">{sizes}</div><div class="cap">{key}.svg</div></div>'
        out.append(_panel(ground, ink, f'<div class="items">{items}</div>'))
    out.append("</div>")

    out.append("<h1>Symbol <span>· the flower alone, one flat colour. Black or white by default; violet on light and lilac on dark as the brand colour.</span></h1>")
    out.append('<div class="row" style="grid-template-columns:repeat(4,1fr)">')
    for ground, ink in (("mist", "ink"), ("mist", "violet"), ("night", "white"), ("night", "lilac")):
        sizes = "".join(svg.symbol(attrs=_sized(px)) for px in (140, 48, 32, 16))
        out.append(_panel(ground, ink, f'<div class="items" style="gap:18px">{sizes}</div><div class="cap">{ink} on {ground}</div>'))
    out.append("</div>")

    out.append(f"<h1>Lockups <span>· flower + name, in black or white only. Company name in one weight; product names with the second word at {config.PRODUCT_WEIGHT}.</span></h1>")
    out.append('<div class="row" style="grid-template-columns:1fr 1fr">')
    for ground, ink in (("mist", "ink"), ("night", "white")):
        large = "".join(svg.lockup(m, attrs=' height="64"') for m in marks)
        small = "".join(svg.lockup(m, attrs=f' height="{SMALL_PX}"') for m in marks)
        out.append(_panel(ground, ink, f'<div class="stack">{large}</div><div class="small">{small}</div>'))
    out.append("</div>")

    out.append("<h1>Hero lockups <span>· the lockup on a full field of colour. Normal and night.</span></h1>")
    out.append('<div class="heroes">')
    out += [svg.hero(m, **spec, attrs="") for m in marks for spec in HEROES.values()]
    out.append("</div>")

    out.append("<h1>In use <span>· the two icons on a phone home screen and in a desktop dock, and the favicon in a browser tab, in light and dark mode. The other apps are stand-ins.</span></h1>")
    out.append('<div class="uses">')
    for theme in ("light", "dark"):
        phones = "".join(_phone(spec) for spec in ICONS.values())
        docks = "".join(_dock(key, spec) for key, spec in ICONS.items())
        out.append(f'<div class="use {theme}">{phones}{docks}{_tab_strip(theme)}</div>')
    out.append("</div>")

    out.append("<h1>Wordmarks <span>· the names without the flower, in black or white only.</span></h1>")
    out.append('<div class="row" style="grid-template-columns:1fr 1fr">')
    for ground, ink in (("mist", "ink"), ("night", "white")):
        row = "".join(svg.wordmark(m, attrs=' height="34"') for m in marks)
        out.append(_panel(ground, ink, f'<div class="items" style="gap:30px 40px">{row}</div>'))
    out.append("</div>")
    return (
        '<!doctype html>\n<html lang="en"><meta charset="utf-8">\n<title>Zozo brand</title>\n'
        f"<style>{CSS}</style>\n" + "\n".join(out) + "\n</html>\n"
    )


def find_browser():
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome"):
        if shutil.which(name):
            return shutil.which(name)
    return None


def screenshot(page: str, png_path: Path, scale=2):
    """Render the sheet to a PNG with a headless Chromium-family browser."""
    browser = find_browser()
    if not browser:
        raise RuntimeError("a sheet PNG needs Chromium or Chrome on the PATH")
    base = [browser, "--headless", "--disable-gpu", "--hide-scrollbars"]
    window = WIDTH + 2 * PADDING
    with tempfile.TemporaryDirectory() as tmp:
        # First pass: have the page report its own height, so the picture can
        # be exactly as tall as the content.
        probe = Path(tmp) / "probe.html"
        probe.write_text(page + "<script>document.title = document.documentElement.scrollHeight</script>")
        dom = subprocess.run([*base, f"--window-size={window},1000", "--dump-dom", probe.as_uri()], check=True, capture_output=True, text=True).stdout
        found = re.search(r"<title>(\d+)</title>", dom)
        if not found:
            raise RuntimeError("could not measure the sheet's height")
        final = Path(tmp) / "sheet.html"
        final.write_text(page)
        subprocess.run(
            [*base, f"--force-device-scale-factor={scale}", f"--window-size={window},{found.group(1)}", f"--screenshot={png_path}", final.as_uri()],
            check=True,
            capture_output=True,
        )
