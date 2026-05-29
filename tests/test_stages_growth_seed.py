"""Tests for stages/growth_seed.py auto seed placement (Step 04 §4.9).

Integration smoke + determinism over a real golden case (Phase 3-5 pipeline →
auto_place_seeds_by_cells). Broad auto golden coverage is 4.12.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from room_layout.schema import ShapeInput, from_dict
from room_layout.stages.atomize import atomize
from room_layout.stages.growth_seed import auto_place_seeds_by_cells
from room_layout.stages.region_graph import build_region_graph
from room_layout.stages.regionize import regionize
from room_layout.stages.territory import resolve_territories

GOLDEN = Path(__file__).parent / "golden"
_CASE = "case_06_square_10x10"


def _build(case_name: str = _CASE):
    with (GOLDEN / case_name / "input.json").open(encoding="utf-8") as f:
        floor = from_dict(ShapeInput, json.load(f)["shape"]).floors[0]
    atoms = atomize(floor)
    regions = regionize(floor, atoms=atoms)
    rg = build_region_graph(floor, atoms=atoms, regions=regions)
    terrs = resolve_territories(floor)
    return floor, rg, terrs


def test_auto_place_returns_k_distinct_valid_seeds():
    floor, rg, terrs = _build()
    placements = auto_place_seeds_by_cells(floor, rg, terrs, K=4, has_public=True)
    assert len(placements) == 4
    ids = [p.region.region_id for p in placements]
    assert len(set(ids)) == 4  # all distinct
    assert placements[0].phase == "hub"  # has_public → first is the hub
    valid = {r.region_id for r in rg.regions}
    assert all(i in valid for i in ids)


def test_auto_place_no_public_has_no_hub_phase():
    floor, rg, terrs = _build()
    placements = auto_place_seeds_by_cells(floor, rg, terrs, K=2, has_public=False)
    assert len(placements) == 2
    assert all(p.phase != "hub" for p in placements)


def test_auto_place_k_must_be_positive():
    floor, rg, terrs = _build()
    with pytest.raises(ValueError, match="K must be >= 1"):
        auto_place_seeds_by_cells(floor, rg, terrs, K=0, has_public=True)


def test_auto_place_is_deterministic():
    floor, rg, terrs = _build()
    a = auto_place_seeds_by_cells(floor, rg, terrs, K=4, has_public=True)
    b = auto_place_seeds_by_cells(floor, rg, terrs, K=4, has_public=True)
    assert [p.region.region_id for p in a] == [p.region.region_id for p in b]
    assert [p.phase for p in a] == [p.phase for p in b]
