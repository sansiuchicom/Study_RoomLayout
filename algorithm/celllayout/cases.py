"""Showcase footprint cases for zoning experiments."""
import shapely.affinity as sa
import shapely.geometry as sg
from shapely.ops import unary_union


def _clean(p):
    return p.buffer(0)


def _rot(p, deg):
    return sa.rotate(p, deg, origin=p.centroid)


def _xrot(box, deg, x, y):
    return sa.translate(sa.rotate(box, deg, origin=(0, 0)), xoff=x, yoff=y)


def make_cases():
    """33 documented footprint cases (name, polygon)."""
    box = sg.box
    union = unary_union
    L = lambda *bs: union(list(bs))
    cases = [
        # Korean apartments
        ("30평 판상형",  box(0, 0, 14, 10)),
        ("30평 ㄱ자",   L(box(0, 0, 8, 10), box(8, 0, 14, 7))),
        ("40평 4-bay",  box(0, 0, 16, 10)),
        ("50평 ㄷ자",   box(0, 0, 16, 10).difference(box(4, 3.8, 16, 6.2))),
        ("타워형",      L(box(0, 0, 10, 7), box(5, 3, 13, 11), box(10, 7, 15, 11))),
        # Simple rectangles
        ("Square 10x10",   box(0, 0, 10, 10)),
        ("Long rect 20x6", box(0, 0, 20, 6)),
        ("Tall rect 6x20", box(0, 0, 6, 20)),
        # ㄱ/7/十/T variants
        ("ㄱ자 standard", L(box(0, 0, 12, 5), box(0, 5, 5, 12))),
        ("ㄱ자 thick",    L(box(0, 0, 14, 5), box(0, 5, 6, 14))),
        ("ㄱ자 thin",     L(box(0, 0, 14, 3), box(0, 3, 3, 14))),
        ("7자 standard",  L(box(0, 7, 14, 12), box(10, 0, 14, 7))),
        ("十자 symmetric",  L(box(0, 4, 14, 8), box(5, 0, 9, 12))),
        ("十자 asymmetric", L(box(0, 4, 14, 7), box(6, 0, 9, 12))),
        ("T자",           L(box(0, 0, 14, 5), box(5, 5, 9, 12))),
        # ㅁ자 (with hole)
        ("ㅁ자 small hole", box(0, 0, 14, 10).difference(box(4.5, 3, 8.5, 6.5))),
        ("ㅁ자 big hole",   box(0, 0, 14, 10).difference(box(3, 3, 11, 7))),
        # Rotated single-axis
        ("Rect rotated 30°", _rot(box(0, 0, 12, 8), 30)),
        ("Rect rotated 60°", _rot(box(0, 0, 12, 8), 60)),
        ("ㄱ자 rotated 30°", _rot(L(box(0, 0, 12, 5), box(0, 5, 5, 12)), 30)),
        ("7자 rotated 45°",  _rot(L(box(0, 7, 12, 12), box(8, 0, 12, 7)), 45)),
        # Multi-axis
        ("Main + wing 25°",  L(box(0, 0, 12, 8), _xrot(box(0, 0, 5, 4), 25, 9, 7))),
        ("Mirror wings ±30°", L(box(0, 0, 12, 8),
                                 _xrot(box(0, 0, 5, 3),  30, -3, 6),
                                 _xrot(box(0, 0, 5, 3), -30, 10, 8))),
        ("7자 angled (-25 + 0°)", L(_xrot(box(0, 0, 8, 3), -25, 0, 8),
                                     box(7, 0, 10, 8))),
        # Curved
        ("Circle r=6",  sg.Point(0, 0).buffer(6, resolution=64)),
        ("Ellipse 10x6", sa.scale(sg.Point(0, 0).buffer(1, resolution=64),
                                    xfact=8, yfact=4)),
        ("Half circle", sg.Point(0, 0).buffer(6, resolution=64)
                          .intersection(box(-6, 0, 6, 6))),
        ("Curved ㄱ",   L(box(0, 0, 4, 14), box(4, 0, 13, 4),
                          sg.Point(4, 4).buffer(4, resolution=32)
                            .intersection(box(0, 0, 8, 8)))),
        # Complex
        ("E자",         box(0, 0, 14, 12).difference(
                          L(box(5, 3, 14, 5), box(5, 8, 14, 10)))),
        ("ㄹ자 (zigzag)", L(box(0, 8, 14, 12), box(11, 0, 14, 12),
                            box(0, 0, 11, 4))),
        ("비대칭 ㄱ",     L(box(0, 0, 14, 3), box(0, 3, 2.2, 12))),
        ("60평 큰 ㄱ자",  L(box(0, 0, 16, 12), box(16, 0, 22, 5),
                             box(16, 6, 21, 10))),
        ("ㅁ자 + wing",  L(box(0, 0, 12, 10).difference(box(3, 3, 7, 7)),
                            box(8, 5, 15, 9))),
    ]
    return [(name, _clean(p)) for name, p in cases]
