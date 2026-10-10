"""Command line: python -m zozo_brand

    build      write every artifact to dist/ (the default command)
    wordmark   outline one piece of text, for trying things out
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config, svg
from .build import build
from .wordmark import BrandError
from .wordmark import build as build_wordmark


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m zozo_brand", description="Generate the Zozo brand assets.")
    sub = ap.add_subparsers(dest="command")

    b = sub.add_parser("build", help="write every artifact (default)")
    b.add_argument("--out", type=Path, default=config.ROOT / "dist", help="output folder, emptied first (default: dist/)")
    b.add_argument("--no-rasters", action="store_true", help="SVG and HTML only; skips PNG and ICO")
    b.add_argument("--sheet-png", action="store_true", help="also render the brand sheet to a PNG (needs Chromium or Chrome)")

    w = sub.add_parser("wordmark", help="outline one piece of text and print or save the SVG")
    w.add_argument("text")
    w.add_argument("-o", "--output", type=Path, help="file to write (default: standard output)")
    w.add_argument("--weight", type=float, default=config.WEIGHT)
    w.add_argument("--tail-weight", type=float, default=None, help="weight for the words after the first")
    w.add_argument("--spacing", type=float, default=config.LETTER_SPACING, help="letter-spacing in em")
    w.add_argument("--round", type=float, default=config.ROUND_OUTER, dest="round_outer", help="outer corner radius")
    w.add_argument("--round-inner", type=float, default=config.ROUND_INNER)
    w.add_argument("--keep-dots", action="store_true", help="keep the dot on i")
    w.add_argument("--feature", action="append", default=None, metavar="TAG", help="OpenType feature to switch on (repeatable; replaces the defaults)")

    args = ap.parse_args(argv)
    try:
        if args.command == "wordmark":
            mark = build_wordmark(
                args.text,
                weight=args.weight,
                tail_weight=args.tail_weight,
                spacing=args.spacing,
                round_outer=args.round_outer,
                round_inner=args.round_inner,
                dotless_i=not args.keep_dots,
                features=config.FEATURES if args.feature is None else tuple(args.feature),
            )
            for note in mark.notes:
                print(f"note: {note}", file=sys.stderr)
            text = svg.wordmark(mark) + "\n"
            args.output.write_text(text) if args.output else sys.stdout.write(text)
        else:
            if args.command is None:
                args = b.parse_args([])
            build(args.out, rasters=not args.no_rasters, sheet_png=args.sheet_png)
    except (BrandError, RuntimeError) as error:
        raise SystemExit(f"error: {error}")


if __name__ == "__main__":
    main()
