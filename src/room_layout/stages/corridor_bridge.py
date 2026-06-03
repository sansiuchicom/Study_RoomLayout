"""Orphan-corridor bridging — connect hub-disconnected corridor components.

Plan reference: ``007_Step07_EntryPoint_Plan.md`` §4.11 + the §4.10 finding.

A Stage-2 detour shortcut routes *through rooms* (Cell §4.6 keeps src/tgt
regions as rooms), so its carved regions can form an **orphan** corridor
component disconnected from the hub corridor network. A corridor is *connected
circulation*, so the natural fix is to **bridge** it — carve the shortest room
path from the hub component to the orphan so the corridor becomes one connected
spine — not to dissolve it back into rooms.

This runs *after* ``carve_corridors`` (the Cell stages stay byte-identical) and
carves the intermediate room regions of that shortest path into the corridor.
No-op (returns the input) when the corridor is already one hub-connected
component — the production auto-seed ``run()`` path, where no orphan occurs.
"""

from __future__ import annotations

from collections import deque

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


def _hub_component(corridor: set[int], hub: set[int], adj: dict[int, set[int]]) -> set[int]:
    net = corridor | hub
    seen = {r for r in hub if r in net}
    q = deque(seen)
    while q:
        cur = q.popleft()
        for nb in adj.get(cur, ()):
            if nb in net and nb not in seen:
                seen.add(nb)
                q.append(nb)
    return seen


def _shortest_path(
    sources: set[int], targets: set[int], adj: dict[int, set[int]]
) -> list[int] | None:
    """BFS from ``sources`` to the nearest ``targets`` region; returns the path
    (inclusive of both endpoints), or ``None`` if unreachable."""
    seen = set(sources)
    parent: dict[int, int | None] = {s: None for s in sources}
    q = deque(sources)
    while q:
        cur = q.popleft()
        for nb in adj.get(cur, ()):
            if nb in seen:
                continue
            parent[nb] = cur
            if nb in targets:
                path = [nb]
                x: int | None = cur
                while x is not None:
                    path.append(x)
                    x = parent[x]
                return path[::-1]
            seen.add(nb)
            q.append(nb)
    return None


def bridge_orphan_corridors(
    corridored: CorridoredLayout,
    regions: tuple[Region, ...],
    region_graph: RegionGraph,
) -> CorridoredLayout:
    """Connect orphan corridor components to the hub network by carving the
    shortest room path between them. No-op when already one hub-connected
    component (returns the input unchanged)."""
    hub_idx = corridored.fixture.hub_room_index
    if hub_idx is None:
        return corridored

    adj = _region_adjacency(region_graph)
    area = {r.region_id: to_shapely(r.shape).area for r in regions}

    base = set(corridored.base_corridor_region_ids)
    shortcut = set(corridored.shortcut_corridor_region_ids)
    room_regions = [set(room.region_ids) for room in corridored.rooms]
    region_to_room = {rid: i for i, rs in enumerate(room_regions) for rid in rs}
    hub = room_regions[hub_idx]

    bridges: list[int] = []
    for _ in range(100):  # bounded: each pass connects ≥1 orphan component
        corridor = base | shortcut
        hub_comp = _hub_component(corridor, hub, adj)
        orphan = corridor - hub_comp
        if not orphan:
            break
        path = _shortest_path(hub_comp, orphan, adj)
        if path is None:
            break  # unreachable (should not happen on a connected floor)
        for rid in path:
            if rid in base or rid in shortcut or rid in hub:
                continue  # endpoints / already corridor or hub
            ri = region_to_room.get(rid)
            if ri is not None:
                room_regions[ri].discard(rid)
                del region_to_room[rid]
            base.add(rid)  # the bridge joins the hub-connected base network
            bridges.append(rid)

    if not bridges:
        return corridored

    new_rooms = tuple(
        GrownRoom(
            name=room.name,
            role=room.role,
            region_ids=tuple(sorted(room_regions[i])),
            area_m2=sum(area[rid] for rid in room_regions[i]),
        )
        for i, room in enumerate(corridored.rooms)
    )
    diagnostics = dict(corridored.diagnostics)
    diagnostics["orphan_bridge"] = {"bridge_region_ids": sorted(bridges)}
    return CorridoredLayout(
        fixture=corridored.fixture,
        rooms=new_rooms,
        base_corridor_region_ids=tuple(sorted(base)),
        shortcut_corridor_region_ids=tuple(sorted(shortcut)),
        leftover_region_ids=corridored.leftover_region_ids,
        diagnostics=diagnostics,
    )
