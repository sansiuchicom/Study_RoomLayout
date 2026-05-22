"""Stage 2 detour shortcut routing for corridor carving."""

from __future__ import annotations

import math
from collections import deque

from .corridor_path import (
    _minimize_offending,
    _path_damages_any_room,
    _shortest_region_path,
)
from .corridor_params import (
    CORRIDOR_MAX_RETRY as _CORRIDOR_MAX_RETRY,
    CORRIDOR_SIZE_FLOOR as _CORRIDOR_SIZE_FLOOR,
    CORRIDOR_SIZE_REF as _CORRIDOR_SIZE_REF,
    HUB_SUPERNODE as _HUB_SUPERNODE,
    STAGE2_BOUNDARY_BASE as _STAGE2_BOUNDARY_BASE,
    STAGE2_ENDPOINT_COST as _STAGE2_ENDPOINT_COST,
    STAGE2_FREE_COST as _STAGE2_FREE_COST,
    STAGE2_INTERIOR_BASE as _STAGE2_INTERIOR_BASE,
    STAGE2_MAX_OUTER_ITER as _STAGE2_MAX_OUTER_ITER,
    STAGE2_SRC_TGT_AVOID as _STAGE2_SRC_TGT_AVOID,
)


def _bfs_hop_collapse_hub(
    src_ids: set[int],
    dst_ids: set[int],
    passable: set[int],
    hub_regions: set[int],
    region_adj: dict[int, set[int]],
) -> int | None:
    """BFS hop count with all hub regions collapsed into a single supernode.

    Hub is a free-movement zone in the real walking sense — passing through
    1 vs 5 hub regions is the same "one space traversal". Collapsing makes
    distance reflect this. Corridor stays region-by-region (corridors *are*
    long walks) and so do other rooms.

    Returns hop count or None if unreachable.
    """
    if not src_ids or not dst_ids:
        return None
    src = {r for r in src_ids if r in passable}
    dst = {r for r in dst_ids if r in passable}
    if not src or not dst:
        return None

    def node(rid: int) -> int:
        return _HUB_SUPERNODE if rid in hub_regions else rid

    src_nodes = {node(r) for r in src}
    dst_nodes = {node(r) for r in dst}
    if src_nodes & dst_nodes:
        return 0

    seen: set[int] = set(src_nodes)
    queue: deque[tuple[int, int]] = deque((n, 0) for n in src_nodes)
    while queue:
        cur, d = queue.popleft()
        if cur == _HUB_SUPERNODE:
            adj_regions: set[int] = set()
            for hr in hub_regions:
                if hr in passable:
                    adj_regions.update(region_adj[hr])
            adj_regions -= hub_regions
        else:
            adj_regions = region_adj[cur]
        for nbr in adj_regions:
            if nbr not in passable:
                continue
            nbr_node = node(nbr)
            if nbr_node in seen:
                continue
            if nbr_node in dst_nodes:
                return d + 1
            seen.add(nbr_node)
            queue.append((nbr_node, d + 1))
    return None


def _map_distance_hop(
    src_ids: set[int],
    dst_ids: set[int],
    hub_regions: set[int],
    region_adj: dict[int, set[int]],
    all_region_ids: set[int],
) -> int | None:
    """BFS hop count through any territory region, with hub collapsed."""
    return _bfs_hop_collapse_hub(
        src_ids, dst_ids,
        passable=all_region_ids,
        hub_regions=hub_regions,
        region_adj=region_adj,
    )


def _corridor_distance_hop(
    entr_src: set[int],
    entr_dst: set[int],
    passable: set[int],
    hub_regions: set[int],
    region_adj: dict[int, set[int]],
) -> int | None:
    """BFS hop count from ``entr_src`` to ``entr_dst`` restricted to
    ``passable`` (corridor ∪ hub ∪ entr_src ∪ entr_dst — see §4.1),
    with hub collapsed to a single supernode.
    """
    return _bfs_hop_collapse_hub(
        entr_src, entr_dst,
        passable=passable,
        hub_regions=hub_regions,
        region_adj=region_adj,
    )


def _find_entrances(
    room_idx: int,
    hub_idx: int | None,
    room_region_ids: dict[int, set[int]],
    corridor: set[int],
    region_adj: dict[int, set[int]],
) -> set[int]:
    """§4.3 — regions to start/end the strict A* from.

    Normal room R: R's regions 4-adjacent to (corridor ∪ hub).
    Hub: hub's boundary regions (hub regions adjacent to any non-hub region).
    """
    room_regions = room_region_ids.get(room_idx, set())
    if not room_regions:
        return set()
    if room_idx == hub_idx:
        entrances: set[int] = set()
        for rid in room_regions:
            for nbr in region_adj[rid]:
                if nbr not in room_regions:
                    entrances.add(rid)
                    break
        return entrances
    hub_regions = (
        room_region_ids.get(hub_idx, set()) if hub_idx is not None else set()
    )
    target = corridor | hub_regions
    entrances = set()
    for rid in room_regions:
        for nbr in region_adj[rid]:
            if nbr in target:
                entrances.add(rid)
                break
    return entrances


def _astar_shortcut(
    *,
    start_set: set[int],
    goal_set: set[int],
    src_room_idx: int,
    tgt_room_idx: int,
    hub_idx: int | None,
    room_region_ids: dict[int, set[int]],
    all_corridor: set[int],
    unassigned_set: set[int],
    region_area: dict[int, float],
    region_adj: dict[int, set[int]],
    on_footprint_edge: dict[int, bool],
    forbidden: frozenset[int] = frozenset(),
) -> list[int] | None:
    """§4.4 strict shortcut path search.

    Hub/corridor regions outside the start/goal entrances are hard-blocked so
    the resulting path is forced to carve through other rooms — the whole point
    of a "detour shortcut".
    """
    if not start_set or not goal_set:
        return None

    region_to_room: dict[int, int] = {}
    for room_idx, regions in room_region_ids.items():
        for rid in regions:
            region_to_room[rid] = room_idx

    hub_regions = (
        room_region_ids.get(hub_idx, set()) if hub_idx is not None else set()
    )
    blocked = (hub_regions | all_corridor) - start_set - goal_set

    def cost(rid: int) -> float:
        if rid in forbidden or rid in blocked:
            return math.inf
        if rid in start_set or rid in goal_set:
            return _STAGE2_ENDPOINT_COST
        if rid in unassigned_set:
            return _STAGE2_FREE_COST
        owner = region_to_room.get(rid)
        if owner is None:
            return _STAGE2_FREE_COST
        if owner == src_room_idx or owner == tgt_room_idx:
            return _STAGE2_SRC_TGT_AVOID
        owner_regions = room_region_ids[owner]
        owner_area = sum(region_area[r] for r in owner_regions)
        is_outline = (
            on_footprint_edge.get(rid, False)
            or any(
                region_to_room.get(nbr) != owner for nbr in region_adj[rid]
            )
        )
        base = _STAGE2_BOUNDARY_BASE if is_outline else _STAGE2_INTERIOR_BASE
        return base * (_CORRIDOR_SIZE_REF / max(owner_area, _CORRIDOR_SIZE_FLOOR))

    return _shortest_region_path(
        start_set=start_set,
        goal_set=goal_set,
        region_adj=region_adj,
        cost_fn=cost,
    )


def _stage2_detour_shortcut(
    room_region_ids: dict[int, set[int]],
    base_corridor: set[int],
    unassigned_set: set[int],
    hub_idx: int | None,
    region_area: dict[int, float],
    region_adj: dict[int, set[int]],
    on_footprint_edge: dict[int, bool],
    threshold: float,
) -> tuple[set[int], dict]:
    """§4 — iterative ratio-greedy detour shortcut carving.

    Mutates ``room_region_ids`` and ``unassigned_set`` in place when a
    shortcut path is committed. Returns the new shortcut corridor set
    and per-iteration diagnostics. Disconnection is forbidden via the
    same simulation + minimal-cut retry as Stage 1.
    """
    shortcut_corridor: set[int] = set()
    log: list[dict] = []
    n_rooms = len(room_region_ids)
    if n_rooms < 2:
        return shortcut_corridor, {"iterations": 0, "log": log}

    processed_pairs: set[tuple[int, int]] = set()
    hub_regions_set = (
        room_region_ids.get(hub_idx, set()) if hub_idx is not None else set()
    )
    all_region_ids = set(region_adj.keys())

    for it in range(1, _STAGE2_MAX_OUTER_ITER + 1):
        all_corridor = base_corridor | shortcut_corridor
        worst: tuple[int, int, int, int, float] | None = None
        for i in range(n_rooms):
            for j in range(i + 1, n_rooms):
                if (i, j) in processed_pairs:
                    continue
                a_regs = room_region_ids[i]
                b_regs = room_region_ids[j]
                if not a_regs or not b_regs:
                    continue
                entr_a = _find_entrances(
                    i, hub_idx, room_region_ids, all_corridor, region_adj,
                )
                entr_b = _find_entrances(
                    j, hub_idx, room_region_ids, all_corridor, region_adj,
                )
                if not entr_a or not entr_b:
                    continue
                passable = (
                    all_corridor | hub_regions_set | entr_a | entr_b
                )
                dc = _corridor_distance_hop(
                    entr_a, entr_b, passable,
                    hub_regions=hub_regions_set,
                    region_adj=region_adj,
                )
                if dc is None:
                    continue
                dm = _map_distance_hop(
                    a_regs, b_regs,
                    hub_regions=hub_regions_set,
                    region_adj=region_adj,
                    all_region_ids=all_region_ids,
                )
                if dm is None or dm <= 1:
                    # Already 4-adjacent — no detour to shortcut.
                    continue
                ratio = dc / max(dm, 1)
                if worst is None or ratio > worst[4]:
                    worst = (i, j, dm, dc, ratio)

        if worst is None or worst[4] <= threshold:
            break
        a, b, dm, dc, ratio = worst
        all_corridor = base_corridor | shortcut_corridor
        entr_a = _find_entrances(
            a, hub_idx, room_region_ids, all_corridor, region_adj,
        )
        entr_b = _find_entrances(
            b, hub_idx, room_region_ids, all_corridor, region_adj,
        )

        forbidden: set[int] = set()
        path: list[int] | None = None
        attempts = 0
        excluded_for_simulation = (
            room_region_ids[a] | room_region_ids[b]
            | hub_regions_set | all_corridor
        )
        for attempts in range(1, _CORRIDOR_MAX_RETRY + 1):
            candidate = _astar_shortcut(
                start_set=entr_a, goal_set=entr_b,
                src_room_idx=a, tgt_room_idx=b, hub_idx=hub_idx,
                room_region_ids=room_region_ids,
                all_corridor=all_corridor,
                unassigned_set=unassigned_set,
                region_area=region_area, region_adj=region_adj,
                on_footprint_edge=on_footprint_edge,
                forbidden=frozenset(forbidden),
            )
            if candidate is None:
                break
            damage = _path_damages_any_room(
                candidate,
                excluded=excluded_for_simulation,
                room_region_ids=room_region_ids, region_adj=region_adj,
            )
            if damage is None:
                path = candidate
                break
            offending, damaged_room = damage
            minimal = _minimize_offending(
                offending, damaged_room, room_region_ids, region_adj,
            )
            forbidden.update(minimal)

        if path is None:
            log.append({
                "iter": it, "a": a, "b": b,
                "dm": dm, "dc": dc, "ratio": round(ratio, 3),
                "result": "astar-failed", "attempts": attempts,
            })
            processed_pairs.add((a, b))
            continue

        carved_now: list[int] = []
        for rid in path:
            if rid in room_region_ids[a] or rid in room_region_ids[b]:
                continue
            if rid in hub_regions_set:
                continue
            if rid in base_corridor or rid in shortcut_corridor:
                continue
            for owner_set in room_region_ids.values():
                owner_set.discard(rid)
            unassigned_set.discard(rid)
            shortcut_corridor.add(rid)
            carved_now.append(rid)
        log.append({
            "iter": it, "a": a, "b": b,
            "dm": dm, "dc": dc, "ratio": round(ratio, 3),
            "result": "carved", "attempts": attempts,
            "path_len": len(path), "carved": carved_now,
        })
        processed_pairs.add((a, b))

    return shortcut_corridor, {"iterations": it, "log": log}
