"""Stage 1 hub-radial base corridor routing — Phase 8 (§4.13).

Plan reference: ``004_Step04_AlgorithmCore_Plan.md`` §4.13 + S04-D1.
Faithful port of Cell ``corridor_stage1.py`` (imports swapped to
``room_layout.stages.*``). Routes a hub→target base corridor per target room
(ascending area), with carve-damage simulation + minimal-cut retry.
"""

from __future__ import annotations

import math

from room_layout.stages.corridor_index import _set_adjacent_to_set
from room_layout.stages.corridor_params import (
    CORRIDOR_MAX_RETRY as _CORRIDOR_MAX_RETRY,
)
from room_layout.stages.corridor_params import (
    CORRIDOR_SIZE_FLOOR as _CORRIDOR_SIZE_FLOOR,
)
from room_layout.stages.corridor_params import (
    CORRIDOR_SIZE_REF as _CORRIDOR_SIZE_REF,
)
from room_layout.stages.corridor_params import (
    STAGE1_BOUNDARY_BASE as _STAGE1_BOUNDARY_BASE,
)
from room_layout.stages.corridor_params import (
    STAGE1_ENDPOINT_COST as _STAGE1_ENDPOINT_COST,
)
from room_layout.stages.corridor_params import (
    STAGE1_FREE_COST as _STAGE1_FREE_COST,
)
from room_layout.stages.corridor_params import (
    STAGE1_INTERIOR_BASE as _STAGE1_INTERIOR_BASE,
)
from room_layout.stages.corridor_path import (
    _minimize_offending,
    _path_damages_any_room,
    _shortest_region_path,
)
from room_layout.stages.room_growth import GrowthResult


def _astar_base_corridor(
    *,
    start_set: set[int],
    goal_set: set[int],
    room_region_ids: dict[int, set[int]],
    base_corridor: set[int],
    unassigned_set: set[int],
    region_area: dict[int, float],
    region_adj: dict[int, set[int]],
    on_footprint_edge: dict[int, bool],
    forbidden: frozenset[int] = frozenset(),
) -> list[int] | None:
    """Multi-source / multi-goal Dijkstra over the region adjacency graph.

    Costs follow PHASE8_Corridor.md §3 Stage 1 table. A region of "some other
    room" counts as **boundary** when *any* of its perimeter sits on that room's
    outer outline — whether the other side is another room
    (``region_to_room`` mismatch) or the footprint / hole exterior
    (``on_footprint_edge``). Only regions whose entire perimeter is shared with
    same-room regions get the interior penalty.

    Single shot — no cut-vertex protection, no simulation check, no retry.
    Heuristic omitted (= 0) — Dijkstra is plenty fast at this scale.
    """
    if not start_set or not goal_set:
        return None

    region_to_room: dict[int, int] = {}
    for room_idx, regions in room_region_ids.items():
        for rid in regions:
            region_to_room[rid] = room_idx

    def cost(rid: int) -> float:
        if rid in forbidden:
            return math.inf
        if rid in start_set or rid in goal_set:
            return _STAGE1_ENDPOINT_COST
        if rid in base_corridor or rid in unassigned_set:
            return _STAGE1_FREE_COST
        owner = region_to_room.get(rid)
        if owner is None:
            return _STAGE1_FREE_COST
        owner_regions = room_region_ids[owner]
        owner_area = sum(region_area[r] for r in owner_regions)
        is_boundary = on_footprint_edge.get(rid, False) or any(
            region_to_room.get(nbr) != owner for nbr in region_adj[rid]
        )
        base = _STAGE1_BOUNDARY_BASE if is_boundary else _STAGE1_INTERIOR_BASE
        return base * (_CORRIDOR_SIZE_REF / max(owner_area, _CORRIDOR_SIZE_FLOOR))

    return _shortest_region_path(
        start_set=start_set,
        goal_set=goal_set,
        region_adj=region_adj,
        cost_fn=cost,
    )


def _stage1_base_corridor(
    growth_result: GrowthResult,
    region_area: dict[int, float],
    region_adj: dict[int, set[int]],
    on_footprint_edge: dict[int, bool],
) -> tuple[dict[int, set[int]], set[int], set[int], dict]:
    """Phase 8 Stage 1 — hub-radial base corridor.

    See PHASE8_Corridor.md §3. Targets are processed in ascending area order.
    For each target: hub-direct → corridor-direct → A* once.
    """
    fixture = growth_result.fixture
    hub_idx = fixture.hub_room_index

    room_region_ids: dict[int, set[int]] = {
        i: set(g.region_ids) for i, g in enumerate(growth_result.rooms)
    }
    base_corridor: set[int] = set()
    unassigned_set: set[int] = set(growth_result.unassigned_region_ids)
    log: list[dict] = []

    if hub_idx is None:
        return (
            room_region_ids,
            base_corridor,
            unassigned_set,
            {"hub_room_idx": None, "log": log},
        )

    hub_regions = room_region_ids[hub_idx]
    if not hub_regions:
        return (
            room_region_ids,
            base_corridor,
            unassigned_set,
            {"hub_room_idx": hub_idx, "hub_empty": True, "log": log},
        )

    target_order = sorted(
        [i for i in range(len(growth_result.rooms)) if i != hub_idx],
        key=lambda i: growth_result.rooms[i].area_m2,
    )

    for tgt_idx in target_order:
        tgt_regions = room_region_ids[tgt_idx]
        if not tgt_regions:
            log.append({"room": tgt_idx, "result": "empty-room-skip"})
            continue
        if _set_adjacent_to_set(tgt_regions, hub_regions, region_adj):
            log.append({"room": tgt_idx, "result": "hub-direct"})
            continue
        if base_corridor and _set_adjacent_to_set(tgt_regions, base_corridor, region_adj):
            log.append({"room": tgt_idx, "result": "corridor-direct"})
            continue

        # Simulation-retry loop: each A* attempt that turns out to damage some
        # non-target room contributes the offending regions to ``forbidden`` and
        # we try again. Splitting/emptying any room is a hard violation — we'd
        # rather leave the target unreached than ship a sliced room.
        forbidden: set[int] = set()
        path: list[int] | None = None
        attempts = 0
        for attempts_counter in range(1, _CORRIDOR_MAX_RETRY + 1):
            attempts = attempts_counter
            candidate = _astar_base_corridor(
                start_set=hub_regions,
                goal_set=tgt_regions,
                room_region_ids=room_region_ids,
                base_corridor=base_corridor,
                unassigned_set=unassigned_set,
                region_area=region_area,
                region_adj=region_adj,
                on_footprint_edge=on_footprint_edge,
                forbidden=frozenset(forbidden),
            )
            if candidate is None:
                break
            damage = _path_damages_any_room(
                candidate,
                excluded=hub_regions | tgt_regions,
                room_region_ids=room_region_ids,
                region_adj=region_adj,
            )
            if damage is None:
                path = candidate
                break
            offending, damaged_room = damage
            minimal = _minimize_offending(offending, damaged_room, room_region_ids, region_adj)
            forbidden.update(minimal)

        if path is None:
            log.append({"room": tgt_idx, "result": "astar-failed", "attempts": attempts})
            continue

        carved_now: list[int] = []
        for rid in path:
            if rid in hub_regions or rid in tgt_regions:
                continue
            for owner_set in room_region_ids.values():
                owner_set.discard(rid)
            unassigned_set.discard(rid)
            base_corridor.add(rid)
            carved_now.append(rid)
        log.append(
            {
                "room": tgt_idx,
                "result": "ok",
                "attempts": attempts,
                "path_len": len(path),
                "carved": carved_now,
            }
        )

    return room_region_ids, base_corridor, unassigned_set, {"hub_room_idx": hub_idx, "log": log}
