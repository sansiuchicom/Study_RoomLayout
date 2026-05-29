"""Shared seed-placement helpers — Phase 6 (Step 04 §4.5).

Plan reference: ``004_Step04_AlgorithmCore_Plan.md`` §4.5 + S04-D1.

Ported from Cell ``seed_placement.py`` (faithful — logic unchanged). Imports
swapped to ``room_layout.stages.*``; ``region_area`` uses ``to_shapely``
(identical to Cell's ``sg.Polygon(exterior, holes).area``). These centrality
/ BFS primitives are consumed by the Phase 7 cell-aware placement
(``growth_seed``) and the corridor router.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from room_layout.stages._helpers import to_shapely
from room_layout.stages.region_graph import RegionGraph
from room_layout.stages.regionize import Region

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
    return float(to_shapely(region.shape).area)


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
