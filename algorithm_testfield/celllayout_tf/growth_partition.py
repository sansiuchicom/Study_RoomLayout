"""Top-down partition growth (Phase 7 Round 4 v2 W7) — replaces growth
algorithms with reflex-vertex-based piece decomposition.

Algorithm:
  1. Determine seeds (auto_place_seeds or fixture-manual).
  2. For each surviving territory piece:
       a. Rotate piece polygon to its theta-local frame.
       b. Find reflex vertices (exterior CCW + hole CW boundaries).
       c. Generate axis-aligned cut lines (horizontal y=y_v + vertical x=x_v)
          from each reflex vertex.
       d. Split piece by these cuts → "vertex cells" (max axis-aligned rects).
  3. Map regions and seeds to cells (point-in-polygon, local frame).
  4. For each cell:
       - 0 seeds: cell stays unassigned (corridor candidate)
       - 1 seed: cell wholly becomes that room
       - 2+ seeds: W7b will use guillotine partition; W7a uses BFS-Voronoi
                   among same-cell regions as a temporary fallback.

Curved pieces: no reflex (smooth curve) → 1 cell = whole piece.
"""

from __future__ import annotations

from collections import defaultdict, deque
from math import degrees

import shapely.affinity
import shapely.geometry as sg
import shapely.geometry.polygon
import shapely.ops

from .atomize import atomize
from .dimensions import DimensionPolicy
from .region_graph import build_region_graph
from .regionize import regionize
from .seed_placement import auto_place_seeds
from .territory import Territory, resolve_territories


def _to_shapely(part) -> sg.Polygon:
    return sg.Polygon(part.exterior, [list(h) for h in part.holes])


def _rotate(geom, theta: float, sign: int = -1):
    if theta == 0.0:
        return geom
    return shapely.affinity.rotate(geom, sign * degrees(theta), origin=(0, 0))


def reflex_vertices_local(piece, theta: float) -> list[tuple[float, float]]:
    """Reflex vertices of a piece in its theta-local frame.

    Includes:
      - exterior CCW reflex (cross product < 0)
      - all hole boundary vertices (each is concave from inside)
    """
    poly_global = _to_shapely(piece)
    poly_local = _rotate(poly_global, theta, sign=-1)
    poly_local = shapely.geometry.polygon.orient(poly_local, sign=1.0)

    reflex: list[tuple[float, float]] = []

    # Exterior reflex
    coords = list(poly_local.exterior.coords)
    if len(coords) >= 2 and coords[0] == coords[-1]:
        coords = coords[:-1]
    n = len(coords)
    for i in range(n):
        ax, ay = coords[(i - 1) % n]
        bx, by = coords[i]
        cx, cy = coords[(i + 1) % n]
        cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if cross < -1e-9:
            reflex.append((bx, by))

    # Holes — every hole vertex is concave from interior
    for hole in poly_local.interiors:
        hcoords = list(hole.coords)
        if len(hcoords) >= 2 and hcoords[0] == hcoords[-1]:
            hcoords = hcoords[:-1]
        reflex.extend(hcoords)

    return reflex


def vertex_cells_of_piece(piece, theta: float) -> list[sg.Polygon]:
    """Split piece into axis-aligned rect cells using reflex-vertex cuts.

    Cuts are axis-aligned LINES in the piece's local frame through each
    reflex vertex. Cells returned in GLOBAL frame (rotated back by +theta).

    For a piece with no reflex (rect, curved): returns [piece] in global frame.
    """
    poly_global = _to_shapely(piece)
    poly_local = _rotate(poly_global, theta, sign=-1)
    reflex = reflex_vertices_local(piece, theta)

    if not reflex:
        return [poly_global]

    # Unique cut coords
    x_cuts = sorted({round(v[0], 6) for v in reflex})
    y_cuts = sorted({round(v[1], 6) for v in reflex})

    # Bounds for cut line endpoints (extend well beyond piece)
    minx, miny, maxx, maxy = poly_local.bounds
    pad = max(maxx - minx, maxy - miny) * 10.0 + 100.0
    x_lo, x_hi = minx - pad, maxx + pad
    y_lo, y_hi = miny - pad, maxy + pad

    cells = [poly_local]
    for x_cut in x_cuts:
        new_cells = []
        cut_line = sg.LineString([(x_cut, y_lo), (x_cut, y_hi)])
        for cell in cells:
            try:
                result = shapely.ops.split(cell, cut_line)
                new_cells.extend(
                    g for g in result.geoms
                    if g.geom_type == "Polygon" and g.area > 1e-9
                )
            except Exception:
                new_cells.append(cell)
        cells = new_cells
    for y_cut in y_cuts:
        new_cells = []
        cut_line = sg.LineString([(x_lo, y_cut), (x_hi, y_cut)])
        for cell in cells:
            try:
                result = shapely.ops.split(cell, cut_line)
                new_cells.extend(
                    g for g in result.geoms
                    if g.geom_type == "Polygon" and g.area > 1e-9
                )
            except Exception:
                new_cells.append(cell)
        cells = new_cells

    # Rotate cells back to global frame
    return [_rotate(c, theta, sign=+1) for c in cells]


def _assign_to_cells(
    points: list[tuple[int, sg.Point]],
    cells: list[sg.Polygon],
) -> dict[int, list[int]]:
    """Assign points to cells (returns cell_idx → list of point keys).

    Uses ``covers`` so a point on a cell boundary still resolves
    deterministically to the first cell in list order.
    """
    out: dict[int, list[int]] = defaultdict(list)
    for key, pt in points:
        for cell_idx, cell in enumerate(cells):
            if cell.covers(pt):
                out[cell_idx].append(key)
                break
    return out


def _bfs_voronoi_within_regions(
    seed_region_ids: list[int],
    candidate_region_ids: list[int],
    neighbors_map: dict[int, set[int]],
) -> dict[int, list[int]]:
    """Multi-source BFS within the candidate region set, returning the cell
    assignment for each seed (tie-break: smallest seed_id wins).

    Used as a TEMPORARY fallback for W7a's multi-seed-in-cell case. W7b will
    replace this with seed-position-based guillotine cuts.
    """
    pool = set(candidate_region_ids)
    seed_set = set(seed_region_ids)
    pool |= seed_set

    seed_distances: dict[int, dict[int, int]] = {}
    for sid in seed_region_ids:
        dists = {sid: 0}
        queue = deque([sid])
        while queue:
            node = queue.popleft()
            for nbr in neighbors_map.get(node, ()):
                if nbr not in pool or nbr in dists:
                    continue
                dists[nbr] = dists[node] + 1
                queue.append(nbr)
        seed_distances[sid] = dists

    assignment: dict[int, list[int]] = defaultdict(list)
    _INF = 10**9
    for rid in pool:
        best = min(
            (seed_distances[sid].get(rid, _INF), sid)
            for sid in seed_region_ids
        )
        assignment[best[1]].append(rid)
    return dict(assignment)


def region_partition_growth(shape, fixture, *, policy: DimensionPolicy | None = None):
    """Top-down piece-based partition growth (Round 4 v2 W7a)."""
    from .room_growth import GrownRoom, GrowthResult

    atoms = atomize(shape, policy)
    regions = regionize(shape, atoms=atoms, policy=policy)
    rg = build_region_graph(shape, atoms=atoms, regions=regions, policy=policy)
    territories = resolve_territories(shape)
    regions_by_id = {r.region_id: r for r in regions}
    region_poly_by_id = {r.region_id: _to_shapely(r.shape) for r in regions}
    region_area_by_id = {rid: p.area for rid, p in region_poly_by_id.items()}

    neighbors_map: dict[int, set[int]] = defaultdict(set)
    for e in rg.edges:
        neighbors_map[e.region_a].add(e.region_b)
        neighbors_map[e.region_b].add(e.region_a)

    # --- Seed determination (same as growth_priority) ---
    K = fixture.K
    seeds_by_room: dict[int, int] = {}
    if fixture.auto_seed:
        has_public = fixture.hub_room_index is not None
        placements = auto_place_seeds(rg, territories, K=K, has_public=has_public)
        if has_public:
            hub_idx = fixture.hub_room_index
            seeds_by_room[hub_idx] = placements[0].region.region_id
            si = 1
            for room_idx in range(K):
                if room_idx == hub_idx:
                    continue
                seeds_by_room[room_idx] = placements[si].region.region_id
                si += 1
        else:
            for room_idx in range(K):
                seeds_by_room[room_idx] = placements[room_idx].region.region_id
    else:
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
            seeds_by_room[room_idx] = found

    seed_to_room = {sid: ridx for ridx, sid in seeds_by_room.items()}

    # --- Partition: per piece, per cell ---
    room_regions: dict[int, list[int]] = {i: [] for i in range(K)}
    region_to_room: dict[int, int] = {}

    for territory in territories:
        # Regions in this territory
        terr_regions = [r for r in regions if r.part_id == territory.part_id]
        terr_seed_region_ids = [
            sid for sid in seeds_by_room.values()
            if regions_by_id[sid].part_id == territory.part_id
        ]

        for piece_idx, piece in enumerate(territory.pieces):
            piece_global = _to_shapely(piece)

            # Map regions to this piece by centroid
            piece_region_ids: list[int] = []
            for r in terr_regions:
                rc = region_poly_by_id[r.region_id].centroid
                if piece_global.covers(rc):
                    piece_region_ids.append(r.region_id)

            if not piece_region_ids:
                continue

            piece_seeds = [
                sid for sid in terr_seed_region_ids
                if sid in piece_region_ids
            ]

            if not piece_seeds:
                # No seed in this piece — all its regions are unassigned
                continue

            # Vertex cells (in global frame)
            cells = vertex_cells_of_piece(piece, territory.theta)

            # Assign regions to cells by centroid
            region_to_cell = _assign_to_cells(
                [(rid, region_poly_by_id[rid].centroid) for rid in piece_region_ids],
                cells,
            )
            seed_to_cell = _assign_to_cells(
                [(sid, region_poly_by_id[sid].centroid) for sid in piece_seeds],
                cells,
            )

            # For each cell, allocate its regions to the room(s) of its seed(s)
            for cell_idx in range(len(cells)):
                cell_regions = region_to_cell.get(cell_idx, [])
                cell_seeds = seed_to_cell.get(cell_idx, [])
                if not cell_regions:
                    continue

                if len(cell_seeds) == 0:
                    # cell unassigned (corridor candidate)
                    continue
                elif len(cell_seeds) == 1:
                    # whole cell → that room
                    room_idx = seed_to_room[cell_seeds[0]]
                    for rid in cell_regions:
                        if rid not in region_to_room:
                            room_regions[room_idx].append(rid)
                            region_to_room[rid] = room_idx
                else:
                    # 2+ seeds — temporary BFS-Voronoi fallback (W7b will
                    # replace this with guillotine partition).
                    bfs_assignment = _bfs_voronoi_within_regions(
                        cell_seeds, cell_regions, neighbors_map,
                    )
                    for seed_id, region_ids in bfs_assignment.items():
                        room_idx = seed_to_room[seed_id]
                        for rid in region_ids:
                            if rid not in region_to_room:
                                room_regions[room_idx].append(rid)
                                region_to_room[rid] = room_idx

    # --- Build result ---
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
        "hub_room_index": fixture.hub_room_index,
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
