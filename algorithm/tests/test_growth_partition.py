"""Tests for growth_partition.region_partition_growth (Phase 7 Round 4 v2 W7)."""

from __future__ import annotations

import shapely.geometry as sg

from celllayout_tf.cases import make_cases
from celllayout_tf.growth_partition import (
    _guillotine_partition,
    reflex_vertices_local,
    region_partition_growth,
    vertex_cells_of_piece,
)
from celllayout_tf.layout_fixtures import make_fixtures


def _all_cases_and_fixtures():
    cases = {c.name: c for c in make_cases()}
    return [(cases[f.case_name], f) for f in make_fixtures()]


# ---------- reflex_vertices_local ----------


def test_reflex_no_vertex_in_simple_rect():
    from celllayout_tf.schema import ShapePart
    rect = ShapePart(exterior=((0, 0), (4, 0), (4, 2), (0, 2)))
    assert reflex_vertices_local(rect, 0.0) == []


def test_reflex_one_vertex_in_l_shape():
    from celllayout_tf.schema import ShapePart
    # L: outer 4x4 minus top-right 2x2
    l = ShapePart(exterior=((0, 0), (4, 0), (4, 2), (2, 2), (2, 4), (0, 4)))
    reflex = reflex_vertices_local(l, 0.0)
    assert len(reflex) == 1
    assert reflex[0] == (2.0, 2.0)


def test_reflex_includes_hole_vertices():
    from celllayout_tf.schema import ShapePart
    # 14x10 rect with 4x4 hole in center
    rect_with_hole = ShapePart(
        exterior=((0, 0), (14, 0), (14, 10), (0, 10)),
        holes=(((3, 3), (11, 3), (11, 7), (3, 7)),),
    )
    reflex = reflex_vertices_local(rect_with_hole, 0.0)
    # 4 hole vertices = reflex from interior
    reflex_set = {(round(x, 6), round(y, 6)) for x, y in reflex}
    assert (3.0, 3.0) in reflex_set
    assert (11.0, 3.0) in reflex_set
    assert (11.0, 7.0) in reflex_set
    assert (3.0, 7.0) in reflex_set


# ---------- vertex_cells_of_piece ----------


def test_vertex_cells_rect_returns_one_cell():
    from celllayout_tf.schema import ShapePart
    rect = ShapePart(exterior=((0, 0), (4, 0), (4, 2), (0, 2)))
    cells = vertex_cells_of_piece(rect, 0.0)
    assert len(cells) == 1
    # Original rect area = 8
    assert abs(cells[0].area - 8.0) < 1e-6


def test_vertex_cells_l_shape_returns_three_cells():
    """An L with 1 reflex generates 1 vertical + 1 horizontal cut → 3 sub-rects."""
    from celllayout_tf.schema import ShapePart
    l = ShapePart(exterior=((0, 0), (4, 0), (4, 2), (2, 2), (2, 4), (0, 4)))
    cells = vertex_cells_of_piece(l, 0.0)
    # L = 12 (4×2 + 2×2). After cuts at x=2 and y=2, we get 3 sub-rects
    # of total area 12.
    assert len(cells) == 3
    total = sum(c.area for c in cells)
    assert abs(total - 12.0) < 1e-6


# ---------- _guillotine_partition ----------


def test_guillotine_single_seed_takes_all_regions():
    seeds = [(100, sg.Point(2, 1))]
    regions = [(0, sg.Point(1, 1)), (1, sg.Point(3, 1))]
    result = _guillotine_partition((0, 0, 4, 2), seeds, regions)
    assert result == {100: [0, 1]}


def test_guillotine_two_seeds_horizontal_spread_vertical_cut():
    """Wide cell with horizontally-spread seeds → vertical cut between them."""
    seeds = [(10, sg.Point(1, 1)), (20, sg.Point(3, 1))]
    regions = [
        (100, sg.Point(0.5, 1)),
        (200, sg.Point(1.5, 1)),
        (300, sg.Point(2.5, 1)),
        (400, sg.Point(3.5, 1)),
    ]
    result = _guillotine_partition((0, 0, 4, 2), seeds, regions)
    assert set(result.keys()) == {10, 20}
    # Cut at x=2 (midpoint between seeds 1 and 3)
    # Regions with x < 2 → seed 10; x >= 2 → seed 20
    assert set(result[10]) == {100, 200}
    assert set(result[20]) == {300, 400}


def test_guillotine_two_seeds_vertical_spread_horizontal_cut():
    """Tall cell with vertically-spread seeds → horizontal cut between them."""
    seeds = [(10, sg.Point(1, 1)), (20, sg.Point(1, 5))]
    regions = [
        (100, sg.Point(1, 0.5)),
        (200, sg.Point(1, 1.5)),
        (300, sg.Point(1, 4.5)),
        (400, sg.Point(1, 5.5)),
    ]
    result = _guillotine_partition((0, 0, 2, 6), seeds, regions)
    assert set(result.keys()) == {10, 20}
    assert set(result[10]) == {100, 200}
    assert set(result[20]) == {300, 400}


def test_guillotine_aspect_minimizing_picks_better_cut():
    """Wide 8x4 cell with seeds diagonal: 1st cut should be vertical (long axis).

    Seeds at (2, 1) and (6, 3): both x-spread and y-spread exist.
      x-cut at x=4 → 2 sub-rects 4×4 each, aspect 1.0
      y-cut at y=2 → 2 sub-rects 8×2 each, aspect 4.0
    Min-aspect picks x-cut.
    """
    seeds = [(10, sg.Point(2, 1)), (20, sg.Point(6, 3))]
    regions = [
        (100, sg.Point(1, 1)),
        (200, sg.Point(7, 3)),
    ]
    result = _guillotine_partition((0, 0, 8, 4), seeds, regions)
    # Seeds split by x-cut (vertical) at x=4 → 100 goes to seed 10 (x=1<4),
    # 200 goes to seed 20 (x=7>=4).
    assert set(result[10]) == {100}
    assert set(result[20]) == {200}


def test_guillotine_4_seeds_2x2_grid_yields_4_quadrants():
    """4 seeds in 2x2 grid in 8x8 cell → 4 quadrant sub-rects."""
    seeds = [
        (10, sg.Point(2, 2)),
        (20, sg.Point(6, 2)),
        (30, sg.Point(2, 6)),
        (40, sg.Point(6, 6)),
    ]
    # One region per quadrant
    regions = [
        (1, sg.Point(1, 1)),  # bot-left quadrant → seed 10
        (2, sg.Point(7, 1)),  # bot-right → seed 20
        (3, sg.Point(1, 7)),  # top-left → seed 30
        (4, sg.Point(7, 7)),  # top-right → seed 40
    ]
    result = _guillotine_partition((0, 0, 8, 8), seeds, regions)
    assert set(result.keys()) == {10, 20, 30, 40}
    assert set(result[10]) == {1}
    assert set(result[20]) == {2}
    assert set(result[30]) == {3}
    assert set(result[40]) == {4}


# ---------- region_partition_growth end-to-end ----------


def test_partition_growth_runs_on_every_fixture():
    for shape, fixture in _all_cases_and_fixtures():
        result = region_partition_growth(shape, fixture)
        assert len(result.rooms) == fixture.K


def test_partition_growth_each_region_assigned_at_most_once():
    for shape, fixture in _all_cases_and_fixtures()[:8]:
        result = region_partition_growth(shape, fixture)
        seen: set[int] = set()
        for room in result.rooms:
            for rid in room.region_ids:
                assert rid not in seen
                seen.add(rid)


def test_partition_growth_is_deterministic():
    shape, fixture = _all_cases_and_fixtures()[0]
    r1 = region_partition_growth(shape, fixture)
    r2 = region_partition_growth(shape, fixture)
    assert r1.unassigned_region_ids == r2.unassigned_region_ids
    for a, b in zip(r1.rooms, r2.rooms):
        assert a.region_ids == b.region_ids


def test_partition_growth_no_disconnected_rooms_in_simple_cases():
    """For pieces with no reflex (rect footprints), all rooms should be
    rect-equivalent."""
    from celllayout_tf.shape_gate import _reflex_of_union, _REFLEX_INVALID
    from celllayout_tf.regionize import regionize
    from celllayout_tf.territory import resolve_territories
    # case 1 is a single rect
    cases = {c.name: c for c in make_cases()}
    fixtures = make_fixtures()
    shape, fixture = cases[fixtures[0].case_name], fixtures[0]
    result = region_partition_growth(shape, fixture)
    regs = regionize(shape)
    by_id = {r.region_id: r for r in regs}
    terrs = resolve_territories(shape)
    kind_by_part = {t.part_id: t.kind for t in terrs}
    for room in result.rooms:
        if not room.region_ids:
            continue
        kinds = {kind_by_part.get(by_id[rid].part_id) for rid in room.region_ids}
        if "curved" in kinds:
            continue
        theta = by_id[room.region_ids[0]].theta
        refl = _reflex_of_union(room.region_ids, by_id, theta)
        if refl == _REFLEX_INVALID:
            continue
        # In simple rect case 1, expect reflex == 0 (rect) — guillotine guarantees
        assert refl == 0, (
            f"room {room.name} has reflex={refl} in simple rect case"
        )
