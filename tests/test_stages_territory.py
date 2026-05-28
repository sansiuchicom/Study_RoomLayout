"""Tests for ``room_layout.stages.territory`` — work item 4.7 / Plan §4.7.

Covers part_kind classification, resolve_territories overlap resolution
(host/loser by intruding-vertex count + tiebreakers), full-consumption
→ empty territory, and collect_cross_theta_contact_coords on a shared
edge. Stage takes a FloorShape (S03-D13).
"""

import pytest
import shapely.geometry as sg
from shapely.ops import unary_union

from room_layout.schema import FloorShape, ShapePart
from room_layout.stages._helpers import from_shapely, to_shapely
from room_layout.stages.territory import (
    KIND_AXIS_ALIGNED,
    KIND_CURVED,
    KIND_ROTATED,
    Territory,
    collect_cross_theta_contact_coords,
    part_kind,
    resolve_territories,
)


def _rect(x0, y0, x1, y1) -> ShapePart:
    return ShapePart(exterior=((x0, y0), (x1, y0), (x1, y1), (x0, y1)))


def _floor(*parts) -> FloorShape:
    return FloorShape(level=1, parts=list(parts), floor_to_floor_height=3.0)


def _area(territory: Territory) -> float:
    return sum(to_shapely(p).area for p in territory.pieces)


# --- part_kind ---


def test_part_kind_axis_aligned():
    assert part_kind(_rect(0, 0, 10, 10)) == KIND_AXIS_ALIGNED


def test_part_kind_rotated():
    # a square rotated 45°: every edge at 45°, theta = pi/4 (not axis-aligned)
    diamond = ShapePart(exterior=((0.0, 0.0), (1.0, 1.0), (0.0, 2.0), (-1.0, 1.0)))
    assert part_kind(diamond) == KIND_ROTATED


def test_part_kind_curved():
    disk = from_shapely(sg.Point(0, 0).buffer(5, quad_segs=16))
    assert part_kind(disk) == KIND_CURVED


# --- resolve_territories ---


def test_resolve_single_part_full():
    terrs = resolve_territories(_floor(_rect(0, 0, 10, 10)))
    assert len(terrs) == 1
    assert terrs[0].part_id == 0
    assert _area(terrs[0]) == 100.0


def test_resolve_non_overlapping_both_full():
    terrs = resolve_territories(_floor(_rect(0, 0, 5, 5), _rect(10, 10, 15, 15)))
    assert len(terrs) == 2
    assert _area(terrs[0]) == 25.0
    assert _area(terrs[1]) == 25.0
    assert all(not t.is_empty for t in terrs)


def test_resolve_overlap_loser_loses_zone():
    # A=(0,0,10,10), B=(5,5,15,15) overlap in (5,5,10,10)=25. Tie on intruding
    # vertices (1 each) + kind + area → earlier index (A) wins; B loses 25.
    terrs = resolve_territories(_floor(_rect(0, 0, 10, 10), _rect(5, 5, 15, 15)))
    assert _area(terrs[0]) == 100.0  # winner keeps full
    assert _area(terrs[1]) == 75.0  # loser: 100 - 25 overlap


def test_resolve_fully_contained_loser_becomes_empty():
    # small fully inside big: all 4 small vertices intrude, 0 big vertices
    # intrude → big wins, small.difference(big) is empty.
    terrs = resolve_territories(_floor(_rect(0, 0, 20, 20), _rect(5, 5, 10, 10)))
    assert _area(terrs[0]) == 400.0
    assert terrs[1].is_empty
    assert _area(terrs[1]) == 0.0


def test_resolve_preserves_theta_and_kind():
    terrs = resolve_territories(_floor(_rect(0, 0, 10, 10)))
    assert terrs[0].kind == KIND_AXIS_ALIGNED
    assert terrs[0].theta == 0.0


# --- collect_cross_theta_contact_coords ---


def test_contact_coords_shared_edge():
    # two axis-aligned rects sharing the edge x=10 (y in [0,10])
    floor = _floor(_rect(0, 0, 10, 10), _rect(10, 0, 20, 10))
    terrs = resolve_territories(floor)
    xs, ys = collect_cross_theta_contact_coords(floor, terrs)
    # both axis-aligned → theta group key 0.0; local frame == global
    assert 0.0 in xs
    assert 10.0 in xs[0.0]
    assert 0.0 in ys[0.0]
    assert 10.0 in ys[0.0]


def test_contact_coords_no_contact_when_disjoint():
    floor = _floor(_rect(0, 0, 5, 5), _rect(10, 10, 15, 15))
    terrs = resolve_territories(floor)
    xs, ys = collect_cross_theta_contact_coords(floor, terrs)
    # disjoint parts share no boundary → no contact coords
    assert all(len(v) == 0 for v in xs.values())
    assert all(len(v) == 0 for v in ys.values())


# --- Territory dataclass ---


def test_territory_is_empty_property():
    assert Territory(part_id=0, theta=0.0, kind=KIND_AXIS_ALIGNED, pieces=()).is_empty
    sp = _rect(0, 0, 1, 1)
    assert not Territory(part_id=0, theta=0.0, kind=KIND_AXIS_ALIGNED, pieces=(sp,)).is_empty


# --- latent-bug PoC (review C10) ---


@pytest.mark.xfail(
    reason="C10 latent: _pair_winner's 'fewer intruding vertices' rule is not a total "
    "order. For 3 mutually-overlapping parts whose pairwise winners form a cycle, the "
    "triple-overlap region is subtracted (against the original winner polygon) from all "
    "three territories, leaving a hole in the footprint coverage. Not triggered by the "
    "33 fixtures (no 3-way overlap); this is a minimal direct trigger.",
    strict=True,
)
def test_resolve_territories_conserves_coverage_under_cyclic_3way_overlap():
    # Pairwise winners cycle: (0,1)->1, (1,2)->2, (0,2)->0. The triple overlap
    # [3,4]x[4,5] (area 1) ends up removed from every territory.
    parts = (_rect(3, 1, 7, 5), _rect(2, 4, 8, 7), _rect(1, 4, 4, 8))
    terr = resolve_territories(_floor(*parts))
    covered = unary_union([to_shapely(pc) for t in terr for pc in t.pieces])
    original = unary_union([to_shapely(p) for p in parts])
    assert covered.area == pytest.approx(original.area, abs=1e-9)
