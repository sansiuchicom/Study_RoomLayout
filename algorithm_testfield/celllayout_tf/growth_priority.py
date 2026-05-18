"""Voronoi + anchor + outward-vector pre-computation (Phase 7 Round 4 v2 W6a).

For each room's seed, compute:
  - bounded Voronoi cell within its territory (multi-source BFS, hop distance)
  - anchor point (length-weighted centroid of internal edges, or territory
    centroid for single-seed cells)
  - outward vector = seed_centroid - anchor (in territory's local frame)
  - side priority — 4 sides ranked by outward vector projection

W6b (strip extension) and W6c (round-based growth) consume this as input.
"""

from __future__ import annotations

import random
from collections import defaultdict, deque
from dataclasses import dataclass
from math import degrees, hypot
from typing import Literal

import shapely.affinity
import shapely.geometry as sg
from shapely.ops import unary_union

from .region_graph import RegionGraph
from .regionize import Region
from .territory import Territory


Side = Literal["top", "right", "bottom", "left"]
_ALL_SIDES: tuple[Side, ...] = ("top", "right", "bottom", "left")

_AMBIGUOUS_EPS = 1e-6


@dataclass(frozen=True)
class SeedAnchor:
    """Pre-computed routing info for one seed.

    ``side_priority`` orders the 4 sides as
    ``(dominant_out, secondary_out, secondary_in, dominant_in)``.
    """

    seed_region_id: int
    room_idx: int
    anchor_point: tuple[float, float]      # local frame
    outward_vector: tuple[float, float]    # local frame
    side_priority: tuple[Side, Side, Side, Side]


# ---------- Voronoi (bounded, multi-source BFS on territory's region graph) ----------


def bounded_voronoi(
    territory: Territory,
    seed_region_ids: tuple[int, ...],
    region_graph: RegionGraph,
) -> dict[int, tuple[int, ...]]:
    """Multi-source BFS within a single territory.

    Returns ``{seed_id: tuple of region_ids assigned to that seed}``.
    Tie-break for equal-distance regions: smaller ``seed_id`` wins.
    """
    in_territory_ids: set[int] = {
        r.region_id for r in region_graph.regions if r.part_id == territory.part_id
    }
    for sid in seed_region_ids:
        if sid not in in_territory_ids:
            raise ValueError(
                f"seed region {sid} not in territory part_id={territory.part_id}"
            )

    # Single-source BFS from each seed within the territory.
    seed_distances: dict[int, dict[int, int]] = {}
    for sid in seed_region_ids:
        dists: dict[int, int] = {sid: 0}
        queue: deque[int] = deque([sid])
        while queue:
            node = queue.popleft()
            for nbr in region_graph.neighbors(node):
                if nbr not in in_territory_ids or nbr in dists:
                    continue
                dists[nbr] = dists[node] + 1
                queue.append(nbr)
        seed_distances[sid] = dists

    cells: dict[int, list[int]] = {sid: [] for sid in seed_region_ids}
    _INF = 10**9
    for rid in in_territory_ids:
        best = min(
            (seed_distances[sid].get(rid, _INF), sid) for sid in seed_region_ids
        )
        cells[best[1]].append(rid)

    return {sid: tuple(sorted(cells[sid])) for sid in seed_region_ids}


# ---------- Anchor & outward vector ----------


def _to_local_polygon(geom, theta: float):
    """Rotate ``geom`` to the theta-group's local frame (origin = global 0,0)."""
    if theta != 0.0:
        return shapely.affinity.rotate(geom, -degrees(theta), origin=(0, 0))
    return geom


def _region_to_local(region: Region, theta: float) -> sg.Polygon:
    poly = sg.Polygon(region.shape.exterior, [list(h) for h in region.shape.holes])
    return _to_local_polygon(poly, theta)


def _territory_polygon(territory: Territory) -> sg.base.BaseGeometry:
    polys = [
        sg.Polygon(p.exterior, [list(h) for h in p.holes])
        for p in territory.pieces
    ]
    return unary_union(polys)


def _line_components(geom) -> list[sg.LineString]:
    if geom.is_empty:
        return []
    if geom.geom_type == "LineString":
        return [geom] if geom.length > 1e-9 else []
    if geom.geom_type in ("MultiLineString", "GeometryCollection"):
        out: list[sg.LineString] = []
        for g in getattr(geom, "geoms", []):
            out.extend(_line_components(g))
        return out
    return []


def _territory_centroid_local(territory: Territory) -> tuple[float, float]:
    poly = _to_local_polygon(_territory_polygon(territory), territory.theta)
    c = poly.centroid
    return (c.x, c.y)


def compute_anchor(
    voronoi_cell: tuple[int, ...],
    other_cell_ids: set[int],
    region_graph: RegionGraph,
    region_local_polys: dict[int, sg.Polygon],
    territory_centroid: tuple[float, float],
) -> tuple[float, float]:
    """Length-weighted centroid of internal edges in local frame.

    Internal edges = region_graph edges from a region in ``voronoi_cell`` to
    a region in ``other_cell_ids`` (same territory, different Voronoi cell).
    Edge length = shared boundary length in local frame.

    Returns ``territory_centroid`` when there are no internal edges (e.g.,
    single-seed territory, or a disconnected cell).
    """
    weighted_x = 0.0
    weighted_y = 0.0
    total_length = 0.0

    seen: set[tuple[int, int]] = set()
    for ra in voronoi_cell:
        poly_a = region_local_polys[ra]
        for rb in region_graph.neighbors(ra):
            if rb not in other_cell_ids:
                continue
            key = (min(ra, rb), max(ra, rb))
            if key in seen:
                continue
            seen.add(key)
            poly_b = region_local_polys[rb]
            shared = poly_a.intersection(poly_b)
            for seg in _line_components(shared):
                length = seg.length
                if length < 1e-9:
                    continue
                c = seg.centroid
                weighted_x += c.x * length
                weighted_y += c.y * length
                total_length += length

    if total_length < 1e-9:
        return territory_centroid
    return (weighted_x / total_length, weighted_y / total_length)


def _seed_centroid_local(
    seed_region_id: int,
    region_local_polys: dict[int, sg.Polygon],
) -> tuple[float, float]:
    c = region_local_polys[seed_region_id].centroid
    return (c.x, c.y)


# ---------- Side priority from outward vector ----------


def _opposite(side: Side) -> Side:
    return {"top": "bottom", "bottom": "top", "left": "right", "right": "left"}[side]


def _side_priority_from_outward(
    outward: tuple[float, float],
    seed_id: int,
) -> tuple[Side, Side, Side, Side]:
    """Classify 4 sides by outward vector axis projection.

    Ambiguous case (|outward| < eps): deterministic hash-based perturbation
    seeded by ``seed_id`` so each seed gets a stable priority without ties.
    """
    dx, dy = outward
    if hypot(dx, dy) < _AMBIGUOUS_EPS:
        rng = random.Random(seed_id)
        dx = rng.uniform(-1.0, 1.0)
        dy = rng.uniform(-1.0, 1.0)

    if abs(dx) >= abs(dy):
        dom_out: Side = "right" if dx > 0 else "left"
        sec_out: Side = "top" if dy > 0 else "bottom"
    else:
        dom_out = "top" if dy > 0 else "bottom"
        sec_out = "right" if dx > 0 else "left"

    sec_in = _opposite(sec_out)
    dom_in = _opposite(dom_out)
    return (dom_out, sec_out, sec_in, dom_in)


# ---------- High-level: build all SeedAnchors for a fixture ----------


def compute_seed_anchors(
    seeds_by_room: dict[int, int],
    region_graph: RegionGraph,
    territories: tuple[Territory, ...],
    regions_by_id: dict[int, Region],
) -> dict[int, SeedAnchor]:
    """Build ``{room_idx: SeedAnchor}`` for all rooms in a fixture.

    ``seeds_by_room`` is the room_idx → seed_region_id map produced by the
    fixture's manual seeds or by ``auto_place_seeds``.
    """
    # Group seeds by territory (part_id).
    seeds_by_territory: dict[int, list[int]] = defaultdict(list)
    for room_idx, sid in seeds_by_room.items():
        seeds_by_territory[regions_by_id[sid].part_id].append(sid)

    seed_to_room: dict[int, int] = {sid: ridx for ridx, sid in seeds_by_room.items()}
    territory_by_part: dict[int, Territory] = {t.part_id: t for t in territories}

    # Pre-rotate region polygons per territory theta. A region's theta matches
    # its territory's theta (inherited in Phase 5).
    region_local_polys: dict[int, sg.Polygon] = {}
    for r in region_graph.regions:
        region_local_polys[r.region_id] = _region_to_local(r, r.theta)

    anchors: dict[int, SeedAnchor] = {}
    for part_id, seed_ids in seeds_by_territory.items():
        territory = territory_by_part.get(part_id)
        if territory is None:
            # Surviving-territory check: should not happen if seeds came from
            # an auto-place run that respected surviving territories.
            raise ValueError(
                f"seed group references part_id={part_id} with no territory"
            )
        cells = bounded_voronoi(territory, tuple(seed_ids), region_graph)
        all_cell_ids = {rid for cell in cells.values() for rid in cell}
        terr_centroid = _territory_centroid_local(territory)

        for sid in seed_ids:
            cell = cells[sid]
            other_cell_ids = all_cell_ids - set(cell)
            anchor = compute_anchor(
                cell, other_cell_ids,
                region_graph, region_local_polys,
                terr_centroid,
            )
            seed_centroid = _seed_centroid_local(sid, region_local_polys)
            outward = (seed_centroid[0] - anchor[0], seed_centroid[1] - anchor[1])
            priority = _side_priority_from_outward(outward, sid)

            room_idx = seed_to_room[sid]
            anchors[room_idx] = SeedAnchor(
                seed_region_id=sid,
                room_idx=room_idx,
                anchor_point=anchor,
                outward_vector=outward,
                side_priority=priority,
            )

    return anchors


# ---------- Strip extension (region-level) ----------


def _local_bbox(union: sg.base.BaseGeometry) -> tuple[float, float, float, float]:
    return union.bounds  # (minx, miny, maxx, maxy)


def find_strip(
    room_region_ids: tuple[int, ...],
    side: Side,
    region_to_room: dict[int, int],
    region_local_polys: dict[int, sg.Polygon],
    region_ids_by_part: dict[int, list[int]],
    territory_local_poly: sg.base.BaseGeometry,
    part_id: int,
    rect_tol: float = 1e-6,
) -> tuple[int, ...] | None:
    """Find regions on ``side`` of the room that form a clean rect extension.

    Hard constraints:
      1. Strip + room union is bbox-equivalent (rect)
      2. New bbox is covered by territory_local_poly (no overhang, no hole)
      3. Strip regions are unassigned and in same territory

    Returns the strip region_ids (tuple, sorted) or ``None`` if no valid
    strip exists on this side.
    """
    if not room_region_ids:
        return None

    room_polys = [region_local_polys[rid] for rid in room_region_ids]
    room_union = unary_union(room_polys)
    if room_union.is_empty or room_union.geom_type != "Polygon":
        return None
    x_L, y_B, x_R, y_T = _local_bbox(room_union)

    eps = 1e-6
    strip_candidates: list[int] = []
    for rid in region_ids_by_part.get(part_id, ()):
        if rid in region_to_room or rid in room_region_ids:
            continue
        cxL, cyB, cxR, cyT = region_local_polys[rid].bounds
        if side == "top":
            adjacent = abs(cyB - y_T) < eps
            in_span = cxL >= x_L - eps and cxR <= x_R + eps
        elif side == "bottom":
            adjacent = abs(cyT - y_B) < eps
            in_span = cxL >= x_L - eps and cxR <= x_R + eps
        elif side == "right":
            adjacent = abs(cxL - x_R) < eps
            in_span = cyB >= y_B - eps and cyT <= y_T + eps
        else:  # "left"
            adjacent = abs(cxR - x_L) < eps
            in_span = cyB >= y_B - eps and cyT <= y_T + eps
        if adjacent and in_span:
            strip_candidates.append(rid)

    if not strip_candidates:
        return None

    strip_polys = [region_local_polys[rid] for rid in strip_candidates]
    combined = unary_union(room_polys + strip_polys)
    if combined.is_empty or combined.geom_type != "Polygon":
        return None

    cxL, cyB, cxR, cyT = _local_bbox(combined)
    bbox_area = (cxR - cxL) * (cyT - cyB)
    if abs(bbox_area - combined.area) > rect_tol * max(combined.area, 1e-9):
        return None  # not a clean rect

    new_bbox = sg.box(cxL, cyB, cxR, cyT)
    if not territory_local_poly.covers(new_bbox):
        return None  # bbox escapes territory (overhang or hole)

    return tuple(sorted(strip_candidates))


def territory_local_polygon(territory: Territory) -> sg.base.BaseGeometry:
    """Territory polygon (possibly multi-piece) rotated to its local frame."""
    return _to_local_polygon(_territory_polygon(territory), territory.theta)


def region_ids_by_part(region_graph: RegionGraph) -> dict[int, list[int]]:
    """Index of region_ids grouped by part_id (= territory id)."""
    out: dict[int, list[int]] = defaultdict(list)
    for r in region_graph.regions:
        out[r.part_id].append(r.region_id)
    return dict(out)


def region_local_polys_by_id(
    region_graph: RegionGraph,
) -> dict[int, sg.Polygon]:
    """Map region_id → local-frame polygon (cached for repeated gate queries)."""
    return {r.region_id: _region_to_local(r, r.theta) for r in region_graph.regions}
