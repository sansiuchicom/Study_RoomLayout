"""Serialization round-trip + backward-compat tests (S02-D3, S02-D6, S02-D13)."""
import pytest

from proto3.schema import BuildingInput, FloorInput, PersistentAnchor
from proto3.schema.serialize import from_dict, from_json, to_json


def test_building_input_round_trip() -> None:
    """to_json then from_json should produce an equal object (S02-D6 minimum)."""
    b1 = BuildingInput(
        target_type="apartment",
        floors=[
            FloorInput(
                footprint=[(0.0, 0.0), (10000.0, 0.0), (10000.0, 8000.0), (0.0, 8000.0)],
                floor_root=(500.0, 0.0),
            ),
        ],
        persistent_anchors=[PersistentAnchor(kind="stair", floors=[1])],
    )
    s = to_json(b1)
    b2 = from_json(BuildingInput, s)
    assert b1 == b2


def test_from_dict_missing_keys_use_defaults() -> None:
    """Backward-compat (S02-D4): missing keys fall back to dataclass defaults.

    Simulates loading an older run_config.json after schema added new fields.
    """
    minimal = {"target_type": "hotel"}
    b = from_dict(BuildingInput, minimal)
    assert b.target_type == "hotel"
    assert b.floors == []
    assert b.persistent_anchors == []
    assert b.program_request == {}


def test_runconfig_round_trip_and_defaults() -> None:
    """RunConfig round-trip + missing keys fall back to defaults."""
    from proto3.config import RunConfig

    c1 = RunConfig(target_type="house", random_seed=7)
    s = to_json(c1)
    c2 = from_json(RunConfig, s)
    assert c1 == c2

    # Missing-key compat
    c3 = from_dict(RunConfig, {"target_type": "warehouse"})
    assert c3.target_type == "warehouse"
    assert c3.atom_size_mm == 300  # default kept (D019 amended from 600 → 300)


def test_from_dict_rejects_non_dict() -> None:
    """S02-D13: non-dict data for a dataclass cls must raise TypeError.

    Previously `from_dict(BuildingInput, [])` returned an empty BuildingInput
    silently because `'name' in []` is always False — every field fell back
    to default. That is a typo/contract bug, not backward-compat.
    """
    with pytest.raises(TypeError):
        from_dict(BuildingInput, [])
    with pytest.raises(TypeError):
        from_dict(BuildingInput, "apartment")
    with pytest.raises(TypeError):
        from_dict(BuildingInput, 42)


def test_from_dict_rejects_unknown_keys_by_default() -> None:
    """S02-D13: unknown keys raise ValueError so typos are caught early."""
    with pytest.raises(ValueError) as exc:
        from_dict(BuildingInput, {"target_typo": "apartment"})
    assert "target_typo" in str(exc.value)


def test_from_dict_strict_unknown_can_be_disabled() -> None:
    """S02-D13: strict_unknown=False is the escape hatch for removed fields.

    Use only when an old serialized file has a field that the schema no
    longer defines. Added fields (the common backward-compat case) need no
    opt-out — that is the missing-key default path.
    """
    b = from_dict(
        BuildingInput,
        {"target_type": "apartment", "removed_field": 99},
        strict_unknown=False,
    )
    assert b.target_type == "apartment"


def test_invalid_layout_candidate_round_trip() -> None:
    """D018: a valid=False LayoutCandidate with failure_records round-trips.

    Exercises the unified-output schema: failure_records (list of dataclass),
    debug_artifact_refs (dict), validation_result (nested dataclass).
    """
    from proto3.schema import FailureRecord, LayoutCandidate, ValidationResult
    from proto3.schema.serialize import from_json, to_json

    lc1 = LayoutCandidate(
        candidate_id="c-001",
        valid=False,
        validation_result=ValidationResult(
            stage="post_repair",
            valid=False,
            hard_failures=["primary_door_boundary_missing"],
        ),
        failure_records=[
            FailureRecord(
                failure_type="primary_door_boundary_missing",
                affected_space="bathroom_1",
                detected_stage="stage_13",
                evidence={"required_mm": 800, "actual_mm": 600},
            ),
        ],
        debug_artifact_refs={"stage_13_svg": "outputs/debug_runs/r1/stage_13_final.svg"},
    )
    s = to_json(lc1)
    lc2 = from_json(LayoutCandidate, s)
    assert lc1 == lc2


def test_from_dict_rejects_invalid_literal_value() -> None:
    """D017: Literal-typed fields validate allowed values at deserialization.

    Without this, `target_type: TargetType` (a Literal alias) would silently
    accept "apartmnt" or any string — fixture typos would only surface much
    later at Stage 00 gate.
    """
    with pytest.raises(ValueError) as exc:
        from_dict(BuildingInput, {"target_type": "apartmnt", "floors": []})
    assert "apartmnt" in str(exc.value)
    assert "apartment" in str(exc.value)  # message lists allowed values

    # Bypassing strict_unknown does NOT bypass Literal validation
    with pytest.raises(ValueError):
        from_dict(
            BuildingInput,
            {"target_type": "garage", "floors": []},
            strict_unknown=False,
        )
