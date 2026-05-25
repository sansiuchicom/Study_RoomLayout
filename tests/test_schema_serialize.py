"""Tests for `room_layout.schema.serialize` — work item 4.8 / Plan §4.8.

Covers: Polygon coord helpers, `to_dict` / `from_dict` round-trip for
every input + output dataclass, JSON wrappers, strict-by-default
rejection paths (extra keys / missing required / out-of-range Literal /
bool-as-numeric), and Union/None handling.
"""

import pytest
from shapely.geometry import Polygon

from room_layout.schema import (
    Door,
    FailureRecord,
    FloorShape,
    LabeledFloorLayout,
    LabeledRoom,
    LabeledRoomLayout,
    ProgramRequest,
    ShapeInput,
    ShapePart,
    SpaceUnitSpec,
    VerticalAnchor,
    coords_to_polygon,
    from_dict,
    from_json,
    polygon_to_coords,
    to_dict,
    to_json,
)

_SQ = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))


# --- Polygon helpers ---


def test_polygon_to_coords_simple():
    p = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    d = polygon_to_coords(p)
    assert d == {"exterior": [[0, 0], [10, 0], [10, 10], [0, 10]], "holes": []}


def test_polygon_to_coords_with_hole():
    p = Polygon(
        [(0, 0), (10, 0), (10, 10), (0, 10)],
        [[(2, 2), (2, 5), (5, 5), (5, 2)]],
    )
    d = polygon_to_coords(p)
    assert d["holes"] == [[[2, 2], [2, 5], [5, 5], [5, 2]]]


def test_polygon_round_trip():
    p = Polygon(
        [(0, 0), (10, 0), (10, 10), (0, 10)],
        [[(2, 2), (2, 5), (5, 5), (5, 2)]],
    )
    p2 = coords_to_polygon(polygon_to_coords(p))
    assert p.equals_exact(p2, 0)


def test_coords_to_polygon_missing_exterior():
    with pytest.raises(ValueError, match="exterior"):
        coords_to_polygon({"holes": []})


# --- Fixture builders ---


def _shape_part() -> ShapePart:
    return ShapePart(
        exterior=_SQ,
        holes=(((2.0, 2.0), (2.0, 5.0), (5.0, 5.0), (5.0, 2.0)),),
    )


def _vertical_anchor() -> VerticalAnchor:
    return VerticalAnchor(
        id="s1",
        kind="stair_core",
        footprint_polygon=Polygon([(0, 0), (3, 0), (3, 3), (0, 3)]),
        floor_range=(1, 3),
        host_role="vertical_circulation",
    )


def _shape_input() -> ShapeInput:
    return ShapeInput(
        name="demo",
        floors=[FloorShape(level=1, parts=[_shape_part()], floor_to_floor_height=3.0)],
        vertical_anchors=[_vertical_anchor()],
    )


def _space_unit_spec() -> SpaceUnitSpec:
    return SpaceUnitSpec(
        id="living",
        role="public",
        usage="LR",
        area_target_m2=20.0,
        area_min_m2=15.0,
        min_dimension_m=2.4,
        required=True,
    )


def _program_request() -> ProgramRequest:
    return ProgramRequest(
        target_type="apartment",
        floor_programs={1: [_space_unit_spec()]},
    )


def _labeled_room() -> LabeledRoom:
    return LabeledRoom(
        id="r1",
        polygon=Polygon([(0, 0), (5, 0), (5, 5), (0, 5)]),
        role="public",
        usage="LR",
        area_m2=25.0,
    )


def _labeled_room_layout() -> LabeledRoomLayout:
    return LabeledRoomLayout(
        valid=False,
        floors=[LabeledFloorLayout(level=1, rooms=[_labeled_room()])],
        failure_records=[FailureRecord(code="X", stage="s", message="m")],
        provenance={"seed": 42, "version": "0.1"},
    )


# --- Round-trip (dataclasses) ---


def test_shape_part_round_trip():
    sp = _shape_part()
    assert from_dict(ShapePart, to_dict(sp)) == sp


def test_vertical_anchor_round_trip():
    va = _vertical_anchor()
    va2 = from_dict(VerticalAnchor, to_dict(va))
    assert va2.id == va.id
    assert va2.kind == va.kind
    assert va2.host_role == va.host_role
    assert va2.floor_range == va.floor_range
    assert va2.footprint_polygon.equals_exact(va.footprint_polygon, 0)


def test_shape_input_json_round_trip():
    si = _shape_input()
    si2 = from_json(ShapeInput, to_json(si))
    assert si2.name == si.name
    assert len(si2.floors) == len(si.floors)
    assert si2.floors[0].parts[0] == si.floors[0].parts[0]


def test_program_request_json_round_trip_dict_int_keys():
    """Exercises `dict[int, list[SpaceUnitSpec]]` — JSON keys become str
    on dump and are coerced back to int on load."""
    pr = _program_request()
    pr2 = from_json(ProgramRequest, to_json(pr))
    assert pr2 == pr


def test_labeled_room_layout_json_round_trip():
    lrl = _labeled_room_layout()
    lrl2 = from_json(LabeledRoomLayout, to_json(lrl))
    assert lrl2.valid == lrl.valid
    assert lrl2.provenance == lrl.provenance
    assert lrl2.failure_records[0].code == lrl.failure_records[0].code
    assert lrl2.floors[0].rooms[0].polygon.equals_exact(lrl.floors[0].rooms[0].polygon, 0)


def test_failure_record_round_trip_with_data():
    fr = FailureRecord(code="X", stage="s", message="m", data={"a": 1, "b": "two"})
    assert from_dict(FailureRecord, to_dict(fr)) == fr


@pytest.mark.parametrize(
    "d",
    [
        Door(kind="interior"),
        Door(kind="exterior", position=(1.0, 2.0)),
    ],
)
def test_door_round_trip(d):
    assert from_dict(Door, to_dict(d)) == d


# --- Strict-by-default rejection paths ---


def test_from_dict_rejects_extra_key():
    bad = {**to_dict(_space_unit_spec()), "extra": 1}
    with pytest.raises(ValueError, match="extra keys"):
        from_dict(SpaceUnitSpec, bad)


def test_from_dict_rejects_missing_required():
    src = to_dict(_space_unit_spec())
    bad = {k: v for k, v in src.items() if k != "area_target_m2"}
    with pytest.raises(ValueError, match="missing required"):
        from_dict(SpaceUnitSpec, bad)


def test_from_dict_rejects_out_of_range_literal():
    """proto3:D017 — strict Literal validation at deserialization."""
    bad = {**to_dict(_space_unit_spec()), "role": "bedroom"}
    with pytest.raises(ValueError, match="Literal"):
        from_dict(SpaceUnitSpec, bad)


def test_from_dict_default_field_can_be_elided():
    sp = from_dict(ShapePart, {"exterior": [list(p) for p in _SQ]})
    assert sp.holes == ()


def test_from_dict_union_with_none():
    """LabeledRoom.usage / .doors / .anchor_id are all `X | None`."""
    d = to_dict(_labeled_room())
    d["usage"] = None
    d["doors"] = None
    d["anchor_id"] = None
    r = from_dict(LabeledRoom, d)
    assert r.usage is None
    assert r.doors is None
    assert r.anchor_id is None


def test_from_dict_rejects_bool_as_int():
    with pytest.raises(ValueError, match="int"):
        from_dict(int, True)


def test_from_dict_rejects_bool_as_float():
    with pytest.raises(ValueError, match="float"):
        from_dict(float, False)


def test_from_dict_accepts_int_as_float():
    """JSON has no 0 vs 0.0 distinction."""
    assert from_dict(float, 5) == 5.0
