"""Turn SVG into PNG and ICO."""

from __future__ import annotations

import struct

import resvg_py


def png(svg: str, width: int | None = None, height: int | None = None) -> bytes:
    """Render an SVG at the given width or height in pixels; the other side
    follows the drawing's proportions."""
    return bytes(resvg_py.svg_to_bytes(svg_string=svg, width=width, height=height))


def png_size(data: bytes) -> tuple[int, int]:
    """Width and height read from a PNG's header."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    return struct.unpack(">II", data[16:24])


def ico(pngs: list[bytes]) -> bytes:
    """Pack PNG images into one .ico file, which may store PNG data directly."""
    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = len(header) + 16 * len(pngs)
    entries, body = b"", b""
    for data in pngs:
        w, h = png_size(data)
        if w > 256 or h > 256:
            raise ValueError("an .ico image can be at most 256 pixels a side")
        entries += struct.pack("<BBBBHHII", w % 256, h % 256, 0, 0, 1, 32, len(data), offset + len(body))
        body += data
    return header + entries + body
