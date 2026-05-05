"""Serialization round-trip + backward-compat tests (S02-D3, S02-D6)."""
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
