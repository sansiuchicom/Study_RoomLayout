"""Phase 8: Corridor Carving — base corridor + detour shortcut + cleanup.

See ``PHASE8_Corridor.md`` for the full spec. W2 implements Stage 1
(hub-radial base corridor) in the simplest possible form: one A* call
per target, no retries, no fallbacks, no cut-vertex protection.
Stage 2 (detour shortcut) lands in W3 and cleanup in W4.

The baseline is intentionally bare so we can see, on the 33 fixtures,
exactly which cases the §3 cost table alone can solve and which need
additional mechanisms. Patches go on top of this, not into it.
"""

from __future__ import annotations

import heapq
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field

import shapely.geometry as sg
from shapely.ops import unary_union

from .atomize import atomize
from .dimensions import DimensionPolicy
from .region_graph import build_region_graph
from .regionize import Region, regionize
from .room_growth import GrownRoom, GrowthResult, LayoutFixture
from .schema import ShapeInput, ShapePart


# ---------- Stage 1 cost constants -------------------------------------

# PHASE8_Corridor.md §3 cost table. Sandbox used numbers in cell-count
# units; we translate to m² with `_STAGE1_SIZE_REF` ≈ a typical Korean
# apartment room area and `_STAGE1_SIZE_FLOOR` keeping tiny rooms from
# blowing up the cost.
_STAGE1_ENDPOINT_COST = 0.01     # hub / target room regions
_STAGE1_FREE_COST     = 0.01     # unassigned or already-carved corridor
_STAGE1_BOUNDARY_BASE = 1.0      # other-room boundary region (any kind)
_STAGE1_INTERIOR_BASE = 8.0      # other-room interior region
_STAGE1_SIZE_REF      = 20.0     # m² reference for `× 20 / room_size`
_STAGE1_SIZE_FLOOR    = 4.0      # m² lower bound on room_size in cost
_STAGE1_MAX_RETRY     = 30       # simulation-retry budget per target


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


# ---------- Region index helpers ---------------------------------------


def _to_shapely(part: ShapePart) -> sg.Polygon:
    if part.holes:
        return sg.Polygon(part.exterior, holes=part.holes)
    return sg.Polygon(part.exterior)


def _build_region_index(
    shape: ShapeInput,
    policy: DimensionPolicy | None,
) -> tuple[
    tuple[Region, ...],
    dict[int, sg.Polygon],
    dict[int, float],
    dict[int, set[int]],
    dict[int, bool],
]:
    """Return ``(regions, region_poly, region_area, region_adj, on_footprint_edge)``.

    ``on_footprint_edge[rid]`` is True iff the region's polygon shares a
    positive-length stretch with the footprint outer/hole boundary. Such
    a region is on the *outside* of whatever it belongs to — its other
    side is not another region but the wall/exterior. For the corridor
    cost it is just as much a "room edge" as a region next to another
    room (PHASE8_Corridor.md §3 — spec intent "방 외곽선을 따라 흐르고"
    is about a room's outer outline regardless of what is on the other
    side).
    """
    atoms = atomize(shape, policy)
    regions = regionize(shape, atoms=atoms, policy=policy)
    rg = build_region_graph(shape, atoms=atoms, regions=regions, policy=policy)

    region_poly: dict[int, sg.Polygon] = {
        r.region_id: _to_shapely(r.shape) for r in regions
    }
    region_area: dict[int, float] = {
        rid: poly.area for rid, poly in region_poly.items()
    }
    region_adj: dict[int, set[int]] = defaultdict(set)
    for e in rg.edges:
        region_adj[e.region_a].add(e.region_b)
        region_adj[e.region_b].add(e.region_a)
    for r in regions:
        region_adj.setdefault(r.region_id, set())

    footprint = unary_union([_to_shapely(p) for p in shape.parts])
    footprint_boundary = footprint.boundary  # outer ring + holes
    on_footprint_edge: dict[int, bool] = {}
    for rid, poly in region_poly.items():
        contact = poly.boundary.intersection(footprint_boundary)
        on_footprint_edge[rid] = (
            not contact.is_empty and contact.length > 1e-6
        )

    return regions, region_poly, region_area, region_adj, on_footprint_edge


def _set_adjacent_to_set(
    set_a: set[int],
    set_b: set[int],
    region_adj: dict[int, set[int]],
) -> bool:
    """True iff any region in A is 4-adjacent to any region in B."""
    if not set_a or not set_b:
        return False
    for rid in set_a:
        for nbr in region_adj[rid]:
            if nbr in set_b:
                return True
    return False


def _room_is_connected(
    region_ids: set[int],
    region_adj: dict[int, set[int]],
) -> bool:
    """Single-component check via BFS on region adjacency."""
    if not region_ids:
        return True
    start = next(iter(region_ids))
    seen = {start}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        for nbr in region_adj[cur]:
            if nbr in region_ids and nbr not in seen:
                seen.add(nbr)
                queue.append(nbr)
    return len(seen) == len(region_ids)


# ---------- Stage 1: base corridor (hub-radial) ------------------------


def _path_damages_any_room(
    path: list[int],
    *,
    excluded: set[int],
    room_region_ids: dict[int, set[int]],
    region_adj: dict[int, set[int]],
) -> tuple[set[int], int] | None:
    """Simulate carving ``path`` and return ``(offending, room_idx)`` for
    the first room that would be emptied or split — else None.

    ``excluded`` is the set of path regions that are NOT carved (Stage 1:
    hub + target endpoints; Stage 2: hub + src + tgt + existing corridor).
    Only path regions outside ``excluded`` count toward each owning room's
    carve simulation.
    """
    owner_carve: dict[int, set[int]] = defaultdict(set)
    for rid in path:
        if rid in excluded:
            continue
        for room_idx, regions in room_region_ids.items():
            if rid in regions:
                owner_carve[room_idx].add(rid)
                break
    for room_idx, carved in owner_carve.items():
        remaining = room_region_ids[room_idx] - carved
        if not remaining or not _room_is_connected(remaining, region_adj):
            return carved, room_idx
    return None


def _minimize_offending(
    offending: set[int],
    damaged_room_idx: int,
    room_region_ids: dict[int, set[int]],
    region_adj: dict[int, set[int]],
) -> set[int]:
    """Greedy minimal cut: drop any region whose removal leaves the rest
    still damaging.

    A whole carved path may include "innocent" regions whose removal alone
    doesn't disconnect the room — they only happened to be on the path
    that, *combined* with the genuinely critical regions, caused the split.
    Forbidding only the minimal critical subset lets the next A* attempt
    re-use those innocent regions in a different combination (e.g. case 10:
    the right-column path shares R5 with the slicing path, but R5 is not
    itself essential to the split).

    Greedy single pass: O(N) iterations × O(N) connectivity check, where N
    is the offending path's region count in the damaged room (typically ≤ 5).
    """
    candidate = set(offending)
    room_regions = room_region_ids[damaged_room_idx]
    for rid in list(offending):
        if rid not in candidate:
            continue
        test = candidate - {rid}
        if not test:
            break
        remaining = room_regions - test
        still_damages = (
            not remaining or not _room_is_connected(remaining, region_adj)
        )
        if still_damages:
            candidate = test
    return candidate


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
        return base * (_STAGE1_SIZE_REF / max(owner_area, _STAGE1_SIZE_FLOOR))

    pq: list[tuple[float, int]] = []
    g_score: dict[int, float] = {}
    came_from: dict[int, int] = {}
    for rid in start_set:
        g_score[rid] = 0.0
        heapq.heappush(pq, (0.0, rid))

    goal_reached: int | None = None
    while pq:
        cur_g, cur = heapq.heappop(pq)
        if cur_g > g_score[cur] + 1e-9:
            continue
        if cur in goal_set:
            goal_reached = cur
            break
        for nbr in region_adj[cur]:
            step = cost(nbr)
            if math.isinf(step):
                continue
            new_g = cur_g + step
            if new_g < g_score.get(nbr, math.inf) - 1e-9:
                g_score[nbr] = new_g
                came_from[nbr] = cur
                heapq.heappush(pq, (new_g, nbr))

    if goal_reached is None:
        return None
    path = [goal_reached]
    while path[-1] in came_from:
        path.append(came_from[path[-1]])
    path.reverse()
    return path


def _stage1_base_corridor(
    growth_result: GrowthResult,
    region_area: dict[int, float],
    region_adj: dict[int, set[int]],
    on_footprint_edge: dict[int, bool],
) -> tuple[dict[int, set[int]], set[int], set[int], dict]:
    """Phase 8 Stage 1 — hub-radial base corridor (baseline).

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
        for attempts_counter in range(1, _STAGE1_MAX_RETRY + 1):
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

_STAGE2_ENDPOINT_COST = 0.01     # entrance regions (start/end)
_STAGE2_FREE_COST     = 0.01     # unassigned
_STAGE2_SRC_TGT_AVOID = 5.0      # non-entrance regions of the pair's rooms
_STAGE2_BOUNDARY_BASE = 1.0      # other-room outline (shared with §3 spec)
_STAGE2_INTERIOR_BASE = 8.0      # other-room interior
_STAGE2_MAX_OUTER_ITER = 30      # outer ratio-greedy iteration cap


_HUB_SUPERNODE = -1   # sentinel for hub collapse in BFS hop counting


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
    """§4.4 strict A*. Hub/corridor regions outside the start/goal entrances
    are hard-blocked so the resulting path is forced to carve through other
    rooms — the whole point of a "detour shortcut".
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
        return base * (_STAGE1_SIZE_REF / max(owner_area, _STAGE1_SIZE_FLOOR))

    pq: list[tuple[float, int]] = []
    g_score: dict[int, float] = {}
    came_from: dict[int, int] = {}
    for rid in start_set:
        g_score[rid] = 0.0
        heapq.heappush(pq, (0.0, rid))

    goal_reached: int | None = None
    while pq:
        cur_g, cur = heapq.heappop(pq)
        if cur_g > g_score[cur] + 1e-9:
            continue
        if cur in goal_set:
            goal_reached = cur
            break
        for nbr in region_adj[cur]:
            step = cost(nbr)
            if math.isinf(step):
                continue
            new_g = cur_g + step
            if new_g < g_score.get(nbr, math.inf) - 1e-9:
                g_score[nbr] = new_g
                came_from[nbr] = cur
                heapq.heappush(pq, (new_g, nbr))

    if goal_reached is None:
        return None
    path = [goal_reached]
    while path[-1] in came_from:
        path.append(came_from[path[-1]])
    path.reverse()
    return path


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
        for attempts in range(1, _STAGE1_MAX_RETRY + 1):
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
# Implemented in W4. See PHASE8_Corridor.md §5.


# ---------- Public entry -----------------------------------------------


def carve_corridors(
    shape: ShapeInput,
    growth_result: GrowthResult,
    *,
    policy: DimensionPolicy | None = None,
) -> CorridoredLayout:
    """Phase 8 entry — see ``PHASE8_Corridor.md``.

    W2 baseline: Stage 1 only, single-shot A* per target. Diagnostics
    record disconnected and emptied rooms for inspection; cleanup is
    deferred to W4.
    """
    (
        _regions, _region_poly, region_area, region_adj, on_footprint_edge,
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
        "phase": "w3-stage1+stage2",
        "stage1": stage1_diag,
        "stage2": stage2_diag,
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
