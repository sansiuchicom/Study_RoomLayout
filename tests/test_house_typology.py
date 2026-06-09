"""house typology smoke (Step 10 §4.2 / S10-D3 / S10-D13).

The first multi-floor typology: `house.json` loads, registers, and lets a
multi-floor run past `check_multi_floor_feasibility` (apartment forbids it).
Building-level cardinality logic itself is 10.3 — here both floors carry a full
program so per-floor admission (still active) passes; this proves the typology
+ the gate, not the building-cardinality split.
"""

from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from room_layout import run
from room_layout.schema import ProgramRequest, ShapeInput
from room_layout.schema.geometry import FloorShape, ShapePart, VerticalAnchor
from room_layout.schema.program import SpaceUnitSpec
from room_layout.schema.target import TargetRules
from room_layout.target.adapter import DEFAULT_HOUSE_RULES_PATH
from room_layout.target.rules_loader import load_target_rules


def _floor(level: int) -> FloorShape:
    return FloorShape(
        level=level,
        parts=[ShapePart(exterior=((0, 0), (12, 0), (12, 10), (0, 10)))],
        floor_to_floor_height=3.0,
    )


def _spec(sid: str, role: str, **kw) -> SpaceUnitSpec:
    return SpaceUnitSpec(id=sid, role=role, usage=None, area_min_m2=0.5, required=True, **kw)


def _stair(levels: tuple[int, int]) -> VerticalAnchor:
    return VerticalAnchor(
        id="stair",
        kind="stair_core",
        footprint_polygon=Polygon([(0, 0), (2, 0), (2, 3), (0, 3)]),
        floor_range=levels,
        host_role="vertical_circulation",
    )


def _house_floor_program(suffix: str) -> list[SpaceUnitSpec]:
    return [
        _spec(f"living{suffix}", "public"),
        _spec(f"bed{suffix}", "private"),
        _spec(f"kitchen{suffix}", "wet"),
        _spec(f"stair{suffix}", "vertical_circulation", anchor_id="stair"),
    ]


# --- house.json + cardinality_scope field ----------------------------------


def test_house_rules_load_with_building_scope():
    rules = load_target_rules(DEFAULT_HOUSE_RULES_PATH)
    assert rules.requires_single_floor is False
    assert rules.cardinality_scope == "building"
    assert rules.min_cardinality == {"public": 1, "private": 1, "wet": 1}


def test_apartment_rules_default_to_per_floor_scope():
    # apartment.json has no cardinality_scope key → field default (byte-identical)
    from room_layout.target.adapter import DEFAULT_APARTMENT_RULES_PATH

    assert load_target_rules(DEFAULT_APARTMENT_RULES_PATH).cardinality_scope == "per_floor"


def test_cardinality_scope_validated():
    with pytest.raises(ValueError, match="cardinality_scope"):
        TargetRules(
            density_factor=0.85,
            requires_single_floor=False,
            default_min_area_m2={
                r: 1.0
                for r in (
                    "public",
                    "private",
                    "service",
                    "wet",
                    "hub",
                    "corridor",
                    "vertical_circulation",
                )
            },
            cardinality_scope="whole_site",
        )


# --- house through run() ---------------------------------------------------


def test_single_floor_house_is_valid():
    shape = ShapeInput(name="house1", floors=[_floor(1)], vertical_anchors=[_stair((1, 1))])
    prog = ProgramRequest(target_type="house", floor_programs={1: _house_floor_program("_1")})
    result = run(shape, prog, seed=42)
    assert result.valid is True
    assert len(result.floors) == 1


def test_multi_floor_house_passes_the_multi_floor_gate():
    # apartment would fail here with DOMAIN_MULTI_FLOOR_NOT_SUPPORTED; house must
    # not. Both floors carry a full program so per-floor admission (still active
    # until 10.3) passes — proving the typology + the gate end-to-end.
    shape = ShapeInput(
        name="house2", floors=[_floor(1), _floor(2)], vertical_anchors=[_stair((1, 2))]
    )
    prog = ProgramRequest(
        target_type="house",
        floor_programs={1: _house_floor_program("_1"), 2: _house_floor_program("_2")},
    )
    result = run(shape, prog, seed=42)
    codes = {fr.code for fr in result.failure_records}
    assert "DOMAIN_MULTI_FLOOR_NOT_SUPPORTED" not in codes
    assert "NO_TARGET_RULES" not in codes
    assert result.valid is True, codes
    assert len(result.floors) == 2
