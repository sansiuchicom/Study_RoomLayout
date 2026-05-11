"""Tests for TargetAdapter (S04-D3 redesigned at S06-D5, D15, D22).

Step 06 §4.3a: single concrete TargetAdapter — no per-typology subclass.
Tests cover: rules_path required, default-path resolves, target_type
property sourced from JSON, fixture target_type guard.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from proto3.schema.input import BuildingInput
from proto3.target import (
    DEFAULT_APARTMENT_RULES_PATH,
    TargetAdapter,
    TargetRules,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _adapter() -> TargetAdapter:
    return TargetAdapter(DEFAULT_APARTMENT_RULES_PATH)


def test_default_apartment_rules_path_resolves_to_existing_file():
    assert DEFAULT_APARTMENT_RULES_PATH.is_file()


def test_target_adapter_requires_rules_path():
    with pytest.raises(TypeError):
        TargetAdapter()  # type: ignore[call-arg]


def test_target_adapter_target_type_property_from_json():
    """target_type is sourced from the JSON, not from a class name (S06-D22)."""
    a = _adapter()
    assert a.target_type == "apartment"


def test_target_adapter_load_fixture_returns_building_input():
    b = _adapter().load_fixture(FIXTURES / "apartment_minimal.json")
    assert isinstance(b, BuildingInput)
    assert b.target_type == "apartment"
    assert len(b.floors) == 1


def test_target_adapter_load_fixture_rejects_wrong_target_type(tmp_path: Path):
    """S06-D15: adapter ↔ fixture mismatch fails loudly even without RunConfig."""
    bad = tmp_path / "hotel.json"
    bad.write_text(
        '{"target_type": "hotel", "floors": [], '
        '"program_request": {"spaces": []}, "persistent_anchors": []}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="target_type='hotel'"):
        _adapter().load_fixture(bad)


def test_target_adapter_target_rules_returns_typed_target_rules():
    rules = _adapter().target_rules()
    assert isinstance(rules, TargetRules)
    assert rules.target_type == "apartment"
    assert rules.min_cardinality == {"public": 1, "private": 1, "wet": 1}
    assert rules.density_factor == 0.85
    assert rules.requires_single_floor is True
    assert rules.default_min_area_m2["private"] == 7.0
