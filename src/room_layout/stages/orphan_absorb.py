"""Orphan-corridor absorption — a repo post-process over the Cell-faithful carve.

Plan reference: ``007_Step07_EntryPoint_Plan.md`` §4.11 + the §4.10 finding.

A Stage-2 detour shortcut routes *through rooms* (Cell §4.6 keeps the src/tgt
room regions as rooms), so a shortcut whose carved regions don't reach the hub
through the corridor network becomes an **isolated "orphan" corridor
component** — circulation not connected to the main spine, i.e. dead /
implausible space (a ~14 m² floating strip in case_33). This step runs *after*
``carve_corridors`` — the Cell stages (stage1 / stage2 / cleanup) stay
byte-identical — and gives each orphan corridor region back to its
most-adjacent room, removing the dead corridor.

Access is unaffected: every room already reaches the hub via the **base**
corridor (Stage 1's guarantee); the orphan was an *extra* through-room
shortcut, so absorbing it only enlarges rooms. Returns an updated
``CorridoredLayout``; a **no-op** (returns the input) when the corridor network
is already a single hub-connected component (most cases).
"""

from __future__ import annotations

from collections import Counter, deque

from room_layout.stages._helpers import to_shapely
from room_layout.stages.corridor import CorridoredLayout
from room_layout.stages.region_graph import RegionGraph
from room_layout.stages.regionize import Region
from room_layout.stages.room_growth import GrownRoom


def _region_adjacency(region_graph: RegionGraph) -> dict[int, set[int]]:
    adj: dict[int, set[int]] = {}
    for e in region_graph.edges:
        adj.setdefault(e.region_a, set()).add(e.region_b)
        adj.setdefault(e.region_b, set()).add(e.region_a)
    return adj


def _hub_reachable(network: set[int], hub: set[int], adj: dict[int, set[int]]) -> set[int]:
    """Regions of ``network`` reachable from the hub regions (BFS within network)."""
    seen = {r for r in hub if r in network}
    queue = deque(seen)
    while queue:
        cur = queue.popleft()
        for nb in adj.get(cur, ()):
            if nb in network and nb not in seen:
                seen.add(nb)
                queue.append(nb)
    return seen


def absorb_orphan_corridors(
    corridored: CorridoredLayout,
    regions: tuple[Region, ...],
    region_graph: RegionGraph,
) -> CorridoredLayout:
    """Reassign orphan corridor regions (not hub-reachable via corridors) to
    their most-adjacent room.

    No-op (returns ``corridored`` unchanged) when there is no hub or the
    corridor network is already one hub-connected component. Un-absorbable
    orphans (touching no room even after propagation) stay as corridor.
    """
    hub_idx = corridored.fixture.hub_room_index
    if hub_idx is None:
        return corridored

    adj = _region_adjacency(region_graph)
    region_area = {r.region_id: to_shapely(r.shape).area for r in regions}

    corridor = set(corridored.corridor_region_ids)
    hub_regions = set(corridored.rooms[hub_idx].region_ids)
    reachable = _hub_reachable(corridor | hub_regions, hub_regions, adj)
    orphan = corridor - reachable
    if not orphan:
        return corridored  # single hub-connected component already — nothing to do

    region_to_room: dict[int, int] = {}
    for i, room in enumerate(corridored.rooms):
        for rid in room.region_ids:
            region_to_room[rid] = i

    assigned: dict[int, int] = {}
    pending = set(orphan)
    changed = True
    while pending and changed:
        changed = False
        for rid in sorted(pending):
            counts: Counter[int] = Counter()
            for nb in adj.get(rid, ()):
                if nb in region_to_room:
                    counts[region_to_room[nb]] += 1
            if counts:
                # most-adjacent room; tie-break to the lower room index (deterministic)
                best = min(counts, key=lambda r: (-counts[r], r))
                assigned[rid] = best
                region_to_room[rid] = best  # neighbours may attach via this region next pass
                pending.discard(rid)
                changed = True

    absorbed = set(assigned)
    new_rooms = tuple(
        GrownRoom(
            name=room.name,
            role=room.role,
            region_ids=tuple(
                sorted(set(room.region_ids) | {r for r, ri in assigned.items() if ri == i})
            ),
            area_m2=sum(
                region_area[rid]
                for rid in set(room.region_ids) | {r for r, ri in assigned.items() if ri == i}
            ),
        )
        for i, room in enumerate(corridored.rooms)
    )
    diagnostics = dict(corridored.diagnostics)
    diagnostics["orphan_absorb"] = {
        "orphan_region_ids": sorted(orphan),
        "absorbed": {str(rid): ri for rid, ri in sorted(assigned.items())},
        "unabsorbed_region_ids": sorted(pending),  # stayed corridor (touch no room)
    }
    return CorridoredLayout(
        fixture=corridored.fixture,
        rooms=new_rooms,
        base_corridor_region_ids=tuple(
            r for r in corridored.base_corridor_region_ids if r not in absorbed
        ),
        shortcut_corridor_region_ids=tuple(
            r for r in corridored.shortcut_corridor_region_ids if r not in absorbed
        ),
        leftover_region_ids=corridored.leftover_region_ids,
        diagnostics=diagnostics,
    )
