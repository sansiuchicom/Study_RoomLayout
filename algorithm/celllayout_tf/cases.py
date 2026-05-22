"""Testfield-only showcase ``ShapeInput`` cases.

These 33 synthetic footprints support diagnostics, docs, and regression tests.
They are not part of the portable RoomLayout algorithm core; production callers
should provide ``ShapeInput`` values directly.

The cases match the previous testfield iteration by index, name, and union
geometry. The difference: each case is expressed as a ``ShapeInput`` with parts
preserved (not unioned). Rotated wings, filleted shapes, and ㅁ-with-hole keep
their constituent primitives as separate ``ShapePart`` entries.
"""

from __future__ import annotations

import re
import unicodedata

import shapely.affinity as sa
import shapely.geometry as sg
from shapely.ops import unary_union

from .geometry import from_shapely as _from_shapely
from .schema import ShapeInput, ShapePart


def case_slug(index: int, name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_name).strip("_").lower()
    if not slug:
        slug = "case"
    return f"{index:02d}_{slug}"


def make_cases() -> list[ShapeInput]:
    return [
        _case_01_panhang(),
        _case_02_giyeok(),
        _case_03_4bay(),
        _case_04_digeut(),
        _case_05_tower(),
        _case_06_square(),
        _case_07_long_rect(),
        _case_08_tall_rect(),
        _case_09_giyeok_std(),
        _case_10_giyeok_thick(),
        _case_11_giyeok_thin(),
        _case_12_chil_std(),
        _case_13_sib_sym(),
        _case_14_sib_asym(),
        _case_15_t(),
        _case_16_mieum_small_hole(),
        _case_17_mieum_big_hole(),
        _case_18_rect_rot30(),
        _case_19_rect_rot60(),
        _case_20_giyeok_rot30(),
        _case_21_chil_rot45(),
        _case_22_main_wing25(),
        _case_23_mirror_wings(),
        _case_24_chil_angled(),
        _case_25_circle(),
        _case_26_ellipse(),
        _case_27_half_circle(),
        _case_28_curved_giyeok(),
        _case_29_e(),
        _case_30_zigzag(),
        _case_31_asym_giyeok(),
        _case_32_60_giyeok(),
        _case_33_mieum_wing(),
    ]


def selected_cases(
    indices: list[int] | None = None,
) -> list[tuple[int, str, ShapeInput]]:
    """Return ``(index, name, shape)`` tuples, 1-based indices."""
    all_cases = make_cases()
    if not indices:
        return [(idx, c.name, c) for idx, c in enumerate(all_cases, start=1)]
    return [
        (idx, all_cases[idx - 1].name, all_cases[idx - 1])
        for idx in indices
        if 1 <= idx <= len(all_cases)
    ]


# ---------- helpers ----------


def _rect_part(x0: float, y0: float, x1: float, y1: float) -> ShapePart:
    return ShapePart(exterior=((x0, y0), (x1, y0), (x1, y1), (x0, y1)))


def _rotated_rect(
    x0: float, y0: float, x1: float, y1: float,
    deg: float,
    origin: tuple[float, float] = (0, 0),
    translate: tuple[float, float] = (0, 0),
) -> ShapePart:
    poly = sa.rotate(sg.box(x0, y0, x1, y1), deg, origin=origin)
    if translate != (0, 0):
        poly = sa.translate(poly, xoff=translate[0], yoff=translate[1])
    return _from_shapely(poly)


def _rotate_boxes_around_union_centroid(
    boxes: list[tuple[float, float, float, float]], deg: float,
) -> tuple[ShapePart, ...]:
    polys = [sg.box(*b) for b in boxes]
    centroid = unary_union(polys).centroid
    return tuple(_from_shapely(sa.rotate(p, deg, origin=centroid)) for p in polys)


def _rect_with_hole(
    x0: float, y0: float, x1: float, y1: float,
    h_x0: float, h_y0: float, h_x1: float, h_y1: float,
) -> ShapePart:
    return ShapePart(
        exterior=((x0, y0), (x1, y0), (x1, y1), (x0, y1)),
        holes=(((h_x0, h_y0), (h_x0, h_y1), (h_x1, h_y1), (h_x1, h_y0)),),
    )


def _disk(cx: float, cy: float, r: float, quad_segs: int = 64) -> ShapePart:
    return _from_shapely(sg.Point(cx, cy).buffer(r, quad_segs=quad_segs))


def _ellipse(
    cx: float, cy: float, xfact: float, yfact: float, quad_segs: int = 64,
) -> ShapePart:
    unit = sg.Point(cx, cy).buffer(1, quad_segs=quad_segs)
    return _from_shapely(sa.scale(unit, xfact=xfact, yfact=yfact))


def _half_disk(cx: float, cy: float, r: float, quad_segs: int = 64) -> ShapePart:
    disk = sg.Point(cx, cy).buffer(r, quad_segs=quad_segs)
    return _from_shapely(disk.intersection(sg.box(cx - r, cy, cx + r, cy + r)))


# ---------- case builders ----------


def _case_01_panhang() -> ShapeInput:
    return ShapeInput("30평 판상형", (_rect_part(0, 0, 14, 10),))


def _case_02_giyeok() -> ShapeInput:
    return ShapeInput(
        "30평 ㄱ자",
        (_rect_part(0, 0, 8, 10), _rect_part(8, 0, 14, 7)),
    )


def _case_03_4bay() -> ShapeInput:
    return ShapeInput("40평 4-bay", (_rect_part(0, 0, 16, 10),))


def _case_04_digeut() -> ShapeInput:
    return ShapeInput(
        "50평 ㄷ자",
        (
            _rect_part(0, 0, 16, 3.8),
            _rect_part(0, 6.2, 16, 10),
            _rect_part(0, 3.8, 4, 6.2),
        ),
    )


def _case_05_tower() -> ShapeInput:
    return ShapeInput(
        "타워형",
        (
            _rect_part(0, 0, 10, 7),
            _rect_part(5, 3, 13, 11),
            _rect_part(10, 7, 15, 11),
        ),
    )


def _case_06_square() -> ShapeInput:
    return ShapeInput("Square 10x10", (_rect_part(0, 0, 10, 10),))


def _case_07_long_rect() -> ShapeInput:
    return ShapeInput("Long rect 20x6", (_rect_part(0, 0, 20, 6),))


def _case_08_tall_rect() -> ShapeInput:
    return ShapeInput("Tall rect 6x20", (_rect_part(0, 0, 6, 20),))


def _case_09_giyeok_std() -> ShapeInput:
    return ShapeInput(
        "ㄱ자 standard",
        (_rect_part(0, 0, 12, 5), _rect_part(0, 5, 5, 12)),
    )


def _case_10_giyeok_thick() -> ShapeInput:
    return ShapeInput(
        "ㄱ자 thick",
        (_rect_part(0, 0, 14, 5), _rect_part(0, 5, 6, 14)),
    )


def _case_11_giyeok_thin() -> ShapeInput:
    return ShapeInput(
        "ㄱ자 thin",
        (_rect_part(0, 0, 14, 3), _rect_part(0, 3, 3, 14)),
    )


def _case_12_chil_std() -> ShapeInput:
    return ShapeInput(
        "7자 standard",
        (_rect_part(0, 7, 14, 12), _rect_part(10, 0, 14, 7)),
    )


def _case_13_sib_sym() -> ShapeInput:
    return ShapeInput(
        "十자 symmetric",
        (_rect_part(0, 4, 14, 8), _rect_part(5, 0, 9, 12)),
    )


def _case_14_sib_asym() -> ShapeInput:
    return ShapeInput(
        "十자 asymmetric",
        (_rect_part(0, 4, 14, 7), _rect_part(6, 0, 9, 12)),
    )


def _case_15_t() -> ShapeInput:
    return ShapeInput(
        "T자",
        (_rect_part(0, 0, 14, 5), _rect_part(5, 5, 9, 12)),
    )


def _case_16_mieum_small_hole() -> ShapeInput:
    return ShapeInput(
        "ㅁ자 small hole",
        (_rect_with_hole(0, 0, 14, 10, 4.5, 3, 8.5, 6.5),),
    )


def _case_17_mieum_big_hole() -> ShapeInput:
    return ShapeInput(
        "ㅁ자 big hole",
        (_rect_with_hole(0, 0, 14, 10, 3, 3, 11, 7),),
    )


def _case_18_rect_rot30() -> ShapeInput:
    return ShapeInput(
        "Rect rotated 30°",
        (_rotated_rect(0, 0, 12, 8, 30, origin=(6, 4)),),
    )


def _case_19_rect_rot60() -> ShapeInput:
    return ShapeInput(
        "Rect rotated 60°",
        (_rotated_rect(0, 0, 12, 8, 60, origin=(6, 4)),),
    )


def _case_20_giyeok_rot30() -> ShapeInput:
    parts = _rotate_boxes_around_union_centroid(
        [(0, 0, 12, 5), (0, 5, 5, 12)], 30,
    )
    return ShapeInput("ㄱ자 rotated 30°", parts)


def _case_21_chil_rot45() -> ShapeInput:
    parts = _rotate_boxes_around_union_centroid(
        [(0, 7, 12, 12), (8, 0, 12, 7)], 45,
    )
    return ShapeInput("7자 rotated 45°", parts)


def _case_22_main_wing25() -> ShapeInput:
    return ShapeInput(
        "Main + wing 25°",
        (
            _rect_part(0, 0, 12, 8),
            _rotated_rect(0, 0, 5, 4, 25, origin=(0, 0), translate=(9, 7)),
        ),
    )


def _case_23_mirror_wings() -> ShapeInput:
    return ShapeInput(
        "Mirror wings +/-30°",
        (
            _rect_part(0, 0, 12, 8),
            _rotated_rect(0, 0, 5, 3, 30, origin=(0, 0), translate=(-3, 6)),
            _rotated_rect(0, 0, 5, 3, -30, origin=(0, 0), translate=(10, 8)),
        ),
    )


def _case_24_chil_angled() -> ShapeInput:
    return ShapeInput(
        "7자 angled (-25 + 0°)",
        (
            _rotated_rect(0, 0, 8, 3, -25, origin=(0, 0), translate=(0, 8)),
            _rect_part(7, 0, 10, 8),
        ),
    )


def _case_25_circle() -> ShapeInput:
    return ShapeInput("Circle r=6", (_disk(0, 0, 6, quad_segs=64),))


def _case_26_ellipse() -> ShapeInput:
    return ShapeInput("Ellipse 10x6", (_ellipse(0, 0, 8, 4, quad_segs=64),))


def _case_27_half_circle() -> ShapeInput:
    return ShapeInput("Half circle", (_half_disk(0, 0, 6, quad_segs=64),))


def _case_28_curved_giyeok() -> ShapeInput:
    return ShapeInput(
        "Curved ㄱ",
        (
            _rect_part(0, 0, 4, 14),
            _rect_part(4, 0, 13, 4),
            _disk(4, 4, 4, quad_segs=32),
        ),
    )


def _case_29_e() -> ShapeInput:
    return ShapeInput(
        "E자",
        (
            _rect_part(0, 0, 5, 12),
            _rect_part(5, 0, 14, 3),
            _rect_part(5, 5, 14, 8),
            _rect_part(5, 10, 14, 12),
        ),
    )


def _case_30_zigzag() -> ShapeInput:
    return ShapeInput(
        "ㄹ자 (zigzag)",
        (
            _rect_part(0, 8, 14, 12),
            _rect_part(11, 0, 14, 12),
            _rect_part(0, 0, 11, 4),
        ),
    )


def _case_31_asym_giyeok() -> ShapeInput:
    return ShapeInput(
        "비대칭 ㄱ",
        (_rect_part(0, 0, 14, 3), _rect_part(0, 3, 2.2, 12)),
    )


def _case_32_60_giyeok() -> ShapeInput:
    return ShapeInput(
        "60평 큰 ㄱ자",
        (
            _rect_part(0, 0, 16, 12),
            _rect_part(16, 0, 22, 5),
            _rect_part(16, 6, 21, 10),
        ),
    )


def _case_33_mieum_wing() -> ShapeInput:
    return ShapeInput(
        "ㅁ자 + wing",
        (
            _rect_with_hole(0, 0, 12, 10, 3, 3, 7, 7),
            _rect_part(8, 5, 15, 9),
        ),
    )
