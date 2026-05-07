"""Tests for TargetAdapter Protocol + ApartmentAdapter (S04-D3, S04-D12)."""
from __future__ import annotations

from pathlib import Path

from proto3.schema.input import BuildingInput
from proto3.target import ApartmentAdapter

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_apartment_adapter_load_fixture_returns_building_input():
    b = ApartmentAdapter().load_fixture(FIXTURES / "apartment_minimal.json")
    assert isinstance(b, BuildingInput)
    assert b.target_type == "apartment"
    assert len(b.floors) == 1


def test_apartment_adapter_target_rules_min_cardinality():
    rules = ApartmentAdapter().target_rules()
    assert "min_cardinality" in rules
    assert rules["min_cardinality"] == {"public": 1, "private": 1, "wet": 1}
