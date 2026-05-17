"""Seed auto-placement — Phase 7 Round 4 (W1 helpers + W2 pipeline).

``auto_place_seeds`` runs three phases:
  A — hub election (highest-centrality region overall; skipped if no public role)
  B — territory coverage (force one seed per top-K-by-area surviving territory)
  C — region-hop FPS for remaining slots, within covered territories only
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable, Literal

import shapely.geometry as sg

from .region_graph import RegionGraph
from .regionize import Region
from .territory import Territory


PlacementPhase = Literal["hub", "coverage", "fps"]


@dataclass(frozen=True)
class SeedPlacement:
    """One placed seed, tagged with the phase that placed it."""

    region: Region
    phase: PlacementPhase


def region_degree(region_id: int, graph: RegionGraph) -> int:
    """Number of region_graph neighbors of ``region_id``."""
    return len(graph.neighbors(region_id))


def region_area(region: Region) -> float:
    """Shapely area of ``region.shape`` (holes subtracted)."""
    holes = [list(h) for h in region.shape.holes]
    return sg.Polygon(region.shape.exterior, holes).area


def territory_of_region(
    region: Region,
    territories: tuple[Territory, ...],
) -> Territory | None:
    """Return the surviving territory whose ``part_id`` matches ``region``.

    ``None`` when no surviving territory matches — the region's source
    part was fully eclipsed by overlap resolution. Caller decides.
    """
    for t in territories:
        if t.part_id == region.part_id:
            return t
    return None


def regions_in_territory(
    territory: Territory,
    graph: RegionGraph,
) -> tuple[Region, ...]:
    """All regions sharing this territory's ``part_id``."""
    return tuple(r for r in graph.regions if r.part_id == territory.part_id)


def pick_top_centrality(
    candidates: Iterable[Region],
    graph: RegionGraph,
) -> Region | None:
    """Highest region-graph degree, tie-break by area DESC.

    ``None`` for an empty candidate set.
    """
    cands = tuple(candidates)
    if not cands:
        return None

    def key(r: Region) -> tuple[int, float]:
        return (region_degree(r.region_id, graph), region_area(r))

    return max(cands, key=key)


def _territory_area(territory: Territory) -> float:
    return sum(
        sg.Polygon(p.exterior, [list(h) for h in p.holes]).area
        for p in territory.pieces
    )


def _bfs_all_distances(src: int, graph: RegionGraph) -> dict[int, int]:
    """All-pairs hop distance from ``src`` on the region graph (BFS)."""
    dists: dict[int, int] = {src: 0}
    queue: deque[int] = deque([src])
    while queue:
        node = queue.popleft()
        for nb in graph.neighbors(node):
            if nb in dists:
                continue
            dists[nb] = dists[node] + 1
            queue.append(nb)
    return dists


_INF_HOP = 10**9


def auto_place_seeds(
    region_graph: RegionGraph,
    territories: tuple[Territory, ...],
    K: int,
    has_public: bool,
) -> tuple[SeedPlacement, ...]:
    """Place ``K`` seeds across the region graph in three phases.

    Selected territories = top ``K`` by area (out of surviving territories).
    Seeds only fall in selected territories; smaller territories' regions
    are intentionally left as unassigned (corridor candidates).

    Raises ``ValueError`` if ``K`` exceeds the total region count of the
    selected territories — that is a fixture misalignment.
    """
    if K <= 0:
        raise ValueError(f"K must be >= 1, got {K}")

    seeds: list[SeedPlacement] = []
    used_ids: set[int] = set()

    # Phase A — Hub
    hub_territory_id: int | None = None
    if has_public:
        hub = pick_top_centrality(region_graph.regions, region_graph)
        if hub is None:
            raise ValueError("region_graph has no regions")
        seeds.append(SeedPlacement(region=hub, phase="hub"))
        used_ids.add(hub.region_id)
        hub_territory_id = hub.part_id

    # Phase B — Territory coverage
    # Pick selected_territories = top (K) by area, ALWAYS including hub's
    # territory if present (it already holds the hub seed).
    covered_part_ids: set[int] = set()
    if hub_territory_id is not None:
        covered_part_ids.add(hub_territory_id)
    other_terrs = [
        t for t in territories if t.part_id not in covered_part_ids
    ]
    other_terrs.sort(key=_territory_area, reverse=True)
    coverage_budget = K - len(covered_part_ids)
    for t in other_terrs[:coverage_budget]:
        members = regions_in_territory(t, region_graph)
        forced = pick_top_centrality(members, region_graph)
        if forced is None:
            # surviving territory with zero regions — unexpected, but skip
            continue
        seeds.append(SeedPlacement(region=forced, phase="coverage"))
        used_ids.add(forced.region_id)
        covered_part_ids.add(t.part_id)

    # Phase C — FPS within covered territories only
    fps_pool: list[Region] = [
        r for r in region_graph.regions
        if r.part_id in covered_part_ids and r.region_id not in used_ids
    ]
    distance_caches: dict[int, dict[int, int]] = {
        s.region.region_id: _bfs_all_distances(s.region.region_id, region_graph)
        for s in seeds
    }

    while len(seeds) < K:
        if not fps_pool:
            raise ValueError(
                f"auto_place_seeds: K={K} exceeds available regions "
                f"({len(seeds)} placed). Check fixture sizing."
            )

        def _min_hop(r: Region) -> int:
            return min(
                distance_caches[seed_id].get(r.region_id, _INF_HOP)
                for seed_id in distance_caches
            )

        next_seed = max(
            fps_pool, key=lambda r: (_min_hop(r), region_area(r))
        )
        seeds.append(SeedPlacement(region=next_seed, phase="fps"))
        used_ids.add(next_seed.region_id)
        distance_caches[next_seed.region_id] = _bfs_all_distances(
            next_seed.region_id, region_graph
        )
        fps_pool = [r for r in fps_pool if r.region_id != next_seed.region_id]

    return tuple(seeds)
