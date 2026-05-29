"""All 33 growth_fixture.json load into valid LayoutFixtures (Step 04 §4.7)."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests._fixtures import load_growth_fixture

from room_layout.stages.room_growth import (
    DEFAULT_ROLE_ASPECT_RANGES,
    DEFAULT_ROLE_MIN_AREAS,
)

GOLDEN_DIR = Path(__file__).parent / "golden"
CASE_DIRS = sorted(p for p in GOLDEN_DIR.iterdir() if p.is_dir() and p.name.startswith("case_"))
_CASE_IDS = [p.name for p in CASE_DIRS] or None


def test_all_33_cases_present():
    assert len(CASE_DIRS) == 33


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=_CASE_IDS)
def test_growth_fixture_loads(case_dir: Path):
    fx = load_growth_fixture(case_dir)
    assert fx.K >= 1
    # the 33 Cell goldens are all manual-seed (S04-D7)
    assert fx.auto_seed is False
    # role tables are Cell's shared defaults
    assert fx.role_min_areas == DEFAULT_ROLE_MIN_AREAS
    assert {k: tuple(v) for k, v in fx.role_aspect_ranges.items()} == DEFAULT_ROLE_ASPECT_RANGES


def test_case_01_matches_cell():
    fx = load_growth_fixture(GOLDEN_DIR / "case_01_30py_flat")
    assert fx.case_index == 1
    assert fx.K == 5
    assert [r.name for r in fx.rooms] == [f"space_{i}" for i in range(1, 6)]
    assert [r.role for r in fx.rooms] == ["public", "private", "private", "private", "wet"]
    assert fx.hub_room_index == 0  # first public
    assert fx.rooms[0].seed_position == (3.5, 5.0)
