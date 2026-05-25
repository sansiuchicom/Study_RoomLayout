"""Tests for `room_layout.schema.output` — work item 4.8 / Plan §4.8.

Covers: `Door` / `LabeledRoom` / `LabeledFloorLayout` / `LabeledRoomLayout`
defaults + mutability (S02-D3) and the `proto3:D018` convention that
`valid=False` carries non-empty `failure_records`.
"""

from shapely.geometry import Polygon

from room_layout.schema.failure import FailureRecord
from room_layout.schema.output import (
    Door,
    LabeledFloorLayout,
    LabeledRoom,
    LabeledRoomLayout,
)


def _poly() -> Polygon:
    return Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])


# --- Door ---


def test_door_default_position_is_none():
    """v1 placeholder per S01-Q2 — `position` defaults to None."""
    d = Door(kind="interior")
    assert d.position is None
    assert d.kind == "interior"


def test_door_with_position():
    d = Door(kind="exterior", position=(1.0, 2.0))
    assert d.position == (1.0, 2.0)


# --- LabeledRoom ---


def test_labeled_room_default_optional_fields():
    r = LabeledRoom(id="r1", polygon=_poly(), role="public", usage=None, area_m2=25.0)
    assert r.doors is None
    assert r.anchor_id is None


def test_labeled_room_is_mutable():
    r = LabeledRoom(id="r1", polygon=_poly(), role="public", usage=None, area_m2=25.0)
    r.doors = [Door(kind="interior")]
    r.area_m2 = 30.0
    assert len(r.doors) == 1
    assert r.area_m2 == 30.0


# --- LabeledFloorLayout ---


def test_labeled_floor_layout_defaults():
    fl = LabeledFloorLayout(level=1)
    assert fl.rooms == []
    assert fl.corridor_polygons == []


def test_labeled_floor_layout_accumulates_rooms():
    fl = LabeledFloorLayout(level=1)
    fl.rooms.append(LabeledRoom(id="r1", polygon=_poly(), role="public", usage=None, area_m2=25.0))
    assert len(fl.rooms) == 1


# --- LabeledRoomLayout ---


def test_labeled_room_layout_valid_true_default_empty():
    lrl = LabeledRoomLayout(valid=True)
    assert lrl.floors == []
    assert lrl.failure_records == []
    assert lrl.provenance == {}


def test_labeled_room_layout_valid_false_carries_failures():
    """proto3:D018 convention test: `valid=False` ⇒ non-empty
    `failure_records`. NOT enforced in `__post_init__` (mutable type;
    the algorithm flips `valid` after accumulation) — pinned here.
    """
    fr = FailureRecord(code="X", stage="s", message="m")
    lrl = LabeledRoomLayout(valid=False, failure_records=[fr])
    assert lrl.valid is False
    assert len(lrl.failure_records) == 1


def test_labeled_room_layout_is_mutable():
    lrl = LabeledRoomLayout(valid=True)
    lrl.valid = False
    lrl.failure_records.append(FailureRecord(code="X", stage="s", message="m"))
    lrl.provenance["seed"] = 42
    assert lrl.valid is False
    assert len(lrl.failure_records) == 1
    assert lrl.provenance["seed"] == 42
