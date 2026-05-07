"""Tests for stages.stage00_load (S04-D4, S04-D13)."""
from __future__ import annotations

from pathlib import Path

import pytest

from proto3.config import RunConfig
from proto3.schema.input import BuildingInput
from proto3.stages import stage00_load
from proto3.target import ApartmentAdapter

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_stage00_default_adapter_returns_building_input():
    b = stage00_load.run(FIXTURES / "apartment_minimal.json")
    assert isinstance(b, BuildingInput)
    assert b.target_type == "apartment"


def test_stage00_explicit_adapter():
    b = stage00_load.run(
        FIXTURES / "apartment_minimal.json",
        adapter=ApartmentAdapter(),
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

    def target_rules(self):
        return {}


def test_stage00_target_type_mismatch_raises():
    rc = RunConfig(target_type="apartment")
    with pytest.raises(ValueError, match="target_type mismatch"):
        stage00_load.run(Path("dummy"), run_config=rc, adapter=_MismatchAdapter())
