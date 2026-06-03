"""Corridor stage tests + a deferred-gap PoC (Step 04 §4.13).

The ``xfail`` below pins the unmet PHASE8 §11 validation goal "corridor is a
single connected component (all 33 cases)". A Stage 2 detour shortcut attaches
to the network *through a room entrance* (Cell §4.6 excludes the src/tgt room
regions from carving), so the carved ``base ∪ shortcut ∪ hub`` region set is not
one region-adjacency component. This is faithful to Cell (byte-identical) — the
goal was stated but never implemented and has no Cell test. The fix
(post-Stage-2 bridge-carve, damage-guarded) is deferred to Step 07 with the
S04-D4 access-guarantee cluster — see Plan §5. When implemented, flip this
``xfail`` (``strict=True`` → it fails loudly on xpass).
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path

import pytest
from tests._fixtures import load_growth_fixture

from room_layout.schema import ShapeInput, from_dict
from room_layout.stages.atomize import atomize
from room_layout.stages.corridor import carve_corridors
from room_layout.stages.growth_partition import region_partition_growth
from room_layout.stages.region_graph import build_region_graph
from room_layout.stages.regionize import regionize

GOLDEN = Path(__file__).parent / "golden"


def _carve(case: str):
    cd = GOLDEN / case
    with (cd / "input.json").open(encoding="utf-8") as f:
        floor = from_dict(ShapeInput, json.load(f)["shape"]).floors[0]
    fixture = load_growth_fixture(cd)
    atoms = atomize(floor)
    regions = regionize(floor, atoms=atoms)
    rg = build_region_graph(floor, atoms=atoms, regions=regions)
    growth = region_partition_growth(floor, fixture, regions=regions, region_graph=rg)
    return carve_corridors(floor, growth, regions=regions, region_graph=rg), rg


def _adjacency(rg) -> dict[int, set[int]]:
    adj: dict[int, set[int]] = defaultdict(set)
    for e in rg.edges:
        adj[e.region_a].add(e.region_b)
        adj[e.region_b].add(e.region_a)
    return adj


def _is_one_component(nodes: set[int], adj: dict[int, set[int]]) -> bool:
    if not nodes:
        return True
    start = next(iter(nodes))
    seen = {start}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        for nbr in adj[cur]:
            if nbr in nodes and nbr not in seen:
                seen.add(nbr)
                queue.append(nbr)
    return len(seen) == len(nodes)


def test_case_33_exercises_stage2_shortcut():
    """Sanity: case_33 (donut + wing) is the manual-seed case that fires Stage 2."""
    cl, _ = _carve("case_33_donut_wing")
    assert cl.shortcut_corridor_region_ids


@pytest.mark.xfail(
    reason="PHASE8 §11 'single corridor component' goal, on carve_corridors ITSELF "
    "(Cell-faithful): a Stage-2 detour shortcut attaches through a room entrance (Cell §4.6 "
    "excludes src/tgt regions), so base ∪ shortcut ∪ hub is not one region-adjacency component "
    "for case_33's manual-seed carve. NOTE access is intact — every room reaches the hub via the "
    "base corridor (verified) — and run() bridges the orphan into one connected network via the "
    "repo post-step bridge_orphan_corridors (Step 07 §4.11); the production auto-seed path produces "
    "no orphan at all (verified, 33 cases). This test drives carve_corridors directly, so it stays "
    "xfail as the Cell-faithfulness PoC for the carve stage.",
    strict=True,
)
def test_corridor_network_is_single_component_case_33():
    cl, rg = _carve("case_33_donut_wing")
    adj = _adjacency(rg)
    hub_idx = cl.fixture.hub_room_index
    hub = set(cl.rooms[hub_idx].region_ids) if hub_idx is not None else set()
    network = set(cl.base_corridor_region_ids) | set(cl.shortcut_corridor_region_ids) | hub
    assert _is_one_component(network, adj)
