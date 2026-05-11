"""Showcase cases and a small legacy-style plotting API.

The original repository referenced this file from ``12_compare.py`` but did
not include it in the workspace. This version restores the 33 documented
footprint cases and enough of the old API for comparison plots to run.
"""
from __future__ import annotations

import numpy as np
import shapely.affinity as sa
import shapely.geometry as sg
from shapely.ops import unary_union


def _clean(poly):
    return poly.buffer(0)


def _rot(poly, deg):
    return sa.rotate(poly, deg, origin=poly.centroid)


def _case(name, poly):
    return name, _clean(poly)


def make_showcase_cases():
    """Return the 33 documented final zoning showcase footprints."""
    cases = []

    cases.append(_case("30평 판상형", sg.box(0, 0, 14, 10)))
    cases.append(_case("30평 ㄱ자", unary_union([sg.box(0, 0, 8, 10), sg.box(8, 0, 14, 7)])))
    cases.append(_case("40평 4-bay", sg.box(0, 0, 16, 10)))
    cases.append(_case("50평 ㄷ자", sg.box(0, 0, 16, 10).difference(sg.box(4, 3.8, 16, 6.2))))
    cases.append(_case("타워형", unary_union([sg.box(0, 0, 10, 7), sg.box(5, 3, 13, 11), sg.box(10, 7, 15, 11)])))
    cases.append(_case("Square 10x10", sg.box(0, 0, 10, 10)))
    cases.append(_case("Long rect 20x6", sg.box(0, 0, 20, 6)))
    cases.append(_case("Tall rect 6x20", sg.box(0, 0, 6, 20)))

    cases.append(_case("ㄱ자 standard", unary_union([sg.box(0, 0, 12, 5), sg.box(0, 5, 5, 12)])))
    cases.append(_case("ㄱ자 thick", unary_union([sg.box(0, 0, 14, 5), sg.box(0, 5, 6, 14)])))
    cases.append(_case("ㄱ자 thin", unary_union([sg.box(0, 0, 14, 3), sg.box(0, 3, 3, 14)])))
    cases.append(_case("7자 standard", unary_union([sg.box(0, 7, 14, 12), sg.box(10, 0, 14, 7)])))
    cases.append(_case("十자 symmetric", unary_union([sg.box(0, 4, 14, 8), sg.box(5, 0, 9, 12)])))
    cases.append(_case("十자 asymmetric", unary_union([sg.box(0, 4, 14, 7), sg.box(6, 0, 9, 12)])))
    cases.append(_case("T자", unary_union([sg.box(0, 0, 14, 5), sg.box(5, 5, 9, 12)])))

    cases.append(_case("ㅁ자 small hole", sg.box(0, 0, 14, 10).difference(sg.box(4.5, 3, 8.5, 6.5))))
    cases.append(_case("ㅁ자 big hole", sg.box(0, 0, 14, 10).difference(sg.box(3, 3, 11, 7))))
    cases.append(_case("Rect rotated 30°", _rot(sg.box(0, 0, 12, 8), 30)))
    cases.append(_case("Rect rotated 60°", _rot(sg.box(0, 0, 12, 8), 60)))
    cases.append(_case("ㄱ자 rotated 30°", _rot(unary_union([sg.box(0, 0, 12, 5), sg.box(0, 5, 5, 12)]), 30)))
    cases.append(_case("7자 rotated 45°", _rot(unary_union([sg.box(0, 7, 12, 12), sg.box(8, 0, 12, 7)]), 45)))

    main = sg.box(0, 0, 12, 8)
    wing25 = sa.translate(sa.rotate(sg.box(0, 0, 5, 4), 25, origin=(0, 0)), xoff=9, yoff=7)
    cases.append(_case("Main + wing 25°", unary_union([main, wing25])))
    left = sa.translate(sa.rotate(sg.box(0, 0, 5, 3), 30, origin=(0, 0)), xoff=-3, yoff=6)
    right = sa.translate(sa.rotate(sg.box(0, 0, 5, 3), -30, origin=(0, 0)), xoff=10, yoff=8)
    cases.append(_case("Mirror wings ±30°", unary_union([main, left, right])))
    angled = unary_union([
        sa.translate(sa.rotate(sg.box(0, 0, 8, 3), -25, origin=(0, 0)), xoff=0, yoff=8),
        sg.box(7, 0, 10, 8),
    ])
    cases.append(_case("7자 angled (-25 + 0°)", angled))

    cases.append(_case("Circle r=6", sg.Point(0, 0).buffer(6, resolution=64)))
    ellipse = sa.scale(sg.Point(0, 0).buffer(1, resolution=64), xfact=8, yfact=4)
    cases.append(_case("Ellipse 10x6", ellipse))
    half = sg.Point(0, 0).buffer(6, resolution=64).intersection(sg.box(-6, 0, 6, 6))
    cases.append(_case("Half circle", half))
    curved_l = unary_union([sg.box(0, 0, 4, 14), sg.box(4, 0, 13, 4), sg.Point(4, 4).buffer(4, resolution=32).intersection(sg.box(0, 0, 8, 8))])
    cases.append(_case("Curved ㄱ", curved_l))

    e_shape = sg.box(0, 0, 14, 12).difference(unary_union([sg.box(5, 3, 14, 5), sg.box(5, 8, 14, 10)]))
    cases.append(_case("E자", e_shape))
    zigzag = unary_union([sg.box(0, 8, 14, 12), sg.box(11, 0, 14, 12), sg.box(0, 0, 11, 4)])
    cases.append(_case("ㄹ자 (zigzag)", zigzag))
    asym_l = unary_union([sg.box(0, 0, 14, 3), sg.box(0, 3, 2.2, 12)])
    cases.append(_case("비대칭 ㄱ", asym_l))
    large = unary_union([
        sg.box(0, 0, 16, 12),
        sg.box(16, 0, 22, 5),
        sg.box(16, 6, 21, 10),
    ])
    cases.append(_case("60평 큰 ㄱ자", large))
    ring_wing = sg.box(0, 0, 12, 10).difference(sg.box(3, 3, 7, 7))
    wing = sg.box(8, 5, 15, 9)
    cases.append(_case("ㅁ자 + wing", unary_union([ring_wing, wing])))

    return cases


def _split_once(poly, k):
    if k <= 1:
        return [poly]
    minx, miny, maxx, maxy = poly.bounds
    if (maxx - minx) >= (maxy - miny):
        line = sg.LineString([(minx + (maxx - minx) / 2, miny - 1), (minx + (maxx - minx) / 2, maxy + 1)])
    else:
        line = sg.LineString([(minx - 1, miny + (maxy - miny) / 2), (maxx + 1, miny + (maxy - miny) / 2)])
    try:
        from shapely.ops import split
        parts = [p for p in split(poly, line).geoms if isinstance(p, sg.Polygon) and p.area > 0.01]
    except Exception:
        parts = []
    if len(parts) < 2:
        return [poly]
    parts.sort(key=lambda p: -p.area)
    return parts


def zone_footprint(footprint, k=None):
    """Small legacy baseline so 12_compare.py can run."""
    if k is None:
        k = max(2, min(10, round(footprint.area / 25.0)))
    pieces = [footprint]
    while len(pieces) < k:
        idx = max(range(len(pieces)), key=lambda i: pieces[i].area)
        split_parts = _split_once(pieces[idx], 2)
        if len(split_parts) < 2:
            break
        pieces.pop(idx)
        pieces.extend(split_parts)
    zones = [{"polygon": p, "zone_id": i, "cut_history": []} for i, p in enumerate(pieces)]
    return zones, [{"id": 0, "polygon": footprint, "theta": 0.0, "area": footprint.area}]


def plot_zone_result(footprint, zones, families, ax, title=""):
    colors = ['#9ad0c2', '#fdb462', '#a481c4', '#f4a3a3', '#88c4dc',
              '#c2d57a', '#e1a8d4', '#a8c8e1', '#ffd700', '#90ee90']
    for z in zones:
        poly = z["polygon"]
        x, y = poly.exterior.xy
        ax.fill(x, y, color=colors[z["zone_id"] % len(colors)], edgecolor="black", linewidth=1.0, alpha=0.75)
    x, y = footprint.exterior.xy
    ax.plot(x, y, color="black", linewidth=1.8)
    for hole in footprint.interiors:
        hx, hy = hole.xy
        ax.fill(hx, hy, color="#444", zorder=10)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.set_title(title, fontsize=9, fontweight="bold")


def zone_with_v12(footprint, k=None):
    from roomlayout_cell.zoning.pipeline12 import zone_footprint
    return zone_footprint(footprint, k=k)
