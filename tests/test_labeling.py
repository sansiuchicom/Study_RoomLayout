"""Labeling tests (Step 07 §4.3) — grown rooms → LabeledRoom / LabeledFloorLayout.

A focused unit test pins the authoritative-role recovery (growth collapses
hub→public; labeling must recover ``'hub'`` from the spec, not echo the grown
role) and the S07-D6 area source (polygon, not ``GrownRoom.area_m2``). The
33-case sweep runs ``label_floor`` over real carved output with specs
synthesized from each ``growth_fixture`` (corpus-A style).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import get_args

import pytest
from shapely.geometry import Polygon
from tests._fixtures import load_growth_fixture

from room_layout.schema import Role, ShapeInput, SpaceUnitSpec, from_dict
from room_layout.stages.atomize import atomize
from room_layout.stages.corridor import carve_corridors
from room_layout.stages.growth_partition import region_partition_growth
from room_layout.stages.labeling import label_floor, label_room
from room_layout.stages.region_graph import build_region_graph
from room_layout.stages.regionize import regionize
from room_layout.stages.room_growth import GrownRoom

GOLDEN = Path(__file__).parent / "golden"
SEVEN_ROLES = set(get_args(Role))


# ---- unit: authoritative role/usage recovery + area source ----------------


def test_label_room_recovers_7class_role_and_usage_from_spec():
    # growth collapsed hub -> public (S04-D3); the spec carries the real role.
    grown = GrownRoom(name="foyer_1", role="public", region_ids=(0, 1), area_m2=99.0)
    spec = SpaceUnitSpec(
        id="foyer_1", role="hub", usage="entry foyer", area_min_m2=1.0, required=True
    )
    poly = Polygon([(0, 0), (3, 0), (3, 4), (0, 4)])  # area 12
    room = label_room(grown, spec, poly)
    assert room.role == "hub"  # recovered from spec, NOT grown.role="public"
    assert room.usage == "entry foyer"  # carried through (S06-D3)
    assert room.id == "foyer_1"
    assert room.area_m2 == pytest.approx(12.0)  # polygon area (S07-D6), not grown.area_m2=99
    assert room.anchor_id is None
    assert room.doors is None


def test_label_room_carries_none_usage():
    grown = GrownRoom(name="bed_1", role="private", region_ids=(0,), area_m2=10.0)
    spec = SpaceUnitSpec(id="bed_1", role="private", usage=None, area_min_m2=1.0, required=True)
    room = label_room(grown, spec, Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]))
    assert room.usage is None
    assert room.role == "private"


# ---- 33-case sweep --------------------------------------------------------


def _carve(case_dir: Path):
    with (case_dir / "input.json").open(encoding="utf-8") as f:
        floor = from_dict(ShapeInput, json.load(f)["shape"]).floors[0]
    fixture = load_growth_fixture(case_dir)
    atoms = atomize(floor)
    regions = regionize(floor, atoms=atoms)
    rg = build_region_graph(floor, atoms=atoms, regions=regions)
    growth = region_partition_growth(floor, fixture, regions=regions, region_graph=rg)
    return carve_corridors(floor, growth, regions=regions, region_graph=rg), regions, floor


def _specs_from(corridored):
    """One SpaceUnitSpec per grown room (corpus-A synthesis): the growth role is
    already a valid 7-class role; a distinctive usage proves carry-through."""
    return [
        SpaceUnitSpec(
            id=gr.name, role=gr.role, usage=f"u_{gr.name}", area_min_m2=0.1, required=True
        )
        for gr in corridored.rooms
    ]


_CASES = sorted(p.name for p in GOLDEN.iterdir() if p.is_dir())


@pytest.mark.parametrize("case", _CASES)
def test_label_floor_over_33_cases(case):
    cl, regions, floor = _carve(GOLDEN / case)
    fl = label_floor(cl, regions, _specs_from(cl), level=floor.level)

    assert fl.level == floor.level
    assert len(fl.rooms) == len(cl.rooms)
    by_id = {r.id: r for r in fl.rooms}
    for gr in cl.rooms:
        room = by_id[gr.name]
        assert room.role in SEVEN_ROLES
        assert room.usage == f"u_{gr.name}"
        assert room.polygon.geom_type == "Polygon" and room.polygon.is_valid
        assert room.area_m2 == room.polygon.area  # S07-D6 source
        assert room.area_m2 > 0
        assert room.anchor_id is None
        assert room.doors is None
    # corridors come through as polygons, not rooms
    assert all(p.geom_type == "Polygon" and p.is_valid for p in fl.corridor_polygons)
