"""Tests for stages/anchors.py donut-hole preprocessing (Step 04 §4.4).

Geometry-level validation only: the hole is excluded and the holed floor
atomizes cleanly. Room-realism (wrap-around / isolation) cannot be observed
until growth lands (4.11) — see S04-D4.
"""

from __future__ import annotations

import shapely.geometry as sg

from room_layout.schema import FloorShape, ShapePart, VerticalAnchor
from room_layout.stages._helpers import to_shapely
from room_layout.stages.anchors import anchors_on_floor, subtract_anchors
from room_layout.stages.atomize import atomize

_SQUARE10 = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))


def _floor(level: int = 0) -> FloorShape:
    return FloorShape(
        level=level,
        parts=[ShapePart(exterior=_SQUARE10)],
        floor_to_floor_height=None,
    )


def _stair(id_: str, box: sg.Polygon, floor_range: tuple[int, int] = (0, 0)) -> VerticalAnchor:
    return VerticalAnchor(
        id=id_,
        kind="stair_core",
        footprint_polygon=box,
        floor_range=floor_range,
        host_role="vertical_circulation",
    )


def test_anchors_on_floor_filters_by_range():
    a0 = _stair("a0", sg.box(4, 4, 6, 6), floor_range=(0, 2))
    a3 = _stair("a3", sg.box(1, 1, 2, 2), floor_range=(3, 5))
    assert anchors_on_floor([a0, a3], 0) == [a0]
    assert anchors_on_floor([a0, a3], 4) == [a3]
    assert anchors_on_floor([a0, a3], 6) == []


def test_no_applicable_anchors_returns_same_floor():
    floor = _floor(level=0)
    a3 = _stair("a3", sg.box(4, 4, 6, 6), floor_range=(3, 5))
    assert subtract_anchors(floor, [a3]) is floor
    assert subtract_anchors(floor, []) is floor


def test_interior_anchor_becomes_hole():
    floor = _floor()
    holed = subtract_anchors(floor, [_stair("st", sg.box(4, 4, 6, 6))])
    assert len(holed.parts) == 1
    part = holed.parts[0]
    assert len(part.holes) == 1
    # area conserved: 100 - (2*2) = 96
    assert abs(to_shapely(part).area - 96.0) < 1e-6


def test_holed_floor_atomizes_without_filling_hole():
    floor = _floor()
    holed = subtract_anchors(floor, [_stair("st", sg.box(4, 4, 6, 6))])
    atoms = atomize(holed)
    total = sum(to_shapely(a.shape).area for a in atoms)
    assert abs(total - 96.0) < 1e-3
    hole = sg.box(4, 4, 6, 6)
    assert all(not hole.contains(sg.Point(*a.centroid)) for a in atoms)


def test_spanning_anchor_splits_part():
    # anchor spans full height through the middle → 10x10 splits into two 4x10
    floor = _floor()
    holed = subtract_anchors(floor, [_stair("bar", sg.box(4, 0, 6, 10))])
    assert len(holed.parts) == 2
    areas = sorted(round(to_shapely(p).area, 6) for p in holed.parts)
    assert areas == [40.0, 40.0]
