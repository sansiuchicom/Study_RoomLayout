"""Tests for stages/growth_cells.py cell decomposition + guillotine (Step 04 §4.8)."""

from __future__ import annotations

import shapely.geometry as sg

from room_layout.schema import ShapePart
from room_layout.stages.growth_cells import (
    _assign_to_cells,
    _guillotine_partition,
    _snap_to_region_edge,
    reflex_vertices_local,
    vertex_cells_of_piece,
)

_RECT = ShapePart(exterior=((0.0, 0.0), (4.0, 0.0), (4.0, 2.0), (0.0, 2.0)))
# L-shape: 4x2 bottom + 2x2 top-left, area 12, one reflex vertex at (2, 2)
_L = ShapePart(exterior=((0.0, 0.0), (4.0, 0.0), (4.0, 2.0), (2.0, 2.0), (2.0, 4.0), (0.0, 4.0)))


# ---------- reflex_vertices_local ----------


def test_reflex_rect_has_none():
    assert reflex_vertices_local(_RECT, 0.0) == []


def test_reflex_l_shape_has_one():
    reflex = reflex_vertices_local(_L, 0.0)
    assert len(reflex) == 1
    assert reflex[0] == (2.0, 2.0)


# ---------- vertex_cells_of_piece ----------


def test_vertex_cells_rect_is_single():
    cells = vertex_cells_of_piece(_RECT, 0.0)
    assert len(cells) == 1
    assert abs(cells[0].area - 8.0) < 1e-9


def test_vertex_cells_l_shape_splits_to_three():
    cells = vertex_cells_of_piece(_L, 0.0)
    assert len(cells) == 3
    assert abs(sum(c.area for c in cells) - 12.0) < 1e-6


# ---------- _assign_to_cells ----------


def test_assign_to_cells():
    cells = [sg.box(0, 0, 2, 2), sg.box(2, 0, 4, 2)]
    points = [(1, sg.Point(1, 1)), (2, sg.Point(3, 1)), (3, sg.Point(2, 1))]
    # (2,1) lies on both boundaries → resolves to the first covering cell
    assert _assign_to_cells(points, cells) == {0: [1, 3], 1: [2]}


# ---------- _snap_to_region_edge ----------


def test_snap_none_bboxes_returns_midpoint():
    assert _snap_to_region_edge(2.0, "x", None, [], 1.0, 3.0) == 2.0


def test_snap_lands_on_region_edge_in_range():
    bboxes = {1: (0.0, 0.0, 2.5, 2.0)}  # right edge x=2.5 ∈ (1,3)
    assert _snap_to_region_edge(2.0, "x", bboxes, [1], 1.0, 3.0) == 2.5


def test_snap_no_edge_in_range_returns_midpoint():
    bboxes = {1: (0.0, 0.0, 5.0, 2.0)}  # edges 0, 5 — neither ∈ (1,3)
    assert _snap_to_region_edge(2.0, "x", bboxes, [1], 1.0, 3.0) == 2.0


# ---------- _guillotine_partition ----------


def test_guillotine_single_seed_gets_all_regions():
    out = _guillotine_partition(
        (0.0, 0.0, 4.0, 2.0),
        seeds_in_cell=[(10, sg.Point(1, 1))],
        regions_in_cell=[(1, sg.Point(0.5, 1)), (2, sg.Point(3.5, 1))],
    )
    assert out == {10: [1, 2]}


def test_guillotine_two_seeds_vertical_split():
    out = _guillotine_partition(
        (0.0, 0.0, 4.0, 2.0),
        seeds_in_cell=[(10, sg.Point(1, 1)), (20, sg.Point(3, 1))],
        regions_in_cell=[(1, sg.Point(0.5, 1)), (2, sg.Point(3.5, 1))],
    )
    assert out == {10: [1], 20: [2]}
