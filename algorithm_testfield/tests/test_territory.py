import math

import shapely.geometry as sg
from shapely.ops import unary_union

from celllayout_tf.cases import selected_cases
from celllayout_tf.schema import ShapeInput, ShapePart
from celllayout_tf.territory import (
    KIND_AXIS_ALIGNED,
    KIND_CURVED,
    KIND_ROTATED,
    Territory,
    part_kind,
    resolve_territories,
)


def _territory_area(t: Territory) -> float:
    total = 0.0
    for piece in t.pieces:
        poly = sg.Polygon(piece.exterior, [list(h) for h in piece.holes])
        total += poly.area
    return total


def test_part_kind_axis_aligned_rect():
    part = ShapePart(exterior=((0, 0), (12, 0), (12, 8), (0, 8)))
    assert part_kind(part) == KIND_AXIS_ALIGNED


def test_part_kind_rotated_rect():
    deg = 25.0
    rad = math.radians(deg)
    e0 = (0.0, 0.0)
    e1 = (5 * math.cos(rad), 5 * math.sin(rad))
    e2 = (e1[0] - 4 * math.sin(rad), e1[1] + 4 * math.cos(rad))
    e3 = (-4 * math.sin(rad), 4 * math.cos(rad))
    part = ShapePart(exterior=(e0, e1, e2, e3))
    assert part_kind(part) == KIND_ROTATED


def test_part_kind_disk_is_curved():
    disk = sg.Point(0, 0).buffer(5, quad_segs=32)
    verts = tuple((float(x), float(y)) for x, y in list(disk.exterior.coords)[:-1])
    part = ShapePart(exterior=verts)
    assert part_kind(part) == KIND_CURVED


def test_case_22_main_wins_over_wing():
    case = selected_cases([22])[0][2]
    territories = resolve_territories(case)

    main_t, wing_t = territories
    # main keeps its full 12x8 rectangle
    assert math.isclose(_territory_area(main_t), 96.0, abs_tol=1e-6)
    # wing's territory shrinks: 5*4 = 20 minus the part inside main
    wing_full_area = 5 * 4
    assert _territory_area(wing_t) < wing_full_area
    assert _territory_area(wing_t) > 0


def test_case_23_wings_win_over_main():
    case = selected_cases([23])[0][2]
    territories = resolve_territories(case)

    main_t, wing1_t, wing2_t = territories
    # main loses small chunks at its upper corners — area should be just under 96
    assert _territory_area(main_t) < 96.0
    assert _territory_area(main_t) > 90.0
    # each wing keeps its full rect (5*3 = 15)
    assert math.isclose(_territory_area(wing1_t), 15.0, abs_tol=1e-6)
    assert math.isclose(_territory_area(wing2_t), 15.0, abs_tol=1e-6)


def test_case_24_vertical_wins_over_rotated_bar():
    case = selected_cases([24])[0][2]
    territories = resolve_territories(case)

    bar_t, vertical_t = territories
    # vertical keeps its full 3*8 = 24 rect
    assert math.isclose(_territory_area(vertical_t), 24.0, abs_tol=1e-6)
    # bar loses its portion inside vertical
    bar_full_area = 8 * 3
    assert _territory_area(bar_t) < bar_full_area
    assert _territory_area(bar_t) > 0


def test_case_28_curved_l_disk_keeps_only_inner_fillet():
    case = selected_cases([28])[0][2]
    territories = resolve_territories(case)

    rect1_t, rect2_t, disk_t = territories
    # both rects keep their full area
    assert math.isclose(_territory_area(rect1_t), 4 * 14, abs_tol=1e-6)
    assert math.isclose(_territory_area(rect2_t), 9 * 4, abs_tol=1e-6)
    # disk only keeps the upper-right quarter (the fillet) ≈ π*r²/4 = π*16/4 ≈ 12.57
    quarter_area = math.pi * 16 / 4
    assert math.isclose(_territory_area(disk_t), quarter_area, rel_tol=0.05)


def test_total_territory_equals_footprint_union_area():
    for idx, _name, case in selected_cases():
        territories = resolve_territories(case)
        total_terr_area = sum(_territory_area(t) for t in territories)
        union = unary_union(
            [sg.Polygon(p.exterior, [list(h) for h in p.holes]) for p in case.parts]
        )
        assert math.isclose(total_terr_area, union.area, rel_tol=1e-6), idx


def test_territory_pieces_do_not_overlap_each_other_across_parts():
    for idx, _name, case in selected_cases():
        territories = resolve_territories(case)
        polys = []
        for t in territories:
            for piece in t.pieces:
                polys.append(sg.Polygon(piece.exterior, [list(h) for h in piece.holes]))
        # pairwise intersection area should be ~0 (parts are now disjoint)
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                inter = polys[i].intersection(polys[j])
                assert inter.area < 1e-6, (idx, i, j, inter.area)
