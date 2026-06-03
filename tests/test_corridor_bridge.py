"""corridor_bridge tests (Step 07 §4.11) — orphan-corridor bridging.

``bridge_orphan_corridors`` connects a hub-disconnected ("orphan") corridor
component to the hub corridor network by carving the shortest room path between
them — so the corridor is one connected spine (a corridor is connected
circulation; dissolving it back into rooms would be wrong). The production
``run()`` auto-seed path produces no orphans (verified across all 33 cases), so
bridge is a no-op there — its **firing path** is exercised here via the
manual-seed fixture path, which produces an orphan in case_33 (a ~14 m² floating
Stage-2 detour shortcut).
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path

import pytest
from tests._fixtures import load_growth_fixture

from room_layout.schema import ShapeInput, from_dict
from room_layout.stages._helpers import to_shapely
from room_layout.stages.atomize import atomize
from room_layout.stages.corridor import CorridoredLayout, carve_corridors
from room_layout.stages.corridor_bridge import bridge_orphan_corridors
from room_layout.stages.growth_partition import region_partition_growth
from room_layout.stages.region_graph import build_region_graph
from room_layout.stages.regionize import regionize

GOLDEN = Path(__file__).parent / "golden"


def _carve_manual(case: str):
    """Manual-seed (Cell fixture) carve — the path that produces an orphan."""
    cd = GOLDEN / case
    with (cd / "input.json").open(encoding="utf-8") as f:
        floor = from_dict(ShapeInput, json.load(f)["shape"]).floors[0]
    fixture = load_growth_fixture(cd)
    atoms = atomize(floor)
    regions = regionize(floor, atoms=atoms)
    rg = build_region_graph(floor, atoms=atoms, regions=regions)
    growth = region_partition_growth(floor, fixture, regions=regions, region_graph=rg)
    return carve_corridors(floor, growth, regions=regions, region_graph=rg), regions, rg


def _region_area(regions) -> dict[int, float]:
    return {r.region_id: to_shapely(r.shape).area for r in regions}


def _orphan_area(cl: CorridoredLayout, regions, rg) -> float:
    """Corridor area not reachable from the hub through the corridor network."""
    area = _region_area(regions)
    adj = defaultdict(set)
    for e in rg.edges:
        adj[e.region_a].add(e.region_b)
        adj[e.region_b].add(e.region_a)
    hub_idx = cl.fixture.hub_room_index
    hub = set(cl.rooms[hub_idx].region_ids) if hub_idx is not None else set()
    corr = set(cl.corridor_region_ids)
    net = corr | hub
    seen = set(hub & net)
    q = deque(seen)
    while q:
        cur = q.popleft()
        for nb in adj[cur]:
            if nb in net and nb not in seen:
                seen.add(nb)
                q.append(nb)
    return sum(area[r] for r in corr - seen)


def _room_plus_corridor_area(cl: CorridoredLayout, regions) -> float:
    area = _region_area(regions)
    rooms = sum(area[r] for room in cl.rooms for r in room.region_ids)
    corridor = sum(area[r] for r in cl.corridor_region_ids)
    return rooms + corridor


def test_bridge_connects_the_case_33_orphan_corridor():
    cl, regions, rg = _carve_manual("case_33_donut_wing")
    assert _orphan_area(cl, regions, rg) > 1.0  # precondition: manual-seed carve HAS an orphan

    cl2 = bridge_orphan_corridors(cl, regions, rg)

    assert _orphan_area(cl2, regions, rg) == pytest.approx(0.0, abs=1e-9)  # now hub-connected
    assert _room_plus_corridor_area(cl2, regions) == pytest.approx(
        _room_plus_corridor_area(cl, regions)
    )  # area conserved — a bridge region only moves room → corridor
    # bridging CARVES room regions INTO the corridor, so the corridor grows
    assert len(cl2.corridor_region_ids) > len(cl.corridor_region_ids)
    assert cl2.diagnostics["orphan_bridge"]["bridge_region_ids"]  # a bridge was carved


def test_bridge_is_idempotent_and_noop_without_orphan():
    cl, regions, rg = _carve_manual("case_33_donut_wing")
    cl2 = bridge_orphan_corridors(cl, regions, rg)  # bridges the orphan
    cl3 = bridge_orphan_corridors(cl2, regions, rg)  # nothing left to bridge
    assert cl3 is cl2  # no-op returns the same object
