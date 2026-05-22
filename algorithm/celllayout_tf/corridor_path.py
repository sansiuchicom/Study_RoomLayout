"""Pathfinding and room-damage helpers for corridor carving."""

from __future__ import annotations

import heapq
import math
from collections import defaultdict
from collections.abc import Callable

from .corridor_index import _room_is_connected


def _shortest_region_path(
    *,
    start_set: set[int],
    goal_set: set[int],
    region_adj: dict[int, set[int]],
    cost_fn: Callable[[int], float],
) -> list[int] | None:
    """Multi-source/multi-goal shortest path over the region graph."""
    if not start_set or not goal_set:
        return None

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
            step = cost_fn(nbr)
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


# ---------- Room-damage simulation helpers -----------------------------


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
