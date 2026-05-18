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


# ---------- Main entry: region_priority_growth ----------


def _aspect_gate_ok(
    room_region_ids: list[int],
    strip_ids: tuple[int, ...],
    region_poly_by_id: dict[int, sg.Polygon],
    aspect_range: tuple[float, float] | None,
) -> bool:
    """bbox aspect (max/min) of combined room ∪ strip within role range."""
    if aspect_range is None:
        return True
    a_min, a_max = aspect_range
    polys = (
        [region_poly_by_id[rid] for rid in room_region_ids]
        + [region_poly_by_id[rid] for rid in strip_ids]
    )
    union = unary_union(polys)
    if union.is_empty:
        return False
    xmin, ymin, xmax, ymax = union.bounds
    w = xmax - xmin
    h = ymax - ymin
    if w < 1e-9 or h < 1e-9:
        return False
    aspect = max(w / h, h / w)
    return a_min <= aspect <= a_max


def _hub_gate_ok(
    room_idx: int,
    strip_ids: tuple[int, ...],
    room_regions: dict[int, list[int]],
    region_to_room: dict[int, int],
    hub_idx: int,
    neighbors_map: dict[int, set[int]],
) -> bool:
    """After absorbing strip, the room-supernode graph keeps every previously
    hub-connected room still hub-connected (D011)."""
    from .room_growth import _rooms_connected_to_hub
    before = _rooms_connected_to_hub(
        room_regions, hub_idx, region_to_room, neighbors_map,
    )
    sim_region_to_room = dict(region_to_room)
    sim_room_regions = {i: list(rs) for i, rs in room_regions.items()}
    for cell in strip_ids:
        sim_region_to_room[cell] = room_idx
        sim_room_regions[room_idx].append(cell)
    after = _rooms_connected_to_hub(
        sim_room_regions, hub_idx, sim_region_to_room, neighbors_map,
    )
    return before.issubset(after)


def _pick_winner(
    claimants: list[int],
    hub_idx: int | None,
    current_areas: dict[int, float],
) -> int:
    """Hub wins. Else smallest current area (deterministic tie: room_idx ASC)."""
    if hub_idx is not None and hub_idx in claimants:
        return hub_idx
    return min(claimants, key=lambda i: (current_areas[i], i))


def _run_round(
    ordering: list[int],
    room_regions: dict[int, list[int]],
    region_to_room: dict[int, int],
    anchors: dict[int, SeedAnchor],
    region_local_polys: dict[int, sg.Polygon],
    ids_by_part: dict[int, list[int]],
    terr_polys: dict[int, sg.base.BaseGeometry],
    regions_by_id: dict[int, Region],
    region_poly_by_id: dict[int, sg.Polygon],
    region_area_by_id: dict[int, float],
    aspect_ranges: list[tuple[float, float] | None],
    hub_idx: int | None,
    neighbors_map: dict[int, set[int]],
    K: int,
) -> set[int]:
    """One round of priority growth + conflict resolution.

    Returns set of room_idxs that committed (absorbed ≥1 strip) this round.
    Within the round, losers of cell conflicts retry their next priority side.
    """
    committed: set[int] = set()
    tried_sides: dict[int, set[Side]] = defaultdict(set)

    while True:
        # Phase 1: each non-committed room proposes its next valid strip
        proposals: dict[int, tuple[tuple[int, ...], Side]] = {}
        for room_idx in ordering:
            if room_idx in committed:
                continue
            anchor = anchors[room_idx]
            for side in anchor.side_priority:
                if side in tried_sides[room_idx]:
                    continue
                part_id = regions_by_id[room_regions[room_idx][0]].part_id
                strip = find_strip(
                    tuple(room_regions[room_idx]),
                    side,
                    region_to_room,
                    region_local_polys,
                    ids_by_part,
                    terr_polys[part_id],
                    part_id,
                )
                if strip is None:
                    tried_sides[room_idx].add(side)
                    continue
                if not _aspect_gate_ok(
                    room_regions[room_idx], strip,
                    region_poly_by_id, aspect_ranges[room_idx],
                ):
                    tried_sides[room_idx].add(side)
                    continue
                if hub_idx is not None and not _hub_gate_ok(
                    room_idx, strip, room_regions, region_to_room,
                    hub_idx, neighbors_map,
                ):
                    tried_sides[room_idx].add(side)
                    continue
                proposals[room_idx] = (strip, side)
                break  # this room's proposal for this iteration

        if not proposals:
            break

        # Phase 2: collect cell claimants
        cell_claimants: dict[int, list[int]] = defaultdict(list)
        for room_idx, (strip, _) in proposals.items():
            for cell in strip:
                cell_claimants[cell].append(room_idx)

        # Phase 3: determine winners (must win ALL cells in their strip)
        current_areas = {
            i: sum(region_area_by_id[rid] for rid in room_regions[i])
            for i in range(K)
        }
        winners: dict[int, tuple[tuple[int, ...], Side]] = {}
        for room_idx, (strip, side) in proposals.items():
            wins_all = True
            for cell in strip:
                claimants = cell_claimants[cell]
                if len(claimants) == 1:
                    continue
                if _pick_winner(claimants, hub_idx, current_areas) != room_idx:
                    wins_all = False
                    break
            if wins_all:
                winners[room_idx] = (strip, side)

        # Phase 4: apply winners; losers mark their tried side and retry
        for room_idx, (strip, side) in proposals.items():
            if room_idx in winners:
                for cell in strip:
                    region_to_room[cell] = room_idx
                    room_regions[room_idx].append(cell)
                committed.add(room_idx)
                tried_sides[room_idx].add(side)
            else:
                tried_sides[room_idx].add(side)

    return committed


def region_priority_growth(
    shape,                  # ShapeInput
    fixture,                # LayoutFixture
    *,
    policy=None,
):
    """Round-based priority growth — Phase 7 Round 4 v2 main entry.

    Each round: rooms (ordered by current area ASC for fairness) propose
    rect-preserving strip extensions using their pre-computed side priority.
    Conflicts resolved by hub > smallest current area. Losers retry the next
    priority side within the same round.

    Stops when no room commits any strip in a full round.
    """
    from .atomize import atomize
    from .regionize import regionize
    from .region_graph import build_region_graph
    from .seed_placement import auto_place_seeds
    from .territory import resolve_territories
    from .room_growth import GrownRoom, GrowthResult

    atoms = atomize(shape, policy)
    regions = regionize(shape, atoms=atoms, policy=policy)
    rg = build_region_graph(shape, atoms=atoms, regions=regions, policy=policy)
    territories = resolve_territories(shape)
    regions_by_id = {r.region_id: r for r in regions}

    # ---- Seed determination ----
    K = fixture.K
    seeds_by_room: dict[int, int] = {}
    if fixture.auto_seed:
        has_public = fixture.hub_room_index is not None
        placements = auto_place_seeds(
            rg, territories, K=K, has_public=has_public,
        )
        if has_public:
            hub_room_idx = fixture.hub_room_index
            seeds_by_room[hub_room_idx] = placements[0].region.region_id
            si = 1
            for room_idx in range(K):
                if room_idx == hub_room_idx:
                    continue
                seeds_by_room[room_idx] = placements[si].region.region_id
                si += 1
        else:
            for room_idx in range(K):
                seeds_by_room[room_idx] = placements[room_idx].region.region_id
    else:
        from .room_growth import _to_shapely as _rg_to_shapely
        region_poly_by_id = {
            r.region_id: _rg_to_shapely(r.shape) for r in regions
        }
        for room_idx, spec in enumerate(fixture.rooms):
            pt = sg.Point(*spec.seed_position)
            found = None
            for r in sorted(regions, key=lambda r: r.region_id):
                if region_poly_by_id[r.region_id].covers(pt):
                    found = r.region_id
                    break
            if found is None:
                raise ValueError(
                    f"case {fixture.case_index} ({fixture.case_name}): "
                    f"seed {spec.name} at {spec.seed_position} not in any region"
                )
            if found in seeds_by_room.values():
                claimed_by = next(
                    i for i, v in seeds_by_room.items() if v == found
                )
                raise ValueError(
                    f"case {fixture.case_index}: seed {spec.name} resolves to "
                    f"region {found} already claimed by "
                    f"{fixture.rooms[claimed_by].name}"
                )
            seeds_by_room[room_idx] = found

    # ---- Pre-compute caches ----
    anchors = compute_seed_anchors(seeds_by_room, rg, territories, regions_by_id)
    region_local_polys = region_local_polys_by_id(rg)
    ids_by_part = region_ids_by_part(rg)
    terr_polys = {t.part_id: territory_local_polygon(t) for t in territories}

    from .room_growth import _to_shapely as _rg_to_shapely
    region_poly_by_id = {
        r.region_id: _rg_to_shapely(r.shape) for r in regions
    }
    region_area_by_id = {rid: p.area for rid, p in region_poly_by_id.items()}

    neighbors_map: dict[int, set[int]] = defaultdict(set)
    for e in rg.edges:
        neighbors_map[e.region_a].add(e.region_b)
        neighbors_map[e.region_b].add(e.region_a)

    aspect_ranges = [fixture.resolved_aspect_range(r) for r in fixture.rooms]
    hub_idx = fixture.hub_room_index

    # ---- Initialize room state ----
    room_regions: dict[int, list[int]] = {
        i: [seeds_by_room[i]] for i in range(K)
    }
    region_to_room: dict[int, int] = {
        sid: i for i, sid in seeds_by_room.items()
    }

    # ---- Main round loop ----
    iterations_log: list[dict] = []
    round_count = 0
    while True:
        round_count += 1
        current_areas = {
            i: sum(region_area_by_id[rid] for rid in room_regions[i])
            for i in range(K)
        }
        ordering = sorted(range(K), key=lambda i: (current_areas[i], i))
        committed = _run_round(
            ordering, room_regions, region_to_room,
            anchors, region_local_polys, ids_by_part, terr_polys,
            regions_by_id, region_poly_by_id, region_area_by_id,
            aspect_ranges, hub_idx, neighbors_map, K,
        )
        if not committed:
            round_count -= 1  # last round had no commits
            break
        iterations_log.append({
            "round": round_count,
            "committed_rooms": sorted(committed),
        })

    # ---- Build result ----
    current_areas = {
        i: sum(region_area_by_id[rid] for rid in room_regions[i])
        for i in range(K)
    }
    min_areas = [fixture.resolved_min_area(r) for r in fixture.rooms]
    grown_rooms = tuple(
        GrownRoom(
            name=spec.name,
            role=spec.role,
            region_ids=tuple(room_regions[i]),
            area_m2=current_areas[i],
        )
        for i, spec in enumerate(fixture.rooms)
    )
    unassigned = tuple(sorted(
        rid for rid in region_poly_by_id if rid not in region_to_room
    ))
    diagnostics = {
        "iterations": iterations_log,
        "hub_room_index": hub_idx,
        "total_rounds": round_count,
        "below_min_area": tuple(
            i for i in range(K) if current_areas[i] < min_areas[i]
        ),
    }
    return GrowthResult(
        fixture=fixture,
        rooms=grown_rooms,
        unassigned_region_ids=unassigned,
        diagnostics=diagnostics,
    )
