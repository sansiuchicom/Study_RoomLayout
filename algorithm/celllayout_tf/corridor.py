"""Phase 8: Corridor Carving — base corridor + detour shortcut + cleanup.

See ``PHASE8_Corridor.md`` for the full spec. The implementation routes a
hub-radial base corridor, adds detour shortcuts for high-ratio room pairs,
then absorbs leftover regions into corridor or adjacent rooms.
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass, field

import shapely.geometry as sg
from shapely.ops import unary_union

from .corridor_index import (
    _build_region_index,
    _room_is_connected,
    _set_adjacent_to_set,
)
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
    STAGE1_BOUNDARY_BASE as _STAGE1_BOUNDARY_BASE,
    STAGE1_ENDPOINT_COST as _STAGE1_ENDPOINT_COST,
    STAGE1_FREE_COST as _STAGE1_FREE_COST,
    STAGE1_INTERIOR_BASE as _STAGE1_INTERIOR_BASE,
    STAGE2_BOUNDARY_BASE as _STAGE2_BOUNDARY_BASE,
    STAGE2_ENDPOINT_COST as _STAGE2_ENDPOINT_COST,
    STAGE2_FREE_COST as _STAGE2_FREE_COST,
    STAGE2_INTERIOR_BASE as _STAGE2_INTERIOR_BASE,
    STAGE2_MAX_OUTER_ITER as _STAGE2_MAX_OUTER_ITER,
    STAGE2_SRC_TGT_AVOID as _STAGE2_SRC_TGT_AVOID,
)
from .dimensions import DimensionPolicy
from .room_growth import GrownRoom, GrowthResult, LayoutFixture
from .schema import ShapeInput


# ---------- Output type ------------------------------------------------


@dataclass(frozen=True)
class CorridoredLayout:
    """Output of Phase 8.

    ``rooms`` is the post-carve copy of ``GrowthResult.rooms`` — region_ids
    are reduced for any room whose region was carved into corridor.

    ``base_corridor_region_ids`` come from Stage 1 (hub-radial), ``shortcut``
    from Stage 2 (detour). ``leftover_region_ids`` are unassigned regions
    that even cleanup could not absorb (usually empty).
    """
    fixture: LayoutFixture
    rooms: tuple[GrownRoom, ...]
    base_corridor_region_ids: tuple[int, ...]
    shortcut_corridor_region_ids: tuple[int, ...]
    leftover_region_ids: tuple[int, ...]
    diagnostics: dict = field(default_factory=dict)

    @property
    def corridor_region_ids(self) -> tuple[int, ...]:
        """All corridor regions — base + shortcut."""
        return self.base_corridor_region_ids + self.shortcut_corridor_region_ids


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

    Costs follow PHASE8_Corridor.md §3 Stage 1 table. A region of "some
    other room" counts as **boundary** when *any* of its perimeter sits on
    that room's outer outline — whether the other side of that perimeter
    is another room (``region_to_room`` mismatch) or the footprint /
    hole exterior (``on_footprint_edge``). Only regions whose entire
    perimeter is shared with same-room regions get the interior penalty.

    Single shot — no cut-vertex protection, no simulation check, no retry.

    Heuristic is omitted (= 0) — 33 cases × few-hundred regions is plenty
    fast under Dijkstra; A* speed-ups can come later if needed.
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
        is_boundary = (
            on_footprint_edge.get(rid, False)
            or any(
                region_to_room.get(nbr) != owner for nbr in region_adj[rid]
            )
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

    See PHASE8_Corridor.md §3. Targets are processed in ascending area
    order. For each target: hub-direct → corridor-direct → A* once.
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
        return room_region_ids, base_corridor, unassigned_set, {
            "hub_room_idx": None, "log": log,
        }

    hub_regions = room_region_ids[hub_idx]
    if not hub_regions:
        return room_region_ids, base_corridor, unassigned_set, {
            "hub_room_idx": hub_idx, "hub_empty": True, "log": log,
        }

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
        if base_corridor and _set_adjacent_to_set(
            tgt_regions, base_corridor, region_adj,
        ):
            log.append({"room": tgt_idx, "result": "corridor-direct"})
            continue

        # Simulation-retry loop: each A* attempt that turns out to damage
        # some non-target room contributes the offending regions to
        # ``forbidden`` and we try again. Splitting/emptying any room is
        # treated as a hard violation — we'd rather leave the target
        # unreached than ship a layout with a sliced room.
        forbidden: set[int] = set()
        path: list[int] | None = None
        attempts = 0
        for attempts_counter in range(1, _CORRIDOR_MAX_RETRY + 1):
            attempts = attempts_counter
            candidate = _astar_base_corridor(
                start_set=hub_regions, goal_set=tgt_regions,
                room_region_ids=room_region_ids,
                base_corridor=base_corridor, unassigned_set=unassigned_set,
                region_area=region_area, region_adj=region_adj,
                on_footprint_edge=on_footprint_edge,
                forbidden=frozenset(forbidden),
            )
            if candidate is None:
                break
            damage = _path_damages_any_room(
                candidate,
                excluded=hub_regions | tgt_regions,
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
                "room": tgt_idx, "result": "astar-failed",
                "attempts": attempts,
            })
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
        log.append({
            "room": tgt_idx, "result": "ok",
            "attempts": attempts,
            "path_len": len(path), "carved": carved_now,
        })

    return room_region_ids, base_corridor, unassigned_set, {
        "hub_room_idx": hub_idx, "log": log,
    }


# ---------- Stage 2: detour shortcut -----------------------------------

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


# ---------- Cleanup ----------------------------------------------------


def _obb_aspect(geom) -> float:
    """Aspect ratio (long-side / short-side) of the geometry's
    minimum-area rotated rectangle. Works for rotated rooms where
    axis-aligned bbox would over-estimate aspect.
    """
    obb = geom.minimum_rotated_rectangle
    coords = list(obb.exterior.coords)[:4]
    side_lens = []
    for i in range(4):
        ax, ay = coords[i]
        bx, by = coords[(i + 1) % 4]
        side_lens.append(math.hypot(bx - ax, by - ay))
    long_side = max(side_lens)
    short_side = min(side_lens)
    return long_side / max(short_side, 1e-9)


def _cleanup_leftover(
    *,
    fixture: LayoutFixture,
    room_meta: tuple[GrownRoom, ...],
    room_region_ids: dict[int, set[int]],
    base_corridor: set[int],
    shortcut_corridor: set[int],
    leftover: set[int],
    hub_regions: set[int],
    region_poly: dict,
    region_area: dict[int, float],
    region_adj: dict[int, set[int]],
) -> dict:
    """PHASE8_Corridor.md §5 cleanup. Mutates ``room_region_ids``,
    ``base_corridor``, and ``leftover`` in place.

    Priority 1 (iterative): any leftover 4-adjacent to corridor/hub →
    absorb into base_corridor. Newly absorbed regions extend the target
    set, so a cluster of adjacent leftovers all bordering corridor gets
    swallowed in a few sweeps.

    Priority 2 (single pass): any remaining leftover 4-adjacent to some
    room → absorb into the room whose OBB aspect after absorption is
    closest to 1.0 (most-square). Tie-break: smaller room area first.
    Hard gate: skip a candidate if absorbing would push aspect above
    ``fixture.role_aspect_ranges[role].max`` (§6.3). If every candidate
    is gated, leftover stays for Priority 3.

    Priority 3: silent — region remains in ``leftover`` (★ extra space).
    """
    log: dict = {
        "priority1_absorbed": [],
        "priority2_absorbed": [],
        "priority3_kept": [],
    }

    # ----- Priority 1 -----
    target_set: set[int] = base_corridor | shortcut_corridor | hub_regions
    changed = True
    while changed:
        changed = False
        for rid in sorted(leftover):
            if any(nbr in target_set for nbr in region_adj[rid]):
                leftover.discard(rid)
                base_corridor.add(rid)
                target_set.add(rid)
                log["priority1_absorbed"].append(rid)
                changed = True

    # ----- Priority 2 -----
    for rid in sorted(leftover):
        candidate_rooms: set[int] = set()
        for nbr in region_adj[rid]:
            for room_idx, regs in room_region_ids.items():
                if nbr in regs:
                    candidate_rooms.add(room_idx)
                    break
        if not candidate_rooms:
            continue

        best_key: tuple[float, float, int] | None = None
        best_room: int | None = None
        rid_poly = region_poly[rid]
        for room_idx in candidate_rooms:
            room_regs = room_region_ids[room_idx]
            if not room_regs:
                continue
            polys = [region_poly[r] for r in room_regs] + [rid_poly]
            union = unary_union(polys)
            aspect = _obb_aspect(union)
            role = room_meta[room_idx].role
            max_aspect = fixture.role_aspect_ranges[role][1]
            if aspect > max_aspect:
                continue
            room_area_pre = sum(region_area[r] for r in room_regs)
            key = (abs(aspect - 1.0), room_area_pre, room_idx)
            if best_key is None or key < best_key:
                best_key = key
                best_room = room_idx

        if best_room is None:
            continue

        leftover.discard(rid)
        room_region_ids[best_room].add(rid)
        log["priority2_absorbed"].append((rid, best_room))

    # ----- Priority 3 -----
    log["priority3_kept"] = sorted(leftover)
    return log


# ---------- Public entry -----------------------------------------------


def carve_corridors(
    shape: ShapeInput,
    growth_result: GrowthResult,
    *,
    policy: DimensionPolicy | None = None,
) -> CorridoredLayout:
    """Phase 8 entry — see ``PHASE8_Corridor.md``."""
    (
        _regions, region_poly, region_area, region_adj, on_footprint_edge,
    ) = _build_region_index(shape, policy)

    room_region_ids, base_corridor, leftover, stage1_diag = _stage1_base_corridor(
        growth_result, region_area, region_adj, on_footprint_edge,
    )

    shortcut_corridor, stage2_diag = _stage2_detour_shortcut(
        room_region_ids=room_region_ids,
        base_corridor=base_corridor,
        unassigned_set=leftover,
        hub_idx=growth_result.fixture.hub_room_index,
        region_area=region_area,
        region_adj=region_adj,
        on_footprint_edge=on_footprint_edge,
        threshold=growth_result.fixture.detour_threshold,
    )

    hub_idx = growth_result.fixture.hub_room_index
    hub_regions_set = (
        room_region_ids.get(hub_idx, set()) if hub_idx is not None else set()
    )
    cleanup_diag = _cleanup_leftover(
        fixture=growth_result.fixture,
        room_meta=growth_result.rooms,
        room_region_ids=room_region_ids,
        base_corridor=base_corridor,
        shortcut_corridor=shortcut_corridor,
        leftover=leftover,
        hub_regions=hub_regions_set,
        region_poly=region_poly,
        region_area=region_area,
        region_adj=region_adj,
    )

    disconnected: list[int] = []
    emptied: list[int] = []
    for room_idx, regions_set in room_region_ids.items():
        if not regions_set:
            if growth_result.rooms[room_idx].region_ids:
                emptied.append(room_idx)
            continue
        if not _room_is_connected(regions_set, region_adj):
            disconnected.append(room_idx)

    new_rooms = tuple(
        GrownRoom(
            name=old.name,
            role=old.role,
            region_ids=tuple(sorted(room_region_ids[i])),
            area_m2=sum(region_area[r] for r in room_region_ids[i]),
        )
        for i, old in enumerate(growth_result.rooms)
    )

    diagnostics = {
        "phase": "w4-stage1+stage2+cleanup",
        "stage1": stage1_diag,
        "stage2": stage2_diag,
        "cleanup": cleanup_diag,
        "base_corridor_count": len(base_corridor),
        "shortcut_corridor_count": len(shortcut_corridor),
        "disconnected_rooms": tuple(disconnected),
        "emptied_rooms": tuple(emptied),
    }

    return CorridoredLayout(
        fixture=growth_result.fixture,
        rooms=new_rooms,
        base_corridor_region_ids=tuple(sorted(base_corridor)),
        shortcut_corridor_region_ids=tuple(sorted(shortcut_corridor)),
        leftover_region_ids=tuple(sorted(leftover)),
        diagnostics=diagnostics,
    )
