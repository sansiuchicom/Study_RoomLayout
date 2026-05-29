"""Tests for stages/growth_absorb.py 3-stage leftover absorption (Step 04 §4.10).

Unit tests for the aspect helpers + an integration smoke for _absorb_remaining
(full behavior is pinned by the 4.11 growth goldens, end-to-end on 33 cases).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from room_layout.schema import ShapeInput, ShapePart, from_dict
from room_layout.stages._helpers import to_shapely
from room_layout.stages.atomize import atomize
from room_layout.stages.growth_absorb import (
    _absorb_remaining,
    _aspect_ok_for_max,
    _local_bbox_aspect,
)
from room_layout.stages.region_graph import build_region_graph
from room_layout.stages.regionize import Region, regionize
from room_layout.stages.territory import resolve_territories

GOLDEN = Path(__file__).parent / "golden"
_CASE = "case_06_square_10x10"


def _region(rid: int, exterior: tuple[tuple[float, float], ...]) -> Region:
    return Region(
        region_id=rid,
        shape=ShapePart(exterior=exterior),
        atom_ids=(),
        part_id=0,
        piece_id=0,
        theta=0.0,
        cut_history=(),
    )


# ---------- _local_bbox_aspect ----------


def test_local_bbox_aspect_two_squares_is_two():
    # unit square + adjacent unit square → 2x1 union → aspect 2.0
    regions = {
        1: _region(1, ((0, 0), (1, 0), (1, 1), (0, 1))),
        2: _region(2, ((1, 0), (2, 0), (2, 1), (1, 1))),
    }
    assert _local_bbox_aspect((1, 2), regions, 0.0) == 2.0


def test_local_bbox_aspect_single_square_is_one():
    regions = {1: _region(1, ((0, 0), (2, 0), (2, 2), (0, 2)))}
    assert _local_bbox_aspect((1,), regions, 0.0) == 1.0


def test_local_bbox_aspect_empty_is_none():
    # empty union → degenerate → None
    assert _local_bbox_aspect((), {}, 0.0) is None


# ---------- _aspect_ok_for_max ----------


def test_aspect_ok_within_max():
    regions = {
        1: _region(1, ((0, 0), (1, 0), (1, 1), (0, 1))),
        2: _region(2, ((1, 0), (2, 0), (2, 1), (1, 1))),
    }
    assert _aspect_ok_for_max((1, 2), regions, 0.0, 4.0) is True  # aspect 2 ≤ 4


def test_aspect_exceeds_max():
    regions = {
        1: _region(1, ((0, 0), (1, 0), (1, 1), (0, 1))),
        2: _region(2, ((1, 0), (2, 0), (2, 1), (1, 1))),
    }
    assert _aspect_ok_for_max((1, 2), regions, 0.0, 1.5) is False  # aspect 2 > 1.5


def test_aspect_degenerate_is_ok():
    assert _aspect_ok_for_max((), {}, 0.0, 1.0) is True


# ---------- _absorb_remaining (integration smoke) ----------


def _build():
    with (GOLDEN / _CASE / "input.json").open(encoding="utf-8") as f:
        floor = from_dict(ShapeInput, json.load(f)["shape"]).floors[0]
    atoms = atomize(floor)
    regions = regionize(floor, atoms=atoms)
    rg = build_region_graph(floor, atoms=atoms, regions=regions)
    terrs = resolve_territories(floor)
    regions_by_id = {r.region_id: r for r in regions}
    region_poly_by_id = {r.region_id: to_shapely(r.shape) for r in regions}
    neighbors_map: dict[int, set[int]] = defaultdict(set)
    for e in rg.edges:
        neighbors_map[e.region_a].add(e.region_b)
        neighbors_map[e.region_b].add(e.region_a)
    return floor, rg, terrs, regions, regions_by_id, region_poly_by_id, neighbors_map


def _seeded_state(regions):
    """One room seeded with the lowest-id region; everything else unassigned."""
    seed_id = min(r.region_id for r in regions)
    return {0: [seed_id]}, {seed_id: 0}


def test_absorb_single_seed_unlimited_aspect_absorbs_all():
    floor, rg, terrs, regions, regions_by_id, region_poly_by_id, neighbors_map = _build()
    room_regions, region_to_room = _seeded_state(regions)
    _absorb_remaining(
        floor=floor,
        rg=rg,
        territories=terrs,
        room_regions=room_regions,
        region_to_room=region_to_room,
        regions_by_id=regions_by_id,
        region_poly_by_id=region_poly_by_id,
        neighbors_map=neighbors_map,
        hub_room_idx=0,
        room_max_aspect={0: float("inf")},
    )
    # case_06 is one territory/piece with a single seeded room → Stage 1 bulk
    # absorb takes every region into room 0.
    assert len(region_to_room) == len(regions)
    assert set(room_regions[0]) == {r.region_id for r in regions}


def test_absorb_tight_aspect_gate_restricts():
    floor, rg, terrs, regions, regions_by_id, region_poly_by_id, neighbors_map = _build()
    room_regions, region_to_room = _seeded_state(regions)
    _absorb_remaining(
        floor=floor,
        rg=rg,
        territories=terrs,
        room_regions=room_regions,
        region_to_room=region_to_room,
        regions_by_id=regions_by_id,
        region_poly_by_id=region_poly_by_id,
        neighbors_map=neighbors_map,
        hub_room_idx=0,
        room_max_aspect={0: 1.0},  # only a perfect square may grow
    )
    # tight gate blocks most absorption → not everything assigned
    assert len(region_to_room) < len(regions)
