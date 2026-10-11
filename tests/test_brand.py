"""Run with: .venv/bin/python -m unittest"""

import math
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from zozo_brand import assets, config, raster, sheet, svg
from zozo_brand.build import MARKER, build
from zozo_brand.geometry import bounds, round_contour, seg_point, signed_area
from zozo_brand.symbol import pinwheel, symbol_path
from zozo_brand.wordmark import BrandError, brand_wordmark
from zozo_brand.wordmark import build as build_wordmark


def square(side):
    pts = [0j, side + 0j, complex(side, side), complex(0, side)]
    return [(pts[i], pts[(i + 1) % 4]) for i in range(4)]


def area(contour, steps=200):
    """Enclosed area, sampled finely enough to measure a curve."""
    pts = [seg_point(seg, i / steps) for seg in contour for i in range(steps)]
    return abs(sum(p.real * q.imag - q.real * p.imag for p, q in zip(pts, pts[1:] + pts[:1])) / 2)


def luminance(hex_color):
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    hi, lo = sorted((luminance(config.COLORS[a]), luminance(config.COLORS[b])), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class Rounding(unittest.TestCase):
    def test_zero_radius_changes_nothing(self):
        shape = square(100)
        self.assertEqual(round_contour(shape, 0, 0, True), shape)

    def test_square_corners_become_quarter_circles(self):
        rounded = round_contour(square(100), 10, 10, True)
        self.assertEqual(len(rounded), 8)
        self.assertAlmostEqual(area(rounded), 100 * 100 - (4 - math.pi) * 10 * 10, delta=0.5)

    def test_radius_is_capped_by_the_edge(self):
        # asking for more than half the side gives a circle and no more
        rounded = round_contour(square(100), 80, 80, True)
        self.assertAlmostEqual(area(rounded), math.pi * 50 * 50, delta=5)
        self.assertEqual([round(v) for v in bounds([rounded])], [0, 0, 100, 100])


class Wordmarks(unittest.TestCase):
    def test_every_name_draws_cleanly(self):
        for name in config.NAMES:
            mark = brand_wordmark(name)
            self.assertEqual(mark.notes, [], name)
            self.assertGreater(mark.width, mark.height, name)

    def test_names_share_one_vertical_box(self):
        boxes = {(brand_wordmark(n).top, brand_wordmark(n).bottom) for n in config.NAMES}
        self.assertEqual(len(boxes), 1)

    def test_product_word_is_lighter_than_the_company_word(self):
        uniform = build_wordmark("zozo chat")
        contrasted = build_wordmark("zozo chat", tail_weight=config.PRODUCT_WEIGHT)
        ink = lambda mark: sum(signed_area(c) for glyph in mark.glyphs[4:] for c in glyph)
        self.assertLess(abs(ink(contrasted)), abs(ink(uniform)))
        self.assertEqual(uniform.glyphs[:4], contrasted.glyphs[:4])

    def test_missing_glyph_is_reported(self):
        with self.assertRaises(BrandError):
            build_wordmark("zozo 中")


class Symbol(unittest.TestCase):
    def test_fits_its_square(self):
        ET.fromstring(svg.symbol())
        numbers = [float(n) for n in symbol_path().replace("M", " ").replace("L", " ").replace("C", " ").replace("Z", " ").split()]
        self.assertGreaterEqual(min(numbers), 0)
        self.assertLessEqual(max(numbers), config.SYMBOL_SIZE)

    def test_overlapping_petals_are_refused(self):
        with self.assertRaises(BrandError):
            pinwheel(**{**config.PINWHEEL, "width": 900})


class Heroes(unittest.TestCase):
    def test_tight_hero_has_the_lockup_box_and_no_field(self):
        mark = brand_wordmark("zozo chat")
        for spec in config.HEROES.values():
            full, tight = svg.hero(mark, **spec), svg.hero(mark, **spec, tight=True)
            self.assertIn("<rect", full)
            self.assertNotIn("<rect", tight)
            self.assertNotIn(config.COLORS[spec["ground"]], tight)
            box = lambda s: ET.fromstring(s).get("viewBox")
            self.assertEqual(box(tight), box(svg.lockup(mark)))


class Colours(unittest.TestCase):
    def test_pairings_are_legible(self):
        for fg, bg in config.PAIRINGS:
            self.assertGreaterEqual(contrast(fg, bg), config.MIN_CONTRAST, f"{fg} on {bg}")

    def test_assets_use_only_palette_colours(self):
        palette = set(config.COLORS.values())
        for asset in assets.all_assets():
            for token in asset.svg.split('"'):
                if token.startswith("#"):
                    self.assertIn(token, palette, asset.path)


class Rasters(unittest.TestCase):
    def test_png_has_the_requested_size(self):
        self.assertEqual(raster.png_size(raster.png(svg.symbol("#000000"), width=64)), (64, 64))
        width, height = raster.png_size(raster.png(svg.lockup(brand_wordmark(config.COMPANY)), height=40))
        self.assertEqual(height, 40)
        self.assertGreater(width, height)

    def test_ico_lists_every_size(self):
        data = raster.ico([raster.png(svg.symbol("#000000"), width=px) for px in (16, 32)])
        self.assertEqual(data[:6], b"\x00\x00\x01\x00\x02\x00")
        self.assertEqual((data[6], data[22]), (16, 32))


class Build(unittest.TestCase):
    def build_into(self, folder, **options):
        build(folder, log=lambda _: None, **options)
        return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()}

    def test_writes_every_asset_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dist"
            first = self.build_into(out, rasters=False)
            for asset in assets.all_assets():
                self.assertIn(f"{asset.path}.svg", first)
            for name in ("brand-sheet.html", "colors.css", "colors.json", MARKER):
                self.assertIn(name, first)
            for path, data in first.items():
                if path.endswith(".svg"):
                    ET.fromstring(data)
            self.assertEqual(first, self.build_into(out, rasters=False))

    def test_rasters_and_favicon_fallbacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = self.build_into(Path(tmp) / "dist")
            self.assertIn("favicon/favicon.ico", files)
            self.assertEqual(raster.png_size(files["favicon/apple-touch-icon.png"]), (config.TOUCH_ICON_SIZE,) * 2)
            self.assertEqual(raster.png_size(files["icon/icon-512.png"]), (512, 512))
            self.assertEqual(raster.png_size(files["hero/zozo-chat-w1200.png"])[0], 1200)
            self.assertEqual(raster.png_size(files["lockup/zozo-chat-white-h128.png"])[1], 128)

    def test_refuses_to_empty_a_folder_it_did_not_make(self):
        with tempfile.TemporaryDirectory() as tmp:
            keep = Path(tmp) / "keep.txt"
            keep.write_text("mine")
            with self.assertRaises(SystemExit):
                build(Path(tmp), rasters=False, log=lambda _: None)
            self.assertEqual(keep.read_text(), "mine")

    def test_sheet_is_self_contained(self):
        page = sheet.html()
        self.assertNotIn("http://", page.replace("http://www.w3.org", ""))
        self.assertNotIn("https://", page)
        self.assertNotIn("<img", page)


if __name__ == "__main__":
    unittest.main()
