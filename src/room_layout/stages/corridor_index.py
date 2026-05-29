"""Region indexing + connectivity helpers for corridor carving — Phase 8 (§4.13).

Plan reference: ``004_Step04_AlgorithmCore_Plan.md`` §4.13 + S04-D1 / S04-D8.

Faithful port of Cell ``corridor_index.py``. **S04-D8**: ``_build_region_index``
takes the Step 03 ``regions`` + ``region_graph`` as parameters instead of
recomputing ``atomize`` / ``regionize`` / ``build_region_graph``; ``shape``→
``floor`` (S03-D13). The other helpers (``_set_adjacent_to_set`` /
``_room_is_connected``) are unchanged. ``on_footprint_edge`` is still derived
from ``floor.parts`` + region boundaries.
"""

from __future__ import annotations

from collections import defaultdict, deque

import shapely.geometry as sg
from shapely.ops import unary_union

from room_layout.schema import FloorShape
from room_layout.stages._helpers import to_shapely as _to_shapely
from room_layout.stages.region_graph import RegionGraph
from room_layout.stages.regionize import Region


def _build_region_index(
    floor: FloorShape,
    regions: tuple[Region, ...],
    region_graph: RegionGraph,
) -> tuple[
    tuple[Region, ...],
    dict[int, sg.Polygon],
    dict[int, float],
    dict[int, set[int]],
    dict[int, bool],
]:
    """Return ``(regions, region_poly, region_area, region_adj, on_footprint_edge)``.

    ``on_footprint_edge[rid]`` is True iff the region's polygon shares a
    positive-length stretch with the footprint outer/hole boundary. Such a
    region is on the *outside* of whatever it belongs to — its other side is
    not another region but the wall/exterior. For the corridor cost it is just
    as much a "room edge" as a region next to another room (PHASE8_Corridor.md
    §3 — spec intent "방 외곽선을 따라 흐르고" is about a room's outer outline
    regardless of what is on the other side).
    """
    region_poly: dict[int, sg.Polygon] = {r.region_id: _to_shapely(r.shape) for r in regions}
    region_area: dict[int, float] = {rid: poly.area for rid, poly in region_poly.items()}
    region_adj: dict[int, set[int]] = defaultdict(set)
    for e in region_graph.edges:
        region_adj[e.region_a].add(e.region_b)
        region_adj[e.region_b].add(e.region_a)
    for r in regions:
        region_adj.setdefault(r.region_id, set())

    footprint = unary_union([_to_shapely(p) for p in floor.parts])
    footprint_boundary = footprint.boundary  # outer ring + holes
    on_footprint_edge: dict[int, bool] = {}
    for rid, poly in region_poly.items():
        contact = poly.boundary.intersection(footprint_boundary)
        on_footprint_edge[rid] = not contact.is_empty and contact.length > 1e-6

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
