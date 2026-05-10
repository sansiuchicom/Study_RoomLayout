"""Tests for stages.stage00_load (S04-D4, S04-D13, S06-D5)."""
from __future__ import annotations

from pathlib import Path

import pytest

from proto3.config import RunConfig
from proto3.schema.input import BuildingInput
from proto3.stages import stage00_load
from proto3.target import (
    DEFAULT_APARTMENT_RULES_PATH,
    ApartmentAdapter,
    TargetRules,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_stage00_default_adapter_returns_building_input():
    b = stage00_load.run(FIXTURES / "apartment_minimal.json")
    assert isinstance(b, BuildingInput)
    assert b.target_type == "apartment"


def test_stage00_explicit_adapter():
    b = stage00_load.run(
        FIXTURES / "apartment_minimal.json",
        adapter=ApartmentAdapter(DEFAULT_APARTMENT_RULES_PATH),
    )
    assert b.target_type == "apartment"


def test_stage00_consistent_run_config_passes():
    rc = RunConfig(target_type="apartment")
    b = stage00_load.run(FIXTURES / "apartment_minimal.json", run_config=rc)
    assert b.target_type == "apartment"


def test_stage00_unregistered_target_type_raises():
    rc = RunConfig(target_type="hotel")
    with pytest.raises(ValueError, match="no TargetAdapter registered"):
        stage00_load.run(FIXTURES / "apartment_minimal.json", run_config=rc)


class _MismatchAdapter:
    """Returns a BuildingInput whose target_type differs from RunConfig."""

    def load_fixture(self, path):
        return BuildingInput(target_type="hotel")

    def target_rules(self) -> TargetRules:
        return TargetRules(
            min_cardinality={},
            default_min_area_m2={},
            density_factor=1.0,
            requires_single_floor=True,
        )


def test_stage00_target_type_mismatch_raises():
    rc = RunConfig(target_type="apartment")
    with pytest.raises(ValueError, match="target_type mismatch"):
        stage00_load.run(Path("dummy"), run_config=rc, adapter=_MismatchAdapter())
