"""Tests for TargetAdapter Protocol + ApartmentAdapter (S04-D3, S06-D5, D9, D15)."""
from __future__ import annotations

from pathlib import Path

import pytest

from proto3.schema.input import BuildingInput
from proto3.target import (
    DEFAULT_APARTMENT_RULES_PATH,
    ApartmentAdapter,
    TargetRules,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _adapter() -> ApartmentAdapter:
    return ApartmentAdapter(DEFAULT_APARTMENT_RULES_PATH)


def test_default_apartment_rules_path_resolves_to_existing_file():
    assert DEFAULT_APARTMENT_RULES_PATH.is_file()


def test_apartment_adapter_requires_rules_path():
    with pytest.raises(TypeError):
        ApartmentAdapter()  # type: ignore[call-arg]


def test_apartment_adapter_load_fixture_returns_building_input():
    b = _adapter().load_fixture(FIXTURES / "apartment_minimal.json")
    assert isinstance(b, BuildingInput)
    assert b.target_type == "apartment"
    assert len(b.floors) == 1


def test_apartment_adapter_load_fixture_rejects_wrong_target_type(tmp_path: Path):
    """S06-D15: adapter ↔ fixture mismatch fails loudly."""
    bad = tmp_path / "hotel.json"
    bad.write_text(
        '{"target_type": "hotel", "floors": [], '
        '"program_request": {"spaces": []}, "persistent_anchors": []}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="expected 'apartment'"):
        _adapter().load_fixture(bad)


def test_apartment_adapter_target_rules_returns_typed_target_rules():
    rules = _adapter().target_rules()
    assert isinstance(rules, TargetRules)
    assert rules.min_cardinality == {"public": 1, "private": 1, "wet": 1}
    assert rules.density_factor == 0.85
    assert rules.requires_single_floor is True
    assert rules.default_min_area_m2["private"] == 7.0
