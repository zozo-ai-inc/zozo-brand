"""Outline geometry: Bezier helpers and corner rounding.

Points are complex numbers. A segment is a tuple of 2 points (a line) or 4 (a
cubic); quadratics are raised to cubics on the way in, which is exact. A
contour is a closed list of segments.
"""

from __future__ import annotations

import cmath
import math

import pathops
from fontTools.pens.recordingPen import DecomposingRecordingPen

# A join where the outline turns by less than this is a smooth curve join, not
# a corner. Geist's smooth joins are well under 1 degree, its real corners
# over 45, so the exact value is not sensitive.
CORNER_MIN_TURN = math.radians(12)


def seg_point(seg, t):
    if len(seg) == 2:
        return seg[0] + (seg[1] - seg[0]) * t
    a, b, c, d = seg
    u = 1 - t
    return u * u * u * a + 3 * u * u * t * b + 3 * u * t * t * c + t * t * t * d


def seg_tangent(seg, t):
    """Unit direction of travel at t, tolerant of coincident control points."""
    if len(seg) == 2:
        v = seg[1] - seg[0]
    else:
        a, b, c, d = seg
        u = 1 - t
        v = 3 * u * u * (b - a) + 6 * u * t * (c - b) + 3 * t * t * (d - c)
        if abs(v) < 1e-9:
            v = (c - a) if t < 0.5 else (d - b)
        if abs(v) < 1e-9:
            v = d - a
    return v / abs(v) if abs(v) > 1e-12 else 1 + 0j


def seg_split(seg, t):
    if len(seg) == 2:
        m = seg_point(seg, t)
        return (seg[0], m), (m, seg[1])
    a, b, c, d = seg
    ab, bc, cd = a + (b - a) * t, b + (c - b) * t, c + (d - c) * t
    abc, bcd = ab + (bc - ab) * t, bc + (cd - bc) * t
    m = abc + (bcd - abc) * t
    return (a, ab, abc, m), (m, bcd, cd, d)


_ARC_STEPS = 64


def _arc_table(seg):
    pts = [seg_point(seg, i / _ARC_STEPS) for i in range(_ARC_STEPS + 1)]
    acc, out = 0.0, [0.0]
    for p, q in zip(pts, pts[1:]):
        acc += abs(q - p)
        out.append(acc)
    return out


def seg_length(seg):
    return abs(seg[1] - seg[0]) if len(seg) == 2 else _arc_table(seg)[-1]


def seg_t_at(seg, s):
    """Parameter t at arc length s from the start."""
    if len(seg) == 2:
        length = abs(seg[1] - seg[0])
        return min(max(s / length, 0.0), 1.0) if length else 0.0
    table = _arc_table(seg)
    if s <= 0:
        return 0.0
    if s >= table[-1]:
        return 1.0
    for i in range(_ARC_STEPS):
        if table[i + 1] >= s:
            span = table[i + 1] - table[i]
            return (i + ((s - table[i]) / span if span else 0)) / _ARC_STEPS
    return 1.0


# --------------------------------------------------------------------------
# An edge is the run of segments between two corners.


def edge_length(edge):
    return sum(seg_length(s) for s in edge)


def edge_at(edge, s):
    """Point and direction of travel at arc length s along an edge."""
    for i, seg in enumerate(edge):
        length = seg_length(seg)
        if s <= length or i == len(edge) - 1:
            t = seg_t_at(seg, s)
            return seg_point(seg, t), seg_tangent(seg, t)
        s -= length


def edge_trim(edge, a, b):
    """Drop arc length a from the start of an edge and b from its end."""
    total = edge_length(edge)
    lo, hi = a, total - b
    if hi - lo < 1e-6:
        return []
    out, pos = [], 0.0
    for seg in edge:
        length = seg_length(seg)
        s0, s1 = max(lo - pos, 0.0), min(hi - pos, length)
        pos += length
        if s1 - s0 < 1e-9:
            continue
        t0, t1 = seg_t_at(seg, s0), seg_t_at(seg, s1)
        if t1 < 1:
            seg = seg_split(seg, t1)[0]
        if t0 > 0:
            seg = seg_split(seg, t0 / t1 if t1 else 0)[1]
        out.append(seg)
    return out


def turn_angle(t_in, t_out):
    """Signed turn from one direction to the next; positive is anticlockwise."""
    return cmath.phase(t_out / t_in)


def fillet(p1, t1, p2, t2):
    """Cubic from p1 (heading t1) to p2 (heading t2).

    Between two straight edges trimmed by the same amount this is the standard
    four-thirds-tan approximation of a circular arc, off a true arc by under
    0.03% of the radius at 90 degrees. Where an edge is curved it is a smooth
    blend that is tangent to both edges but not exactly circular.
    """
    chord = abs(p2 - p1)
    phi = abs(turn_angle(t1, t2))
    if chord < 1e-6 or phi < 1e-3:
        return (p1, p2)
    radius = chord / (2 * math.sin(phi / 2))
    h = 4 / 3 * math.tan(phi / 4) * radius
    return (p1, p1 + t1 * h, p2 - t2 * h, p2)


def signed_area(contour):
    area = 0.0
    for seg in contour:
        pts = [seg_point(seg, i / 8) for i in range(9)] if len(seg) == 4 else seg
        for p, q in zip(pts, pts[1:]):
            area += (p.real * q.imag - q.real * p.imag) / 2
    return area


def find_corners(contour):
    """Indices i where the join between segment i-1 and segment i is a corner,
    with the signed turn at each."""
    out = []
    for i, seg in enumerate(contour):
        turn = turn_angle(seg_tangent(contour[i - 1], 1), seg_tangent(seg, 0))
        if abs(turn) >= CORNER_MIN_TURN:
            out.append((i, turn))
    return out


def round_contour(contour, r_outer, r_inner, ink_left):
    """Round the corners of one closed contour.

    Each corner is cut back along both of its edges by the distance that a
    circle of the requested radius would need, then bridged with a fillet. If
    the two corners at either end of an edge ask for more than the edge has,
    both are scaled back in proportion, so the radius requested is a maximum:
    a stroke end narrower than twice the radius becomes a full semicircle and
    goes no further. When the two corners are of different kinds the outside
    corner is served first and the notch gets what is left, so that the two
    corners of a stroke end always match.
    """
    corners = find_corners(contour)
    if not corners or (r_outer <= 0 and r_inner <= 0):
        return contour
    n = len(corners)
    # edges[k] runs from corner k to corner k+1
    edges = []
    for k, (start, _) in enumerate(corners):
        end = corners[(k + 1) % n][0]
        idx = list(range(start, end)) if end > start else list(range(start, len(contour))) + list(range(end))
        edges.append([contour[i] for i in idx])
    lengths = [edge_length(e) for e in edges]

    want, convex = [], []
    for _, turn in corners:
        convex.append((turn > 0) == ink_left)
        r = r_outer if convex[-1] else r_inner
        want.append(r * math.tan(abs(turn) / 2) if r > 0 else 0.0)
    # allow[k] is what edge k grants to the corner at its (start, end)
    allow = []
    for k in range(n):
        j = (k + 1) % n
        a, b, length = want[k], want[j], lengths[k]
        if a + b > length:
            if convex[k] == convex[j]:
                a, b = a * length / (a + b), b * length / (a + b)
            elif convex[k]:
                a = min(a, length)
                b = length - a
            else:
                b = min(b, length)
                a = length - b
        allow.append((a, b))
    cut = [min(allow[k][0], allow[k - 1][1]) for k in range(n)]

    out = []
    for k in range(n):
        prev = edges[k - 1]
        if cut[k] > 1e-6:
            p1, t1 = edge_at(prev, lengths[k - 1] - cut[k])
            p2, t2 = edge_at(edges[k], cut[k])
            out.append(fillet(p1, t1, p2, t2))
        out.extend(edge_trim(edges[k], cut[k], cut[(k + 1) % n]))
    return out


def round_shape(contours, r_outer, r_inner):
    """Round every contour of one shape. The largest contour is taken as the
    outside, which fixes which way the ink lies for all of them."""
    ink_left = signed_area(max(contours, key=lambda c: abs(signed_area(c)))) > 0
    return [round_contour(c, r_outer, r_inner, ink_left) for c in contours]


# --------------------------------------------------------------------------
# Conversion to and from pathops paths, and out to SVG.


def path_contours(path, glyph_set=None):
    """Closed contours of a pathops path, as lines and cubics."""
    pen = DecomposingRecordingPen(glyph_set or {})
    path.draw(pen)

    contours, current, pos = [], [], 0j
    for op, args in pen.value:
        if op == "qCurveTo" and args[-1] is None:
            # a closed TrueType contour with no on-curve points: the curve
            # passes through the midpoint of each neighbouring pair
            offs = [complex(x, y) for x, y in args[:-1]]
            pos = start = (offs[-1] + offs[0]) / 2
            current = []
            for j, ctrl in enumerate(offs):
                to = (ctrl + offs[(j + 1) % len(offs)]) / 2
                current.append((pos, pos + 2 / 3 * (ctrl - pos), to + 2 / 3 * (ctrl - to), to))
                pos = to
            continue
        pts = [complex(x, y) for x, y in args]
        if op == "moveTo":
            current, pos, start = [], pts[0], pts[0]
        elif op == "lineTo":
            current.append((pos, pts[0]))
            pos = pts[0]
        elif op == "qCurveTo":
            # split a TrueType run of off-curve points into single quadratics
            offs, end = pts[:-1], pts[-1]
            for j, ctrl in enumerate(offs):
                to = end if j == len(offs) - 1 else (ctrl + offs[j + 1]) / 2
                current.append((pos, pos + 2 / 3 * (ctrl - pos), to + 2 / 3 * (ctrl - to), to))
                pos = to
        elif op == "curveTo":
            current.append((pos, pts[0], pts[1], pts[2]))
            pos = pts[2]
        elif op in ("closePath", "endPath"):
            if abs(pos - start) > 1e-6:
                current.append((pos, start))
            current = [s for s in current if seg_length(s) > 1e-6]
            if current:
                contours.append(current)
    return contours


def contours_path(contours):
    """The reverse of path_contours."""
    path = pathops.Path()
    pen = path.getPen()
    for contour in contours:
        pen.moveTo((contour[0][0].real, contour[0][0].imag))
        for seg in contour:
            if len(seg) == 2:
                pen.lineTo((seg[1].real, seg[1].imag))
            else:
                pen.curveTo(*[(p.real, p.imag) for p in seg[1:]])
        pen.closePath()
    return path


def bounds(contours):
    """(x_min, y_min, x_max, y_max) of the ink."""
    xs, ys = [], []
    for contour in contours:
        for seg in contour:
            pts = [seg_point(seg, i / 16) for i in range(17)] if len(seg) == 4 else seg
            xs += [p.real for p in pts]
            ys += [p.imag for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def path_data(contours, place=lambda p: p, digits=2):
    """SVG path data for contours, each point passed through place() first."""

    def fmt(p):
        p = place(p)
        return f"{p.real:.{digits}f}".rstrip("0").rstrip(".") + " " + f"{p.imag:.{digits}f}".rstrip("0").rstrip(".")

    d = []
    for contour in contours:
        d.append("M" + fmt(contour[0][0]))
        for seg in contour:
            d.append("L" + fmt(seg[1]) if len(seg) == 2 else "C" + " ".join(fmt(p) for p in seg[1:]))
        d.append("Z")
    return "".join(d)
