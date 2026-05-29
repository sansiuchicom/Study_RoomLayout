"""Tests for stages/program_adapter.py (Step 04 §4.14, S04-D3).

Unit tests for the 7→4 role collapse + hub-first ordering + exclusions, plus an
integration check that driving case_01 through the adapter (new-schema
ProgramRequest, auto) reproduces the to_auto_fixture production path exactly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests._fixtures import load_growth_fixture, to_auto_fixture

from room_layout.schema import (
    FloorShape,
    ProgramRequest,
    ShapeInput,
    ShapePart,
    SpaceUnitSpec,
    from_dict,
)
from room_layout.stages.atomize import atomize
from room_layout.stages.growth_partition import region_partition_growth
from room_layout.stages.program_adapter import program_to_fixture
from room_layout.stages.region_graph import build_region_graph
from room_layout.stages.regionize import regionize
from room_layout.stages.room_growth import DEFAULT_ROLE_ASPECT_RANGES, DEFAULT_ROLE_MIN_AREAS

GOLDEN = Path(__file__).parent / "golden"


def _spec(id_: str, role: str, anchor_id: str | None = None) -> SpaceUnitSpec:
    return SpaceUnitSpec(
        id=id_,
        role=role,
        usage=None,
        area_target_m2=10.0,
        area_min_m2=4.0,
        min_dimension_m=None,
        required=True,
        anchor_id=anchor_id,
    )


def _floor(level: int = 1) -> FloorShape:
    return FloorShape(
        level=level,
        parts=[ShapePart(exterior=((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)))],
        floor_to_floor_height=None,
    )


def _program(specs: list[SpaceUnitSpec]) -> ProgramRequest:
    return ProgramRequest(target_type="apartment", floor_programs={1: specs})


def test_hub_maps_to_public_and_goes_first():
    prog = _program([_spec("p1", "private"), _spec("h", "hub"), _spec("w", "wet")])
    fx = program_to_fixture(_floor(), prog)
    assert [r.name for r in fx.rooms] == ["h", "p1", "w"]  # hub first
    assert [r.role for r in fx.rooms] == ["public", "private", "wet"]  # hub→public
    assert fx.hub_room_index == 0
    assert fx.auto_seed is True  # no seeds → production auto path


def test_no_hub_role_uses_first_public_as_hub():
    fx = program_to_fixture(_floor(), _program([_spec("a", "public"), _spec("b", "private")]))
    assert [r.name for r in fx.rooms] == ["a", "b"]
    assert fx.hub_room_index == 0


def test_vertical_circulation_excluded():
    prog = _program(
        [
            _spec("h", "hub"),
            _spec("vc", "vertical_circulation", anchor_id="stair1"),
            _spec("w", "wet"),
        ]
    )
    fx = program_to_fixture(_floor(), prog)
    assert [r.name for r in fx.rooms] == ["h", "w"]  # vc dropped (anchor-locked)
    assert fx.K == 2


def test_role_tables_default_to_cell_constants():
    fx = program_to_fixture(_floor(), _program([_spec("a", "public")]))
    assert fx.role_min_areas == DEFAULT_ROLE_MIN_AREAS
    assert {k: tuple(v) for k, v in fx.role_aspect_ranges.items()} == DEFAULT_ROLE_ASPECT_RANGES


def test_missing_floor_level_raises():
    prog = ProgramRequest(target_type="apartment", floor_programs={2: [_spec("a", "public")]})
    with pytest.raises(ValueError, match="no floor_programs entry for floor level 1"):
        program_to_fixture(_floor(level=1), prog)


def test_all_excluded_raises():
    prog = _program([_spec("vc", "vertical_circulation", anchor_id="s")])
    with pytest.raises(ValueError, match="no growable rooms"):
        program_to_fixture(_floor(), prog)


def test_adapter_reproduces_auto_path_case_01():
    """case_01 via adapter (ProgramRequest) == via to_auto_fixture — same GrowthResult."""
    cd = GOLDEN / "case_01_30py_flat"
    with (cd / "input.json").open(encoding="utf-8") as f:
        data = json.load(f)
    floor = from_dict(ShapeInput, data["shape"]).floors[0]
    program = from_dict(ProgramRequest, data["program"])

    atoms = atomize(floor)
    regions = regionize(floor, atoms=atoms)
    rg = build_region_graph(floor, atoms=atoms, regions=regions)

    fx_adapter = program_to_fixture(floor, program)
    fx_auto = to_auto_fixture(load_growth_fixture(cd))

    r_adapter = region_partition_growth(floor, fx_adapter, regions=regions, region_graph=rg)
    r_auto = region_partition_growth(floor, fx_auto, regions=regions, region_graph=rg)

    dig_a = [(g.name, tuple(sorted(g.region_ids)), round(g.area_m2, 4)) for g in r_adapter.rooms]
    dig_b = [(g.name, tuple(sorted(g.region_ids)), round(g.area_m2, 4)) for g in r_auto.rooms]
    assert dig_a == dig_b
    assert r_adapter.unassigned_region_ids == r_auto.unassigned_region_ids
