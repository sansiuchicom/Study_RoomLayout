"""run() end-to-end tests (Step 07 §4.6) — the join.

Happy path on a real footprint (case_01 shape + a program synthesized from its
growth_fixture), determinism (purity), the on_stage trace hook, and graceful
failure injection (area gate / cardinality / unknown typology) upholding
valid=False ⇒ non-empty failure_records (proto3:D018). Anchored end-to-end +
golden LabeledRoomLayouts are corpus A/B (§4.9/§4.10).
"""

from __future__ import annotations

import json
from pathlib import Path

from tests._fixtures import load_growth_fixture

from room_layout import run
from room_layout.schema import ProgramRequest, ShapeInput, StageOutput, from_dict
from room_layout.schema.program import SpaceUnitSpec, TargetType

GOLDEN = Path(__file__).parent / "golden"
SEVEN_ROLES = {
    "public",
    "private",
    "service",
    "wet",
    "hub",
    "corridor",
    "vertical_circulation",
}


def _shape(case: str) -> ShapeInput:
    with (GOLDEN / case / "input.json").open(encoding="utf-8") as f:
        return from_dict(ShapeInput, json.load(f)["shape"])


def _program(specs: list[SpaceUnitSpec], level: int, target_type: TargetType = "apartment"):
    return ProgramRequest(target_type=target_type, floor_programs={level: specs})


def _shape_and_program(case: str) -> tuple[ShapeInput, ProgramRequest]:
    """case shape + a feasible program synthesized from its growth_fixture."""
    shape = _shape(case)
    level = shape.floors[0].level
    fx = load_growth_fixture(GOLDEN / case)
    specs = [
        SpaceUnitSpec(id=r.name, role=r.role, usage=None, area_min_m2=0.5, required=True)
        for r in fx.rooms
    ]
    return shape, _program(specs, level)


# case_01 grows public + private×3 + wet → satisfies apartment cardinality.
CASE = "case_01_30py_flat"


# ---- happy path -----------------------------------------------------------


def test_run_produces_a_valid_apartment_layout():
    shape, program = _shape_and_program(CASE)
    result = run(shape, program, seed=42)

    assert result.valid is True
    assert result.failure_records == []
    assert len(result.floors) == 1
    fl = result.floors[0]
    assert fl.level == shape.floors[0].level
    assert len(fl.rooms) > 0
    for room in fl.rooms:
        assert room.polygon.geom_type == "Polygon" and room.polygon.is_valid
        assert room.area_m2 > 0
        assert room.role in SEVEN_ROLES
    assert all(p.is_valid for p in fl.corridor_polygons)
    assert result.provenance["seed"] == 42
    assert result.provenance["target_type"] == "apartment"


def test_run_is_deterministic():
    shape, program = _shape_and_program(CASE)
    a = run(shape, program, seed=7)
    b = run(shape, program, seed=7)
    assert a.valid == b.valid
    assert [round(r.area_m2, 9) for r in a.floors[0].rooms] == [
        round(r.area_m2, 9) for r in b.floors[0].rooms
    ]


# ---- on_stage trace hook --------------------------------------------------


def test_run_emits_stage_outputs_via_on_stage():
    shape, program = _shape_and_program(CASE)
    seen: list[StageOutput] = []
    run(shape, program, seed=0, on_stage=seen.append)

    assert all(isinstance(so, StageOutput) for so in seen)
    ids = [so.stage_id for so in seen]
    assert ids[0] == "input"
    for stage in ("atomize", "regionize", "region_graph", "growth", "corridor", "labeling"):
        assert stage in ids


def test_run_without_on_stage_is_pure_default():
    # default on_stage=None: no callback, no error
    shape, program = _shape_and_program(CASE)
    assert run(shape, program, seed=0).valid is True


# ---- graceful failure injection (③: never raises out) ---------------------


def test_run_area_gate_failure_is_graceful():
    shape = _shape(CASE)
    level = shape.floors[0].level
    # cardinality satisfied (public/private/wet present) but Σ area_min ≫ capacity
    specs = [
        SpaceUnitSpec(id="p", role="public", usage=None, area_min_m2=1e6, required=True),
        SpaceUnitSpec(id="pr", role="private", usage=None, area_min_m2=1.0, required=True),
        SpaceUnitSpec(id="w", role="wet", usage=None, area_min_m2=1.0, required=True),
    ]
    result = run(shape, _program(specs, level), seed=0)
    assert result.valid is False
    assert result.failure_records  # proto3:D018 invariant
    assert any(f.code == "DOMAIN_AREA_GATE_FAIL" for f in result.failure_records)


def test_run_cardinality_failure_is_graceful():
    shape = _shape(CASE)
    level = shape.floors[0].level
    # no wet → apartment min_cardinality (wet >= 1) unmet
    specs = [
        SpaceUnitSpec(id="p", role="public", usage=None, area_min_m2=1.0, required=True),
        SpaceUnitSpec(id="pr", role="private", usage=None, area_min_m2=1.0, required=True),
    ]
    result = run(shape, _program(specs, level), seed=0)
    assert result.valid is False
    assert result.failure_records


def test_run_unknown_typology_returns_no_target_rules():
    shape = _shape(CASE)
    level = shape.floors[0].level
    specs = [SpaceUnitSpec(id="p", role="public", usage=None, area_min_m2=1.0, required=True)]
    # "hotel" is a valid TargetType Literal but ships no rules file yet (apartment
    # + house are registered — Step 06 / Step 10). Picks any still-unshipped one.
    result = run(shape, _program(specs, level, target_type="hotel"), seed=0)
    assert result.valid is False
    assert [f.code for f in result.failure_records] == ["NO_TARGET_RULES"]


def test_invalid_result_always_has_failure_records():
    # the proto3:D018 invariant across every failure path exercised above
    shape = _shape(CASE)
    level = shape.floors[0].level
    bad = _program(
        [SpaceUnitSpec(id="p", role="public", usage=None, area_min_m2=1.0, required=True)],
        level,
        target_type="hotel",
    )
    result = run(shape, bad, seed=0)
    assert result.valid is False and len(result.failure_records) >= 1
