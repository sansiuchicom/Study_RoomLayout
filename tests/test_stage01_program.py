"""Tests for stages.stage01_program (S04-D4, S04-D11, S04-D12, S06-D7, D10, D023).

Step 06 §4.5 expansions on top of the §4.2 transitional state:
- All SpaceUnitSpec fields preserved (required / min_area_m2 /
  min_dimension_mm / max_area_m2 / preferred_area_m2).
- Default fill: None min_area_m2 → role default from TargetRules.
- Duplicate `name` / unknown `role` / type mismatch → ProgramInstantiationFailure.
- D023 required-only cardinality.
"""
from __future__ import annotations

import pytest

from proto3.schema.input import BuildingInput
from proto3.schema.program import ProgramInstance, ProgramRequest, SpaceUnitSpec
from proto3.schema.serialize import from_json
from proto3.schema.validation import ProgramInstantiationFailure
from proto3.stages import stage01_program
from proto3.target import DEFAULT_APARTMENT_RULES_PATH, TargetAdapter

from .fixture_matrix import fixture_path


def _load(matrix_id: str) -> BuildingInput:
    return from_json(BuildingInput, fixture_path(matrix_id))


def _adapter() -> TargetAdapter:
    return TargetAdapter(DEFAULT_APARTMENT_RULES_PATH)


def _building(*units: SpaceUnitSpec) -> BuildingInput:
    return BuildingInput(
        target_type="apartment",
        program_request=ProgramRequest(spaces=list(units)),
    )


# --- Fixture round-trip happy paths -------------------------------------------------

@pytest.mark.parametrize("matrix_id", ["A1", "A2", "B1", "R2"])
def test_stage01_passes_when_cardinality_satisfied(matrix_id):
    b = _load(matrix_id)
    inst = stage01_program.run(b, adapter=_adapter())
    assert isinstance(inst, ProgramInstance)
    assert len(inst.space_units) == len(b.program_request.spaces)


def test_stage01_r1_raises_program_instantiation_failure():
    b = _load("R1")
    with pytest.raises(ProgramInstantiationFailure) as exc_info:
        stage01_program.run(b, adapter=_adapter())
    failure = exc_info.value.failure
    assert failure.failure_type == "program_cardinality_insufficient"
    assert failure.affected_space == "wet"
    assert failure.evidence == {"role": "wet", "required": 1, "actual": 0}
    assert failure.detected_stage == "01"


# --- Field preservation (S06-D7) ---------------------------------------------------

def test_stage01_preserves_all_space_unit_spec_fields():
    """§4.2 frame dropped fields beyond name/role; §4.5 must preserve everything."""
    b = _building(
        SpaceUnitSpec(
            name="bedroom_master",
            role="private",
            required=False,                 # not default — D023 preservation check
            min_area_m2=9.5,
            max_area_m2=15.0,
            preferred_area_m2=12.0,
            min_dimension_mm=2700,
        ),
        # second private with required=True so cardinality (D023) passes
        SpaceUnitSpec(name="bedroom_kid", role="private"),
        SpaceUnitSpec(name="living", role="public", min_area_m2=14.0),
        SpaceUnitSpec(name="bathroom", role="wet", min_area_m2=3.0),
    )
    inst = stage01_program.run(b, adapter=_adapter())

    bm = next(u for u in inst.space_units if u.name == "bedroom_master")
    assert bm.required is False                # required preserved
    assert bm.min_area_m2 == 9.5
    assert bm.max_area_m2 == 15.0
    assert bm.preferred_area_m2 == 12.0
    assert bm.min_dimension_mm == 2700
    assert bm.role == "private"

    bk = next(u for u in inst.space_units if u.name == "bedroom_kid")
    assert bk.required is True                 # default preserved
    assert bk.min_area_m2 == 7.0               # role default fill


# --- min_area_m2 default fill (S06-D7) ---------------------------------------------

def test_stage01_fills_none_min_area_with_role_default():
    """None min_area_m2 → TargetRules.default_min_area_m2[role]."""
    b = _building(
        SpaceUnitSpec(name="living", role="public"),       # None → 12.0
        SpaceUnitSpec(name="bedroom", role="private"),     # None → 7.0
        SpaceUnitSpec(name="bathroom", role="wet"),        # None → 3.0
    )
    inst = stage01_program.run(b, adapter=_adapter())

    by_name = {u.name: u for u in inst.space_units}
    assert by_name["living"].min_area_m2 == 12.0
    assert by_name["bedroom"].min_area_m2 == 7.0
    assert by_name["bathroom"].min_area_m2 == 3.0


def test_stage01_explicit_min_area_overrides_default():
    """Explicit min_area_m2 wins; default not consulted."""
    b = _building(
        SpaceUnitSpec(name="living", role="public", min_area_m2=20.0),
        SpaceUnitSpec(name="bedroom", role="private", min_area_m2=10.0),
        SpaceUnitSpec(name="bathroom", role="wet", min_area_m2=5.0),
    )
    inst = stage01_program.run(b, adapter=_adapter())

    by_name = {u.name: u for u in inst.space_units}
    assert by_name["living"].min_area_m2 == 20.0     # not 12.0
    assert by_name["bedroom"].min_area_m2 == 10.0
    assert by_name["bathroom"].min_area_m2 == 5.0


# --- Duplicate name guard (S06-D7) -------------------------------------------------

def test_stage01_duplicate_name_raises():
    b = _building(
        SpaceUnitSpec(name="bedroom", role="private"),
        SpaceUnitSpec(name="bedroom", role="private"),    # duplicate
        SpaceUnitSpec(name="bathroom", role="wet"),
        SpaceUnitSpec(name="living", role="public"),
    )
    with pytest.raises(ProgramInstantiationFailure) as exc_info:
        stage01_program.run(b, adapter=_adapter())
    fr = exc_info.value.failure
    assert fr.failure_type == "program_space_name_duplicate"
    assert fr.affected_space == "bedroom"
    assert fr.evidence["index"] == 1


# --- Role validation (S06-D10) -----------------------------------------------------

def test_stage01_role_none_raises():
    """SpaceUnitSpec.role default = None; Stage 01 forbids None reaching cardinality."""
    b = _building(
        SpaceUnitSpec(name="x", role=None),
        SpaceUnitSpec(name="bathroom", role="wet"),
        SpaceUnitSpec(name="living", role="public"),
    )
    with pytest.raises(ProgramInstantiationFailure) as exc_info:
        stage01_program.run(b, adapter=_adapter())
    fr = exc_info.value.failure
    assert fr.failure_type == "program_space_role_invalid"
    assert fr.affected_space == "x"
    assert fr.evidence["role"] is None


def test_stage01_role_unknown_raises():
    """Direct construction can bypass D017 (Python doesn't enforce Literal at runtime).
    Stage 01 is the safety net."""
    b = _building(
        SpaceUnitSpec(name="x", role="rolee"),  # type: ignore[arg-type]
        SpaceUnitSpec(name="bathroom", role="wet"),
        SpaceUnitSpec(name="living", role="public"),
    )
    with pytest.raises(ProgramInstantiationFailure) as exc_info:
        stage01_program.run(b, adapter=_adapter())
    fr = exc_info.value.failure
    assert fr.failure_type == "program_space_role_invalid"
    assert fr.evidence["role"] == "rolee"
    assert "public" in fr.evidence["allowed_roles"]


# --- ProgramRequest type guard (S06-D8 boundary) ------------------------------------

def test_stage01_program_request_type_mismatch_raises():
    """dataclass type hints aren't runtime-enforced; Stage 01 catches misuse
    (e.g., test code passing a raw dict instead of ProgramRequest)."""
    b = BuildingInput(target_type="apartment")
    b.program_request = {"spaces": []}  # type: ignore[assignment]  — deliberate misuse
    with pytest.raises(ProgramInstantiationFailure) as exc_info:
        stage01_program.run(b, adapter=_adapter())
    fr = exc_info.value.failure
    assert fr.failure_type == "program_request_type_invalid"
    assert fr.evidence["got_type"] == "dict"


# --- D023 required-only cardinality -------------------------------------------------

def test_stage01_optional_space_does_not_satisfy_required_cardinality():
    """D023: optional bedroom should NOT count toward `min_cardinality.private = 1`.
    This test exposes the silent-bug from second external review #1."""
    b = _building(
        SpaceUnitSpec(name="living", role="public"),
        SpaceUnitSpec(name="study", role="private", required=False),  # optional
        SpaceUnitSpec(name="bathroom", role="wet"),
    )
    with pytest.raises(ProgramInstantiationFailure) as exc_info:
        stage01_program.run(b, adapter=_adapter())
    fr = exc_info.value.failure
    assert fr.failure_type == "program_cardinality_insufficient"
    assert fr.affected_space == "private"
    assert fr.evidence == {"role": "private", "required": 1, "actual": 0}


def test_stage01_target_mismatch_raises(tmp_path):
    """Defense in depth (merge-prep #2): direct stage01 call with mismatched
    adapter/building target must fail loud (not silently use wrong rules)."""
    b = BuildingInput(
        target_type="hotel",  # adapter is apartment
        program_request=ProgramRequest(spaces=[
            SpaceUnitSpec(name="living", role="public"),
            SpaceUnitSpec(name="bedroom", role="private"),
            SpaceUnitSpec(name="bathroom", role="wet"),
        ]),
    )
    with pytest.raises(ValueError, match="target_type"):
        stage01_program.run(b, adapter=_adapter())


def test_stage01_empty_name_raises():
    """Single empty-name space — dup check would only catch two-empty case."""
    b = _building(
        SpaceUnitSpec(name="", role="public"),
        SpaceUnitSpec(name="bedroom", role="private"),
        SpaceUnitSpec(name="bathroom", role="wet"),
    )
    with pytest.raises(ProgramInstantiationFailure) as exc_info:
        stage01_program.run(b, adapter=_adapter())
    assert exc_info.value.failure.failure_type == "program_space_name_empty"


def test_stage01_required_spaces_satisfy_cardinality_with_optionals_present():
    """Required bedroom satisfies cardinality; optional study is just along for the ride."""
    b = _building(
        SpaceUnitSpec(name="living", role="public"),
        SpaceUnitSpec(name="bedroom", role="private", required=True),
        SpaceUnitSpec(name="study", role="private", required=False),
        SpaceUnitSpec(name="bathroom", role="wet"),
    )
    inst = stage01_program.run(b, adapter=_adapter())
    assert len(inst.space_units) == 4
