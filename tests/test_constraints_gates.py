"""Tests for proto3.constraints.gates (Step 06 §4.4, S06-D6, D013, D023, D024).

Covers all 4 gate functions + DomainGateFailure hierarchy. Stage 02
integration test (R2 → AreaGateFailure end-to-end) lives in
test_stage02_gate.py (§4.6).

Required-only summation (D023) is tested explicitly: optional spaces must
NOT influence area / dim gates. Gross footprint × density (D024) is the
area gate's reference; anchor-aware refinement is a future test (Step 12).

`check_access_schema` is dormant in Stage 02 (S06-D12) — but its function
contract still has unit tests so Step 09-10 activation works without
re-discovery.
"""
from __future__ import annotations

import pytest

from proto3.constraints.gates import (
    check_access_schema,
    check_min_area,
    check_min_dim,
    check_multi_floor_feasibility,
)
from proto3.schema.input import BuildingInput, FloorInput
from proto3.schema.program import (
    AccessPolicy,
    ProgramInstance,
    SpaceUnitSpec,
)
from proto3.schema.validation import (
    AccessSchemaFailure,
    AreaGateFailure,
    DimGateFailure,
    DomainGateFailure,
    FailureRecord,
)
from proto3.target import DEFAULT_APARTMENT_RULES_PATH, TargetRules
from proto3.target.rules_loader import load_target_rules


# --- Shared fixtures ----------------------------------------------------------------

def _apartment_rules() -> TargetRules:
    return load_target_rules(DEFAULT_APARTMENT_RULES_PATH)


def _instance_with(*units: SpaceUnitSpec) -> ProgramInstance:
    return ProgramInstance(space_units=list(units))


# --- DomainGateFailure hierarchy ----------------------------------------------------

def test_failure_hierarchy_subclasses():
    """Catching parent must catch all 3 children (S06-D6)."""
    assert issubclass(AreaGateFailure, DomainGateFailure)
    assert issubclass(DimGateFailure, DomainGateFailure)
    assert issubclass(AccessSchemaFailure, DomainGateFailure)


def test_failure_holds_failure_record():
    """S04-D11 pattern: each failure carries a FailureRecord."""
    fr = FailureRecord(failure_type="x", detected_stage="02")
    e = AreaGateFailure(fr)
    assert e.failure is fr
    assert e.failure.failure_type == "x"


# --- check_min_area -----------------------------------------------------------------

def test_check_min_area_passes_when_within_capacity():
    rules = _apartment_rules()
    inst = _instance_with(
        SpaceUnitSpec(name="living", role="public", min_area_m2=12.0),
        SpaceUnitSpec(name="bedroom_1", role="private", min_area_m2=7.0),
        SpaceUnitSpec(name="bathroom_1", role="wet", min_area_m2=3.0),
    )
    # 22 m² required; 50 m² × 0.85 = 42.5 capacity → pass.
    check_min_area(inst, rules, footprint_area_m2=50.0)


def test_check_min_area_raises_when_exceeds_capacity():
    rules = _apartment_rules()
    inst = _instance_with(
        SpaceUnitSpec(name="living", role="public", min_area_m2=12.0),
        SpaceUnitSpec(name="bedroom_1", role="private", min_area_m2=7.0),
        SpaceUnitSpec(name="bedroom_2", role="private", min_area_m2=7.0),
        SpaceUnitSpec(name="kitchen", role="service", min_area_m2=5.0),
        SpaceUnitSpec(name="bathroom_1", role="wet", min_area_m2=3.0),
    )
    # 34 m² required; 16 m² × 0.85 = 13.6 capacity → fail (R2 shape).
    with pytest.raises(AreaGateFailure) as exc_info:
        check_min_area(inst, rules, footprint_area_m2=16.0)
    fr = exc_info.value.failure
    assert fr.failure_type == "domain_area_gate_fail"
    assert fr.detected_stage == "02"
    assert fr.evidence["total_required_area_m2"] == 34.0
    assert fr.evidence["density_factor"] == 0.85


def test_check_min_area_optional_spaces_not_summed():
    """D023: optional spaces don't inflate the required-area total."""
    rules = _apartment_rules()
    inst = _instance_with(
        SpaceUnitSpec(name="living", role="public", min_area_m2=12.0, required=True),
        # Optional bedroom with huge area — must NOT push the gate over.
        SpaceUnitSpec(name="study", role="private", min_area_m2=100.0, required=False),
    )
    # required-only: 12 m² <= 30 × 0.85 = 25.5 → pass.
    # If optional were summed: 112 m² > 25.5 → would fail.
    check_min_area(inst, rules, footprint_area_m2=30.0)


def test_check_min_area_treats_none_as_zero():
    """A space with min_area_m2=None contributes 0 to the sum (Stage 01 fill is
    upstream; this gate is lenient about un-filled None to allow standalone use)."""
    rules = _apartment_rules()
    inst = _instance_with(
        SpaceUnitSpec(name="living", role="public", min_area_m2=12.0),
        SpaceUnitSpec(name="bedroom", role="private", min_area_m2=None),
    )
    # 12 m² ≤ 30 × 0.85 → pass.
    check_min_area(inst, rules, footprint_area_m2=30.0)


# --- check_min_dim ------------------------------------------------------------------

def test_check_min_dim_passes_when_short_side_sufficient():
    inst = _instance_with(
        SpaceUnitSpec(name="bedroom", role="private", min_dimension_mm=2400),
    )
    check_min_dim(inst, footprint_bbox_short_side_mm=4000)


def test_check_min_dim_raises_when_largest_min_dim_exceeds_short_side():
    inst = _instance_with(
        SpaceUnitSpec(name="living", role="public", min_dimension_mm=3000),
        SpaceUnitSpec(name="bedroom", role="private", min_dimension_mm=2400),
    )
    with pytest.raises(DimGateFailure) as exc_info:
        check_min_dim(inst, footprint_bbox_short_side_mm=2500)
    fr = exc_info.value.failure
    assert fr.failure_type == "domain_dim_gate_fail"
    assert fr.affected_space == "living"
    assert fr.evidence["min_dimension_mm"] == 3000
    assert fr.evidence["footprint_bbox_short_side_mm"] == 2500


def test_check_min_dim_optional_spaces_ignored():
    """D023: optional space's min_dimension does not gate."""
    inst = _instance_with(
        SpaceUnitSpec(name="living", role="public", min_dimension_mm=2400, required=True),
        SpaceUnitSpec(name="walk_in_closet", role="private", min_dimension_mm=5000, required=False),
    )
    # required-only: 2400 ≤ 3000 → pass.
    # If optional considered: 5000 > 3000 → would fail.
    check_min_dim(inst, footprint_bbox_short_side_mm=3000)


def test_check_min_dim_no_constraints_passes():
    """No required space has min_dimension_mm → vacuously pass."""
    inst = _instance_with(
        SpaceUnitSpec(name="living", role="public", min_dimension_mm=None),
    )
    check_min_dim(inst, footprint_bbox_short_side_mm=100)


def test_check_min_dim_empty_required_passes():
    """No required spaces at all → vacuous pass (cardinality fail is upstream)."""
    inst = _instance_with()
    check_min_dim(inst, footprint_bbox_short_side_mm=100)


# --- check_access_schema (dormant scaffold) -----------------------------------------

def test_check_access_schema_empty_policies_passes():
    """ProgramRequest slim (S06-D8) → access_policies empty by construction."""
    inst = _instance_with(
        SpaceUnitSpec(name="living", role="public"),
    )
    check_access_schema(inst)


def test_check_access_schema_dependent_on_unknown_space_raises():
    inst = ProgramInstance(
        space_units=[
            SpaceUnitSpec(name="living", role="public"),
            SpaceUnitSpec(name="bedroom_1", role="private"),
        ],
        access_policies=[
            AccessPolicy(
                space_name="bedroom_1",
                dependent_on_space="bedroom_2",  # nonexistent
            ),
        ],
    )
    with pytest.raises(AccessSchemaFailure) as exc_info:
        check_access_schema(inst)
    assert exc_info.value.failure.failure_type == "access_dependent_space_unknown"


def test_check_access_schema_negative_door_boundary_raises():
    inst = ProgramInstance(
        space_units=[SpaceUnitSpec(name="living", role="public")],
        access_policies=[
            AccessPolicy(space_name="living", door_capable_boundary_mm=-100),
        ],
    )
    with pytest.raises(AccessSchemaFailure) as exc_info:
        check_access_schema(inst)
    assert exc_info.value.failure.failure_type == "access_door_boundary_invalid"


def test_check_access_schema_positive_door_boundary_passes():
    inst = ProgramInstance(
        space_units=[SpaceUnitSpec(name="living", role="public")],
        access_policies=[
            AccessPolicy(space_name="living", door_capable_boundary_mm=900),
        ],
    )
    check_access_schema(inst)


# --- check_multi_floor_feasibility --------------------------------------------------

def test_check_multi_floor_single_floor_apartment_passes():
    rules = _apartment_rules()
    building = BuildingInput(
        target_type="apartment",
        floors=[FloorInput()],
    )
    check_multi_floor_feasibility(building, rules)


def test_check_multi_floor_two_floors_with_single_floor_rule_raises():
    rules = _apartment_rules()  # apartment requires_single_floor=True
    building = BuildingInput(
        target_type="apartment",
        floors=[FloorInput(), FloorInput()],
    )
    with pytest.raises(DomainGateFailure) as exc_info:
        check_multi_floor_feasibility(building, rules)
    fr = exc_info.value.failure
    assert fr.failure_type == "domain_multi_floor_not_supported"
    assert fr.evidence["actual_floor_count"] == 2


def test_check_multi_floor_zero_floors_with_single_floor_rule_raises():
    rules = _apartment_rules()
    building = BuildingInput(target_type="apartment", floors=[])
    with pytest.raises(DomainGateFailure):
        check_multi_floor_feasibility(building, rules)


def test_check_multi_floor_does_not_raise_when_rule_disabled(tmp_path):
    """If rules.requires_single_floor=False, multi-floor passes (Step 14 territory)."""
    import json

    multi_payload = {
        "target_type": "house",
        "density_factor": 0.85,
        "requires_single_floor": False,
        "min_cardinality": {"public": 1, "private": 1, "wet": 1},
        "default_min_area_m2": {
            "public": 12.0, "service": 5.0, "private": 7.0,
            "wet": 3.0, "hub": 2.0, "corridor": 0.0,
        },
    }
    p = tmp_path / "house.json"
    p.write_text(json.dumps(multi_payload), encoding="utf-8")
    rules = load_target_rules(p)

    building = BuildingInput(
        target_type="house",
        floors=[FloorInput(), FloorInput()],
    )
    check_multi_floor_feasibility(building, rules)
