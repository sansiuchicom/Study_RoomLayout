"""run() robustness — the public contract never raises out (③ / S07 review).

Each test feeds an input that previously crashed run() with an uncaught
exception, and asserts a graceful valid=False + the right FailureRecord code.
"""

from __future__ import annotations

from shapely.geometry import Polygon

from room_layout import run
from room_layout.schema import (
    FloorShape,
    ProgramRequest,
    ShapeInput,
    ShapePart,
    SpaceUnitSpec,
    VerticalAnchor,
)


def _rect_floor(w: float, h: float, level: int = 0) -> FloorShape:
    return FloorShape(
        level=level,
        parts=[ShapePart(exterior=((0, 0), (w, 0), (w, h), (0, h)))],
        floor_to_floor_height=None,
    )


def _spec(id_: str, role: str, anchor_id: str | None = None) -> SpaceUnitSpec:
    return SpaceUnitSpec(
        id=id_, role=role, usage=None, area_min_m2=0.5, required=True, anchor_id=anchor_id
    )


def _program(specs: list[SpaceUnitSpec], level: int = 0) -> ProgramRequest:
    return ProgramRequest(target_type="apartment", floor_programs={level: specs})


_BASE = [_spec("liv", "public"), _spec("bed", "private"), _spec("bath", "wet")]


def test_oversubscribed_program_does_not_crash():
    # 3 rooms but a 3x2 floor seeds < 3 regions → was an uncaught DomainGateFailure
    shape = ShapeInput(name="tiny", floors=[_rect_floor(3, 2)], vertical_anchors=[])
    result = run(shape, _program(_BASE), seed=0)
    assert result.valid is False
    assert any(f.code == "GROWTH_OVERSUBSCRIBED" for f in result.failure_records)


def test_anchor_consuming_whole_floor_does_not_crash():
    shape = ShapeInput(
        name="eaten",
        floors=[_rect_floor(4, 4)],
        vertical_anchors=[
            VerticalAnchor(
                id="c",
                kind="stair_core",
                footprint_polygon=Polygon([(0, 0), (4, 0), (4, 4), (0, 4)]),
                floor_range=(0, 0),
                host_role="vertical_circulation",
            )
        ],
    )
    result = run(
        shape, _program([*_BASE, _spec("vc", "vertical_circulation", anchor_id="c")]), seed=0
    )
    assert result.valid is False
    assert any(f.code == "FLOOR_CONSUMED_BY_ANCHORS" for f in result.failure_records)


def test_anchor_outside_floor_does_not_emit_out_of_building_room():
    shape = ShapeInput(
        name="out",
        floors=[_rect_floor(4, 4)],
        vertical_anchors=[
            VerticalAnchor(
                id="c",
                kind="stair_core",
                footprint_polygon=Polygon([(6, 6), (8, 6), (8, 8), (6, 8)]),  # outside the floor
                floor_range=(0, 0),
                host_role="vertical_circulation",
            )
        ],
    )
    result = run(
        shape, _program([*_BASE, _spec("vc", "vertical_circulation", anchor_id="c")]), seed=0
    )
    assert result.valid is False
    assert any(f.code == "ANCHOR_OUTSIDE_FOOTPRINT" for f in result.failure_records)
    # short-circuited at validate_input → no out-of-building room ever emitted
    assert result.floors == []
