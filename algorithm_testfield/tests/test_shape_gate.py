"""Tests for shape_gate.py (Phase 7 Round 4 W4)."""

from __future__ import annotations

import shapely.geometry as sg

from celllayout_tf.regionize import Region
from celllayout_tf.schema import ShapePart
from celllayout_tf.shape_gate import (
    count_reflex_vertices,
    make_shape_gate,
)
from celllayout_tf.territory import Territory


# ---------- helpers ----------


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


def _rect_part(part_id: int = 0, kind: str = "axis_aligned") -> Territory:
    """Minimal Territory stub — only ``part_id`` and ``kind`` are used by the gate."""
    return Territory(
        part_id=part_id,
        theta=0.0,
        kind=kind,
        pieces=(ShapePart(exterior=((0, 0), (1, 0), (1, 1), (0, 1))),),
    )


# ---------- count_reflex_vertices ----------


def test_reflex_count_axis_aligned_rect():
    poly = sg.Polygon([(0, 0), (4, 0), (4, 2), (0, 2)])
    assert count_reflex_vertices(poly) == 0


def test_reflex_count_l_shape():
    # L: 4x4 minus top-right 2x2 corner
    poly = sg.Polygon([(0, 0), (4, 0), (4, 2), (2, 2), (2, 4), (0, 4)])
    assert count_reflex_vertices(poly) == 1


def test_reflex_count_t_shape():
    # T: horizontal bar (0,0)-(6,2) + vertical stem (2,2)-(4,4)
    poly = sg.Polygon(
        [(0, 0), (6, 0), (6, 2), (4, 2), (4, 4), (2, 4), (2, 2), (0, 2)]
    )
    assert count_reflex_vertices(poly) == 2


def test_reflex_count_cross_shape():
    # +: 4 reflex corners (one at each inside corner)
    poly = sg.Polygon([
        (2, 0), (4, 0), (4, 2), (6, 2), (6, 4),
        (4, 4), (4, 6), (2, 6), (2, 4), (0, 4), (0, 2), (2, 2),
    ])
    assert count_reflex_vertices(poly) == 4


def test_reflex_count_u_shape():
    # U: 4x4 outer minus 2x3 inner from top
    poly = sg.Polygon([
        (0, 0), (4, 0), (4, 4), (3, 4), (3, 1), (1, 1), (1, 4), (0, 4),
    ])
    assert count_reflex_vertices(poly) == 2


def test_reflex_count_closing_duplicate_ignored():
    """A trailing duplicate of the first vertex shouldn't add a phantom reflex."""
    coords = [(0, 0), (4, 0), (4, 2), (0, 2), (0, 0)]
    poly = sg.Polygon(coords)
    assert count_reflex_vertices(poly) == 0


# ---------- make_shape_gate: Layer 1 (cross-theta) ----------


def test_gate_cross_theta_rejected():
    territories = (_rect_part(0), _rect_part(1))
    gate = make_shape_gate(territories, max_l_rooms=2)
    regions = {
        1: _mk_region(1, ((0, 0), (2, 0), (2, 2), (0, 2)), theta=0.0, part_id=0),
        2: _mk_region(2, ((2, 0), (4, 0), (4, 2), (2, 2)), theta=0.5, part_id=1),
    }
    assert gate(
        room_idx=0,
        room_region_ids_after=(1, 2),
        rooms_state_before={0: (1,)},
        regions_by_id=regions,
    ) is False


# ---------- make_shape_gate: Layer 2 (curved exemption) ----------


def test_gate_curved_exemption_returns_true():
    territories = (_rect_part(0, kind="curved"),)
    gate = make_shape_gate(territories, max_l_rooms=2)
    # Even a "T-shape" region union passes when curved territory is involved.
    regions = {
        1: _mk_region(1, ((0, 0), (6, 0), (6, 2), (0, 2)), part_id=0),
        2: _mk_region(2, ((2, 2), (4, 2), (4, 4), (2, 4)), part_id=0),
    }
    assert gate(
        room_idx=0,
        room_region_ids_after=(1, 2),
        rooms_state_before={0: (1,)},
        regions_by_id=regions,
    ) is True


# ---------- make_shape_gate: Layer 3 (reflex + budget) ----------


def test_gate_rect_always_passes():
    territories = (_rect_part(0),)
    gate = make_shape_gate(territories, max_l_rooms=0)  # zero budget
    regions = {
        1: _mk_region(1, ((0, 0), (2, 0), (2, 2), (0, 2))),
        2: _mk_region(2, ((2, 0), (4, 0), (4, 2), (2, 2))),
    }
    assert gate(
        room_idx=0,
        room_region_ids_after=(1, 2),
        rooms_state_before={0: (1,)},
        regions_by_id=regions,
    ) is True


def test_gate_t_shape_always_rejected_even_with_budget():
    territories = (_rect_part(0),)
    gate = make_shape_gate(territories, max_l_rooms=99)
    regions = {
        1: _mk_region(1, ((0, 0), (6, 0), (6, 2), (0, 2))),       # 6x2 bar
        2: _mk_region(2, ((2, 2), (4, 2), (4, 4), (2, 4))),       # stem on top
    }
    assert gate(
        room_idx=0,
        room_region_ids_after=(1, 2),
        rooms_state_before={0: (1,)},
        regions_by_id=regions,
    ) is False  # would form T (reflex=2)


def test_gate_l_passes_when_budget_available():
    territories = (_rect_part(0),)
    gate = make_shape_gate(territories, max_l_rooms=2)
    regions = {
        1: _mk_region(1, ((0, 0), (4, 0), (4, 2), (0, 2))),       # 4x2 base
        2: _mk_region(2, ((0, 2), (2, 2), (2, 4), (0, 4))),       # L stem above-left
    }
    assert gate(
        room_idx=0,
        room_region_ids_after=(1, 2),
        rooms_state_before={0: (1,)},
        regions_by_id=regions,
    ) is True


def test_gate_l_rejected_when_budget_zero():
    territories = (_rect_part(0),)
    gate = make_shape_gate(territories, max_l_rooms=0)
    regions = {
        1: _mk_region(1, ((0, 0), (4, 0), (4, 2), (0, 2))),
        2: _mk_region(2, ((0, 2), (2, 2), (2, 4), (0, 4))),
    }
    assert gate(
        room_idx=0,
        room_region_ids_after=(1, 2),
        rooms_state_before={0: (1,)},
        regions_by_id=regions,
    ) is False


def test_gate_l_rejected_when_other_rooms_used_all_slots():
    """With max_l_rooms=1 and another room already L, this room can't go L."""
    territories = (_rect_part(0),)
    gate = make_shape_gate(territories, max_l_rooms=1)
    regions = {
        # Other room (idx=1) holds an L using its two regions.
        10: _mk_region(10, ((10, 0), (14, 0), (14, 2), (10, 2))),
        11: _mk_region(11, ((10, 2), (12, 2), (12, 4), (10, 4))),
        # Our room (idx=0) trying to go L.
        1: _mk_region(1, ((0, 0), (4, 0), (4, 2), (0, 2))),
        2: _mk_region(2, ((0, 2), (2, 2), (2, 4), (0, 4))),
    }
    rooms_before = {0: (1,), 1: (10, 11)}
    assert gate(
        room_idx=0,
        room_region_ids_after=(1, 2),
        rooms_state_before=rooms_before,
        regions_by_id=regions,
    ) is False


def test_gate_already_l_room_can_deepen_without_consuming_extra_slot():
    """A room already L can keep absorbing while reflex stays at 1."""
    territories = (_rect_part(0),)
    gate = make_shape_gate(territories, max_l_rooms=1)
    regions = {
        # Room idx=0 currently L: a 4x2 bar + 2x2 stem on the left → L (reflex=1)
        1: _mk_region(1, ((0, 0), (4, 0), (4, 2), (0, 2))),
        2: _mk_region(2, ((0, 2), (2, 2), (2, 4), (0, 4))),
        # Candidate: extend the stem further up → still L (reflex=1)
        3: _mk_region(3, ((0, 4), (2, 4), (2, 6), (0, 6))),
        # Another room (idx=1) is also L, using the only other L slot.
        10: _mk_region(10, ((10, 0), (14, 0), (14, 2), (10, 2))),
        11: _mk_region(11, ((10, 2), (12, 2), (12, 4), (10, 4))),
    }
    rooms_before = {0: (1, 2), 1: (10, 11)}
    # Even though max_l_rooms=1 and the other room holds it, our room is
    # already counted (already L) — extending stays L, OK.
    assert gate(
        room_idx=0,
        room_region_ids_after=(1, 2, 3),
        rooms_state_before=rooms_before,
        regions_by_id=regions,
    ) is True


def test_gate_l_room_filling_corner_back_to_rect_passes():
    """L → rect (corner filled in) frees the slot and passes regardless of budget."""
    territories = (_rect_part(0),)
    gate = make_shape_gate(territories, max_l_rooms=0)
    regions = {
        # Room idx=0 currently L
        1: _mk_region(1, ((0, 0), (4, 0), (4, 2), (0, 2))),
        2: _mk_region(2, ((0, 2), (2, 2), (2, 4), (0, 4))),
        # Candidate fills missing top-right corner → 4x4 rect
        3: _mk_region(3, ((2, 2), (4, 2), (4, 4), (2, 4))),
    }
    rooms_before = {0: (1, 2)}
    assert gate(
        room_idx=0,
        room_region_ids_after=(1, 2, 3),
        rooms_state_before=rooms_before,
        regions_by_id=regions,
    ) is True


def test_gate_disconnected_union_rejected():
    """Disconnected union (MultiPolygon) sentinel reflex → always reject."""
    territories = (_rect_part(0),)
    gate = make_shape_gate(territories, max_l_rooms=99)
    regions = {
        1: _mk_region(1, ((0, 0), (2, 0), (2, 2), (0, 2))),
        2: _mk_region(2, ((10, 10), (12, 10), (12, 12), (10, 12))),
    }
    # Sentinel _REFLEX_INVALID = 99 → reflex >= 2 path → False
    assert gate(
        room_idx=0,
        room_region_ids_after=(1, 2),
        rooms_state_before={0: (1,)},
        regions_by_id=regions,
    ) is False
