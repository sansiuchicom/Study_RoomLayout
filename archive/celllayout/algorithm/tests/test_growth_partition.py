"""Tests for growth_partition.region_partition_growth."""

from __future__ import annotations

import shapely.geometry as sg

from celllayout_tf.growth_partition import (
    _guillotine_partition,
    reflex_vertices_local,
    region_partition_growth,
    vertex_cells_of_piece,
)


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
    rect_with_hole = ShapePart(
        exterior=((0, 0), (14, 0), (14, 10), (0, 10)),
        holes=(((3, 3), (11, 3), (11, 7), (3, 7)),),
    )
    reflex = reflex_vertices_local(rect_with_hole, 0.0)
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
    assert abs(cells[0].area - 8.0) < 1e-6


def test_vertex_cells_l_shape_returns_three_cells():
    """An L with one reflex generates one vertical and one horizontal cut."""
    from celllayout_tf.schema import ShapePart
    l = ShapePart(exterior=((0, 0), (4, 0), (4, 2), (2, 2), (2, 4), (0, 4)))
    cells = vertex_cells_of_piece(l, 0.0)
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
    seeds = [(10, sg.Point(1, 1)), (20, sg.Point(3, 1))]
    regions = [
        (100, sg.Point(0.5, 1)),
        (200, sg.Point(1.5, 1)),
        (300, sg.Point(2.5, 1)),
        (400, sg.Point(3.5, 1)),
    ]
    result = _guillotine_partition((0, 0, 4, 2), seeds, regions)
    assert set(result.keys()) == {10, 20}
    assert set(result[10]) == {100, 200}
    assert set(result[20]) == {300, 400}


def test_guillotine_two_seeds_vertical_spread_horizontal_cut():
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
    seeds = [(10, sg.Point(2, 1)), (20, sg.Point(6, 3))]
    regions = [
        (100, sg.Point(1, 1)),
        (200, sg.Point(7, 3)),
    ]
    result = _guillotine_partition((0, 0, 8, 4), seeds, regions)
    assert set(result[10]) == {100}
    assert set(result[20]) == {200}


def test_guillotine_4_seeds_2x2_grid_yields_4_quadrants():
    seeds = [
        (10, sg.Point(2, 2)),
        (20, sg.Point(6, 2)),
        (30, sg.Point(2, 6)),
        (40, sg.Point(6, 6)),
    ]
    regions = [
        (1, sg.Point(1, 1)),
        (2, sg.Point(7, 1)),
        (3, sg.Point(1, 7)),
        (4, sg.Point(7, 7)),
    ]
    result = _guillotine_partition((0, 0, 8, 8), seeds, regions)
    assert set(result.keys()) == {10, 20, 30, 40}
    assert set(result[10]) == {1}
    assert set(result[20]) == {2}
    assert set(result[30]) == {3}
    assert set(result[40]) == {4}


# ---------- region_partition_growth end-to-end ----------


def test_partition_growth_runs_on_every_fixture(growth_cases):
    for case in growth_cases:
        assert len(case.growth.rooms) == case.fixture.K


def test_partition_growth_each_region_assigned_at_most_once(growth_cases):
    for case in growth_cases[:8]:
        seen: set[int] = set()
        for room in case.growth.rooms:
            for rid in room.region_ids:
                assert rid not in seen
                seen.add(rid)


def test_partition_growth_is_deterministic(growth_cases):
    case = growth_cases[0]
    result = region_partition_growth(case.shape, case.fixture)
    assert case.growth.unassigned_region_ids == result.unassigned_region_ids
    for a, b in zip(case.growth.rooms, result.rooms):
        assert a.region_ids == b.region_ids


def test_partition_growth_no_disconnected_rooms_in_simple_cases(growth_cases):
    """For pieces with no reflex, all rooms should be rect-equivalent."""
    from celllayout_tf.shape_gate import _reflex_of_union, _REFLEX_INVALID
    from celllayout_tf.regionize import regionize
    from celllayout_tf.territory import resolve_territories

    case = growth_cases[0]
    regs = regionize(case.shape)
    by_id = {r.region_id: r for r in regs}
    terrs = resolve_territories(case.shape)
    kind_by_part = {t.part_id: t.kind for t in terrs}
    for room in case.growth.rooms:
        if not room.region_ids:
            continue
        kinds = {kind_by_part.get(by_id[rid].part_id) for rid in room.region_ids}
        if "curved" in kinds:
            continue
        theta = by_id[room.region_ids[0]].theta
        refl = _reflex_of_union(room.region_ids, by_id, theta)
        if refl == _REFLEX_INVALID:
            continue
        assert refl == 0, (
            f"room {room.name} has reflex={refl} in simple rect case"
        )
