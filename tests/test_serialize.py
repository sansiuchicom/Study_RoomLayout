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
    assert c3.atom_size_mm == 600  # default kept


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
