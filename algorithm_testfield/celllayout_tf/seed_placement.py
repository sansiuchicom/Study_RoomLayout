"""Seed auto-placement — Phase 7 Round 4 (W1 helpers + W2 pipeline).

``auto_place_seeds`` runs three phases:
  A — hub election (highest-centrality region overall; skipped if no public role)
  B — territory coverage (one seed per top-K-by-area surviving territory,
      spread-aware: prefer the territory member farthest from existing seeds)
  C — FPS for remaining slots, within covered territories only

Both Phase B and Phase C use the same ``_pick_farthest`` ranking:
``(min_hop DESC, min_euclidean DESC, area DESC)``. The Euclidean term breaks
hop ties that arise once 2–3 seeds saturate the region-graph diameter; without
it, hop-tied candidates fall back to area DESC and cluster on large central
regions.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import hypot
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


def _region_centroid(region: Region) -> tuple[float, float]:
    poly = sg.Polygon(region.shape.exterior, [list(h) for h in region.shape.holes])
    rp = poly.representative_point()
    return (rp.x, rp.y)


_INF_HOP = 10**9


def auto_place_seeds(
    region_graph: RegionGraph,
    territories: tuple[Territory, ...],
    K: int,
    has_public: bool,
) -> tuple[SeedPlacement, ...]:
    """Place ``K`` seeds across the region graph in three phases.

    Selected territories = top ``K`` by area. Smaller territories are left
    unassigned (corridor candidates). Phase B and Phase C share a unified
    spread-aware ranking that breaks hop ties by Euclidean distance.

    Raises ``ValueError`` if ``K`` exceeds the total region count of the
    selected territories.
    """
    if K <= 0:
        raise ValueError(f"K must be >= 1, got {K}")

    all_regions = region_graph.regions
    if not all_regions:
        raise ValueError("region_graph has no regions")

    centroid_by_id: dict[int, tuple[float, float]] = {
        r.region_id: _region_centroid(r) for r in all_regions
    }
    distance_caches: dict[int, dict[int, int]] = {}
    seeds: list[SeedPlacement] = []

    def _pick_farthest(candidates: list[Region]) -> Region | None:
        """Spread-aware pick: max(min_hop, min_euclidean, area).

        Falls back to centrality when no seed has been placed yet.
        """
        if not candidates:
            return None
        if not distance_caches:
            return pick_top_centrality(candidates, region_graph)

        seed_ids = list(distance_caches.keys())
        seed_centroids = [centroid_by_id[sid] for sid in seed_ids]

        def key(r: Region) -> tuple[int, float, float]:
            min_hop = min(
                distance_caches[sid].get(r.region_id, _INF_HOP)
                for sid in seed_ids
            )
            rx, ry = centroid_by_id[r.region_id]
            min_euc = min(
                hypot(rx - sx, ry - sy) for sx, sy in seed_centroids
            )
            return (min_hop, min_euc, region_area(r))

        return max(candidates, key=key)

    def _record(region: Region, phase: PlacementPhase) -> None:
        seeds.append(SeedPlacement(region=region, phase=phase))
        distance_caches[region.region_id] = _bfs_all_distances(
            region.region_id, region_graph
        )

    # Phase A — Hub (global highest centrality)
    hub_territory_id: int | None = None
    if has_public:
        hub = pick_top_centrality(all_regions, region_graph)
        assert hub is not None  # all_regions checked above
        _record(hub, "hub")
        hub_territory_id = hub.part_id

    # Phase B — Territory coverage (spread-aware within each territory)
    covered_part_ids: set[int] = set()
    if hub_territory_id is not None:
        covered_part_ids.add(hub_territory_id)
    other_terrs = [
        t for t in territories if t.part_id not in covered_part_ids
    ]
    other_terrs.sort(key=_territory_area, reverse=True)
    coverage_budget = K - len(covered_part_ids)
    for t in other_terrs[:coverage_budget]:
        members = [
            r for r in regions_in_territory(t, region_graph)
            if r.region_id not in distance_caches
        ]
        forced = _pick_farthest(members)
        if forced is None:
            continue
        _record(forced, "coverage")
        covered_part_ids.add(t.part_id)

    # Phase C — FPS over covered territories
    fps_pool = [
        r for r in all_regions
        if r.part_id in covered_part_ids and r.region_id not in distance_caches
    ]
    while len(seeds) < K:
        if not fps_pool:
            raise ValueError(
                f"auto_place_seeds: K={K} exceeds available regions "
                f"({len(seeds)} placed). Check fixture sizing."
            )
        next_seed = _pick_farthest(fps_pool)
        assert next_seed is not None  # fps_pool non-empty
        _record(next_seed, "fps")
        fps_pool = [r for r in fps_pool if r.region_id != next_seed.region_id]

    return tuple(seeds)
