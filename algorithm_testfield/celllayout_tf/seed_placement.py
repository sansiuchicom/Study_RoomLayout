"""Seed auto-placement helpers — Phase 7 Round 4.

W1 supplies the building blocks (centrality + territory mapping).
W2 will build ``auto_place_seeds`` on top.
"""

from __future__ import annotations

from typing import Iterable

import shapely.geometry as sg

from .region_graph import RegionGraph
from .regionize import Region
from .territory import Territory


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
