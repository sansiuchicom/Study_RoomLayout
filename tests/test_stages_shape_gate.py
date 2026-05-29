"""Tests for `stages/shape_gate.py` reflex helpers (Step 04 §4.3).

Known-good values mined from Cell's `test_shape_gate.py` (S03-D11 — written
fresh against the new schema, not copied wholesale).
"""

from __future__ import annotations

import shapely.geometry as sg

from room_layout.schema import ShapePart
from room_layout.stages.regionize import Region
from room_layout.stages.shape_gate import (
    _REFLEX_INVALID,
    _reflex_of_union,
    count_reflex_vertices,
)


def _mk_region(
    rid: int,
    exterior: tuple[tuple[float, float], ...],
    theta: float = 0.0,
    part_id: int = 0,
) -> Region:
    return Region(
        region_id=rid,
        shape=ShapePart(exterior=exterior),
        atom_ids=(),
        part_id=part_id,
        piece_id=0,
        theta=theta,
        cut_history=(),
    )


# ---------- count_reflex_vertices ----------


def test_reflex_count_axis_aligned_rect():
    poly = sg.Polygon([(0, 0), (4, 0), (4, 2), (0, 2)])
    assert count_reflex_vertices(poly) == 0


def test_reflex_count_l_shape():
    # L: 4x4 minus top-right 2x2 corner → 1 reflex
    poly = sg.Polygon([(0, 0), (4, 0), (4, 2), (2, 2), (2, 4), (0, 4)])
    assert count_reflex_vertices(poly) == 1


def test_reflex_count_t_shape():
    # T: horizontal bar + vertical stem → 2 reflex
    poly = sg.Polygon([(0, 0), (6, 0), (6, 2), (4, 2), (4, 4), (2, 4), (2, 2), (0, 2)])
    assert count_reflex_vertices(poly) == 2


def test_reflex_count_cross_shape():
    # +: 4 inside corners → 4 reflex
    poly = sg.Polygon(
        [
            (2, 0),
            (4, 0),
            (4, 2),
            (6, 2),
            (6, 4),
            (4, 4),
            (4, 6),
            (2, 6),
            (2, 4),
            (0, 4),
            (0, 2),
            (2, 2),
        ]
    )
    assert count_reflex_vertices(poly) == 4


def test_reflex_count_u_shape():
    # U: 4x4 outer minus 2x3 inner notch from top → 2 reflex
    poly = sg.Polygon(
        [
            (0, 0),
            (4, 0),
            (4, 4),
            (3, 4),
            (3, 1),
            (1, 1),
            (1, 4),
            (0, 4),
        ]
    )
    assert count_reflex_vertices(poly) == 2


def test_reflex_count_closing_duplicate_ignored():
    """A trailing duplicate of the first vertex shouldn't add a phantom reflex."""
    poly = sg.Polygon([(0, 0), (4, 0), (4, 2), (0, 2), (0, 0)])
    assert count_reflex_vertices(poly) == 0


def test_reflex_count_empty_polygon():
    assert count_reflex_vertices(sg.Polygon()) == 0


# ---------- _reflex_of_union ----------


def test_reflex_of_union_empty_ids_returns_invalid():
    assert _reflex_of_union((), {}, theta=0.0) == _REFLEX_INVALID


def test_reflex_of_union_rect_fast_path():
    regions = {
        1: _mk_region(1, ((0, 0), (2, 0), (2, 2), (0, 2))),
        2: _mk_region(2, ((2, 0), (4, 0), (4, 2), (2, 2))),
    }
    assert _reflex_of_union((1, 2), regions, theta=0.0) == 0


def test_reflex_of_union_l_shape():
    regions = {
        1: _mk_region(1, ((0, 0), (4, 0), (4, 2), (0, 2))),
        2: _mk_region(2, ((0, 2), (2, 2), (2, 4), (0, 4))),
    }
    assert _reflex_of_union((1, 2), regions, theta=0.0) == 1


def test_reflex_of_union_disconnected_returns_invalid():
    regions = {
        1: _mk_region(1, ((0, 0), (2, 0), (2, 2), (0, 2))),
        2: _mk_region(2, ((10, 10), (12, 10), (12, 12), (10, 12))),
    }
    assert _reflex_of_union((1, 2), regions, theta=0.0) == _REFLEX_INVALID
