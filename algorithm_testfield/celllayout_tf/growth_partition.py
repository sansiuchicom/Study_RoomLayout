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

from math import hypot

from .atomize import atomize
from .dimensions import DimensionPolicy
from .region_graph import RegionGraph, build_region_graph
from .regionize import regionize
from .seed_placement import (
    SeedPlacement,
    auto_place_seeds,
    pick_top_centrality,
    region_area,
)
from .territory import (
    KIND_CURVED,
    Territory,
    collect_cross_theta_contact_coords,
    resolve_territories,
)


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


def vertex_cells_of_piece(
    piece,
    theta: float,
    extra_cut_xs: set[float] | tuple[float, ...] = (),
    extra_cut_ys: set[float] | tuple[float, ...] = (),
) -> list[sg.Polygon]:
    """Split piece into axis-aligned rect cells using reflex-vertex cuts.

    Cuts are axis-aligned LINES in the piece's local frame at:
      - each reflex vertex (exterior + hole) of the piece itself
      - each extra_cut_xs / extra_cut_ys coord (cross-piece contact
        projections, computed by ``collect_cross_theta_contact_coords``)

    Cells returned in GLOBAL frame (rotated back by +theta).
    For a piece with no cut coords (rect, curved without contacts): returns
    [piece] in global frame.
    """
    poly_global = _to_shapely(piece)
    poly_local = _rotate(poly_global, theta, sign=-1)
    reflex = reflex_vertices_local(piece, theta)

    x_cuts_set = {round(v[0], 6) for v in reflex}
    y_cuts_set = {round(v[1], 6) for v in reflex}
    x_cuts_set.update(round(c, 6) for c in extra_cut_xs)
    y_cuts_set.update(round(c, 6) for c in extra_cut_ys)

    if not x_cuts_set and not y_cuts_set:
        return [poly_global]

    x_cuts = sorted(x_cuts_set)
    y_cuts = sorted(y_cuts_set)

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
                    if g.geom_type == "Polygon" and g.area > 1e-3
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
                    if g.geom_type == "Polygon" and g.area > 1e-3
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


def _snap_to_region_edge(
    midpoint: float,
    axis: str,
    region_local_bboxes: dict[int, tuple[float, float, float, float]] | None,
    region_ids_in_cell: list[int],
    low_excl: float,
    high_excl: float,
) -> float:
    """Snap a midpoint cut value to the nearest frequent region edge.

    Returns ``midpoint`` unchanged when ``region_local_bboxes`` is None or
    no region edge falls strictly within ``(low_excl, high_excl)``.

    Selection: highest-frequency edge (boundary shared by most regions),
    tie-broken by closeness to midpoint.
    """
    if not region_local_bboxes:
        return midpoint
    from collections import Counter
    counter: Counter[float] = Counter()
    for rid in region_ids_in_cell:
        bbox = region_local_bboxes.get(rid)
        if bbox is None:
            continue
        cxL, cyB, cxR, cyT = bbox
        if axis == "x":
            edges = (cxL, cxR)
        else:
            edges = (cyB, cyT)
        for e in edges:
            if low_excl < e < high_excl:
                counter[round(e, 4)] += 1
    if not counter:
        return midpoint
    return max(
        counter.keys(),
        key=lambda c: (counter[c], -abs(c - midpoint)),
    )


def _guillotine_partition(
    cell_bbox: tuple[float, float, float, float],
    seeds_in_cell: list[tuple[int, sg.Point]],
    regions_in_cell: list[tuple[int, sg.Point]],
    region_local_bboxes: dict[int, tuple[float, float, float, float]] | None = None,
) -> dict[int, list[int]]:
    """Recursive aspect-minimizing guillotine partition of a rect cell.

    Each cut is a single straight axis-aligned line (in local frame). Cut
    position starts at the midpoint between adjacent seeds along the chosen
    axis, then SNAPS to the nearest frequent region-edge coord between those
    seeds (so the cut prefers landing on an actual region boundary rather
    than slicing through region interiors). Among all (axis, gap)
    candidates, picks the one minimizing the max aspect of the two resulting
    sub-rects.

    Returns ``{seed_region_id: list of region_ids}``.

    ``region_local_bboxes``: per-region (xmin, ymin, xmax, ymax) in local
    frame, used for snap. Pass ``None`` to disable snap (midpoint only).
    """
    if len(seeds_in_cell) == 1:
        seed_id = seeds_in_cell[0][0]
        return {seed_id: [r[0] for r in regions_in_cell]}

    x_L, y_B, x_R, y_T = cell_bbox
    cell_w = x_R - x_L
    cell_h = y_T - y_B

    candidates: list[tuple[float, str, float, list, list]] = []
    region_ids = [r[0] for r in regions_in_cell]

    # Vertical cuts (along x axis)
    seeds_x = sorted(seeds_in_cell, key=lambda s: (s[1].x, s[0]))
    for i in range(len(seeds_x) - 1):
        xl, xr = seeds_x[i][1].x, seeds_x[i + 1][1].x
        if xr - xl < 1e-9:
            continue
        midpoint = (xl + xr) / 2.0
        cut = _snap_to_region_edge(
            midpoint, "x", region_local_bboxes, region_ids, xl, xr,
        )
        if cut <= x_L + 1e-9 or cut >= x_R - 1e-9:
            continue
        left_w = cut - x_L
        right_w = x_R - cut
        left_aspect = max(left_w, cell_h) / min(left_w, cell_h)
        right_aspect = max(right_w, cell_h) / min(right_w, cell_h)
        score = max(left_aspect, right_aspect)
        candidates.append((score, "x", cut, seeds_x[: i + 1], seeds_x[i + 1 :]))

    # Horizontal cuts (along y axis)
    seeds_y = sorted(seeds_in_cell, key=lambda s: (s[1].y, s[0]))
    for i in range(len(seeds_y) - 1):
        yb, yt = seeds_y[i][1].y, seeds_y[i + 1][1].y
        if yt - yb < 1e-9:
            continue
        midpoint = (yb + yt) / 2.0
        cut = _snap_to_region_edge(
            midpoint, "y", region_local_bboxes, region_ids, yb, yt,
        )
        if cut <= y_B + 1e-9 or cut >= y_T - 1e-9:
            continue
        bot_h = cut - y_B
        top_h = y_T - cut
        bot_aspect = max(cell_w, bot_h) / min(cell_w, bot_h)
        top_aspect = max(cell_w, top_h) / min(cell_w, top_h)
        score = max(bot_aspect, top_aspect)
        candidates.append((score, "y", cut, seeds_y[: i + 1], seeds_y[i + 1 :]))

    if not candidates:
        # Degenerate: no separating cut — give all regions to smallest seed_id
        seed_id = min(s[0] for s in seeds_in_cell)
        return {seed_id: [r[0] for r in regions_in_cell]}

    # Min score; tie-break by axis (x before y) then cut value
    candidates.sort(key=lambda c: (c[0], c[1], c[2]))
    score, axis, cut, group_a, group_b = candidates[0]

    if axis == "x":
        regions_a = [(rid, p) for rid, p in regions_in_cell if p.x < cut]
        regions_b = [(rid, p) for rid, p in regions_in_cell if p.x >= cut]
        cell_a = (x_L, y_B, cut, y_T)
        cell_b = (cut, y_B, x_R, y_T)
    else:
        regions_a = [(rid, p) for rid, p in regions_in_cell if p.y < cut]
        regions_b = [(rid, p) for rid, p in regions_in_cell if p.y >= cut]
        cell_a = (x_L, y_B, x_R, cut)
        cell_b = (x_L, cut, x_R, y_T)

    out: dict[int, list[int]] = {}
    out.update(_guillotine_partition(cell_a, group_a, regions_a, region_local_bboxes))
    out.update(_guillotine_partition(cell_b, group_b, regions_b, region_local_bboxes))
    return out


def _rotate_point(point: sg.Point, theta: float, sign: int) -> sg.Point:
    if theta == 0.0:
        return point
    return shapely.affinity.rotate(point, sign * degrees(theta), origin=(0, 0))


# ---------- Cell-aware seed placement (W8) ----------


def _enumerate_cells_with_regions(
    shape,
    region_graph: RegionGraph,
    territories: tuple[Territory, ...],
    region_poly_by_id: dict[int, sg.Polygon],
) -> list[dict]:
    """Enumerate all vertex cells across all (territory, piece) pairs.

    Cells include cross-piece contact projections from
    ``collect_cross_theta_contact_coords`` so a piece next to another piece
    gets a cut at the neighbor's endpoint (e.g., case 20's right arm cut at
    where the vertical arm meets).

    Returns a list of dicts each with:
      polygon, area, regions (list of region_ids whose centroid lies in cell),
      territory, piece_idx.
    """
    contact_xs, contact_ys = collect_cross_theta_contact_coords(shape, territories)
    out: list[dict] = []
    for territory in territories:
        eff_key = round(
            0.0 if territory.kind == KIND_CURVED else territory.theta, 9,
        )
        ex = contact_xs.get(eff_key, set())
        ey = contact_ys.get(eff_key, set())
        for piece_idx, piece in enumerate(territory.pieces):
            piece_global = _to_shapely(piece)
            piece_region_ids = [
                r.region_id for r in region_graph.regions
                if r.part_id == territory.part_id
                and piece_global.covers(region_poly_by_id[r.region_id].centroid)
            ]
            if not piece_region_ids:
                continue
            cells = vertex_cells_of_piece(
                piece, territory.theta,
                extra_cut_xs=ex, extra_cut_ys=ey,
            )
            for cell in cells:
                cell_regions = [
                    rid for rid in piece_region_ids
                    if cell.covers(region_poly_by_id[rid].centroid)
                ]
                if cell_regions:
                    out.append({
                        "polygon": cell,
                        "area": cell.area,
                        "regions": cell_regions,
                        "territory": territory,
                        "piece_idx": piece_idx,
                    })
    return out


def auto_place_seeds_by_cells(
    shape,
    region_graph: RegionGraph,
    territories: tuple[Territory, ...],
    K: int,
    has_public: bool,
) -> tuple[SeedPlacement, ...]:
    """Cell-aware seed placement (Round 4 v2 W9 — load-balanced).

    Phase A — Hub: pick_top_centrality globally (if has_public).
    Phase B — Territory coverage: each surviving territory not yet covered
              by hub gets 1 seed in its BIGGEST cell. Sorted by territory
              total area DESC. Stops at K.
    Phase C — Load-balanced extras:
              while seeds < K:
                candidate_territories = those having non-hub cells with
                                        unused regions
                target_territory = argmax(area / seed_count) among candidates
                target_cell      = argmax(area / (seed_count + 1)) among
                                   target_territory's non-hub cells
                                   (post-placement load: small empty cells
                                   lose to bigger cells getting extras)
                place seed:
                  empty cell  → pick_top_centrality
                  has seeds   → Euclidean FPS within cell
              Fallback: when no candidate territories remain (e.g., hub has
              the only cell), place extras in the hub cell.

    Hub cell is excluded from Phase C unless all alternatives exhausted.
    """
    if K <= 0:
        raise ValueError(f"K must be >= 1, got {K}")
    if not region_graph.regions:
        raise ValueError("region_graph has no regions")

    regions_by_id = {r.region_id: r for r in region_graph.regions}
    region_poly_by_id = {
        r.region_id: _to_shapely(r.shape) for r in region_graph.regions
    }

    all_cells = _enumerate_cells_with_regions(
        shape, region_graph, territories, region_poly_by_id,
    )
    if not all_cells:
        raise ValueError("no vertex cells could be enumerated")

    cells_by_territory: dict[int, list[int]] = defaultdict(list)
    territory_areas: dict[int, float] = defaultdict(float)
    for idx, cell in enumerate(all_cells):
        pid = cell["territory"].part_id
        cells_by_territory[pid].append(idx)
        territory_areas[pid] += cell["area"]

    seeds: list[SeedPlacement] = []
    used: set[int] = set()
    hub_cell_idx: int | None = None
    cell_seed_count: dict[int, int] = {i: 0 for i in range(len(all_cells))}
    territory_seed_count: dict[int, int] = defaultdict(int)

    # Phase A — Hub
    if has_public:
        hub = pick_top_centrality(region_graph.regions, region_graph)
        assert hub is not None
        seeds.append(SeedPlacement(region=hub, phase="hub"))
        used.add(hub.region_id)
        for idx, cell in enumerate(all_cells):
            if hub.region_id in cell["regions"]:
                hub_cell_idx = idx
                cell_seed_count[idx] += 1
                territory_seed_count[cell["territory"].part_id] += 1
                break

    # Phase B — Territory coverage (1 seed per uncovered surviving territory)
    uncovered_pids = sorted(
        [pid for pid in cells_by_territory if territory_seed_count[pid] == 0],
        key=lambda pid: -territory_areas[pid],
    )
    for pid in uncovered_pids:
        if len(seeds) >= K:
            break
        territory_cells_idx = sorted(
            cells_by_territory[pid], key=lambda i: -all_cells[i]["area"],
        )
        for biggest_idx in territory_cells_idx:
            cell = all_cells[biggest_idx]
            candidates = [
                regions_by_id[rid] for rid in cell["regions"] if rid not in used
            ]
            picked = pick_top_centrality(candidates, region_graph)
            if picked is None:
                continue
            seeds.append(SeedPlacement(region=picked, phase="coverage"))
            used.add(picked.region_id)
            cell_seed_count[biggest_idx] += 1
            territory_seed_count[pid] += 1
            break  # next uncovered territory

    # Phase C — Load-balanced extras
    while len(seeds) < K:
        # Candidate territories: have at least one non-hub cell with unused regions
        candidate_pids: list[int] = []
        for pid, t_cells in cells_by_territory.items():
            non_hub = [i for i in t_cells if i != hub_cell_idx]
            if not non_hub:
                continue
            if any(
                any(rid not in used for rid in all_cells[i]["regions"])
                for i in non_hub
            ):
                candidate_pids.append(pid)

        target_cell_idx: int
        target_pid: int
        if candidate_pids:
            target_pid = max(
                candidate_pids,
                key=lambda pid: (
                    territory_areas[pid] / max(1, territory_seed_count[pid]),
                    territory_areas[pid],
                ),
            )
            target_cells = [
                i for i in cells_by_territory[target_pid]
                if i != hub_cell_idx
                and any(rid not in used for rid in all_cells[i]["regions"])
            ]
            target_cell_idx = max(
                target_cells,
                key=lambda i: (
                    all_cells[i]["area"] / (cell_seed_count[i] + 1),
                    all_cells[i]["area"],
                ),
            )
        else:
            # Fallback: hub cell extras
            if hub_cell_idx is None or not any(
                rid not in used for rid in all_cells[hub_cell_idx]["regions"]
            ):
                break
            target_cell_idx = hub_cell_idx
            target_pid = all_cells[hub_cell_idx]["territory"].part_id

        cell = all_cells[target_cell_idx]
        candidate_regions = [
            regions_by_id[rid] for rid in cell["regions"] if rid not in used
        ]
        if not candidate_regions:
            break

        existing_in_cell = [
            seed.region for seed in seeds
            if seed.region.region_id in cell["regions"]
        ]
        if not existing_in_cell:
            picked = pick_top_centrality(candidate_regions, region_graph)
            phase_label = "coverage"
        else:
            existing_centroids = [
                region_poly_by_id[s.region_id].centroid for s in existing_in_cell
            ]
            def _min_dist(r):
                c = region_poly_by_id[r.region_id].centroid
                return min(
                    hypot(c.x - ec.x, c.y - ec.y) for ec in existing_centroids
                )
            picked = max(
                candidate_regions,
                key=lambda r: (_min_dist(r), region_area(r), -r.region_id),
            )
            phase_label = "fps"
        if picked is None:
            break
        seeds.append(SeedPlacement(region=picked, phase=phase_label))
        used.add(picked.region_id)
        cell_seed_count[target_cell_idx] += 1
        territory_seed_count[target_pid] += 1

    return tuple(seeds)


# ---------- Post-processing: 3-stage unassigned absorption (W10) ----------


def _local_bbox_aspect(
    region_ids,
    regions_by_id: dict,
    theta: float,
) -> float | None:
    """bbox aspect (max/min) of regions' union in local frame; None if degenerate."""
    polys = []
    for rid in region_ids:
        r = regions_by_id[rid]
        p = sg.Polygon(r.shape.exterior, [list(h) for h in r.shape.holes])
        if theta != 0.0:
            p = shapely.affinity.rotate(p, -degrees(theta), origin=(0, 0))
        polys.append(p)
    union = shapely.ops.unary_union(polys)
    if union.is_empty:
        return None
    minx, miny, maxx, maxy = union.bounds
    w = maxx - minx
    h = maxy - miny
    if w < 1e-9 or h < 1e-9:
        return None
    return max(w, h) / min(w, h)


def _absorb_remaining(
    *,
    shape,
    rg,
    territories,
    room_regions: dict[int, list[int]],
    region_to_room: dict[int, int],
    regions_by_id: dict,
    region_poly_by_id: dict,
    neighbors_map: dict[int, set[int]],
    hub_room_idx: int | None,
) -> None:
    """Mutates ``room_regions``/``region_to_room`` in place. 3 stages:

    Stage 1 — Single-seed territory bulk absorb:
      For each territory whose room_count == 1, all unassigned regions in
      that territory go to that single room (shape unrestricted).

    Stage 2 — Vertex-cell-level absorption (one pass, biggest cells first):
      For each unassigned cell:
        1) hub adjacent → absorb to hub (any shape)
        2) else: prefer adjacent rooms that stay rect after absorbing the
           whole cell; among rect-keepers, pick aspect-closest-to-1.
        3) else: skip (defer to Stage 3).

    Stage 3 — Region-level absorption (one pass, biggest regions first):
      For each still-unassigned region:
        - exactly 1 adjacent room → absorb (any shape)
        - 2+ adjacent rooms → prefer rect-keepers, aspect-closest-to-1
        - no rect-keeper among multi-adjacent → skip (stays unassigned)
    """
    from .shape_gate import _reflex_of_union

    K = len(room_regions)

    # ----- Stage 1 -----
    territory_room_count: dict[int, int] = defaultdict(int)
    room_per_territory: dict[int, int] = {}
    for room_idx, rids in room_regions.items():
        if not rids:
            continue
        part_id = regions_by_id[rids[0]].part_id
        territory_room_count[part_id] += 1
        # When >1 room shares a part_id, this overwrites — but we only use it for single-seed territories.
        room_per_territory[part_id] = room_idx
    single_seed_part_ids = {
        pid for pid, c in territory_room_count.items() if c == 1
    }

    for rid in list(regions_by_id.keys()):
        if rid in region_to_room:
            continue
        part_id = regions_by_id[rid].part_id
        if part_id not in single_seed_part_ids:
            continue
        target = room_per_territory[part_id]
        room_regions[target].append(rid)
        region_to_room[rid] = target

    # ----- Stage 2 -----
    all_cells = _enumerate_cells_with_regions(
        shape, rg, territories, region_poly_by_id,
    )
    # Cells with all regions unassigned (= no seed inside)
    cells_unassigned = [
        (idx, cell) for idx, cell in enumerate(all_cells)
        if all(rid not in region_to_room for rid in cell["regions"])
    ]
    # Biggest first
    cells_unassigned.sort(key=lambda x: -x[1]["area"])

    for cell_idx, cell in cells_unassigned:
        cell_unassigned = [
            rid for rid in cell["regions"] if rid not in region_to_room
        ]
        if not cell_unassigned:
            continue

        adj_rooms: set[int] = set()
        for rid in cell_unassigned:
            for nbr in neighbors_map.get(rid, ()):
                if nbr in region_to_room:
                    adj_rooms.add(region_to_room[nbr])
        if not adj_rooms:
            continue

        chosen: int | None = None
        if hub_room_idx is not None and hub_room_idx in adj_rooms:
            chosen = hub_room_idx
        else:
            rect_keepers: list[tuple[int, float]] = []
            for room_idx in adj_rooms:
                room_rids = room_regions[room_idx]
                if not room_rids:
                    continue
                theta = regions_by_id[room_rids[0]].theta
                combined_ids = tuple(room_rids) + tuple(cell_unassigned)
                refl = _reflex_of_union(combined_ids, regions_by_id, theta)
                if refl != 0:
                    continue
                aspect = _local_bbox_aspect(combined_ids, regions_by_id, theta)
                if aspect is None:
                    continue
                rect_keepers.append((room_idx, aspect))
            if rect_keepers:
                rect_keepers.sort(key=lambda x: (abs(x[1] - 1.0), x[0]))
                chosen = rect_keepers[0][0]

        if chosen is None:
            continue
        for rid in cell_unassigned:
            room_regions[chosen].append(rid)
            region_to_room[rid] = chosen

    # ----- Stage 3 -----
    unassigned_regions = sorted(
        [
            r for r in regions_by_id.values()
            if r.region_id not in region_to_room
        ],
        key=lambda r: -region_poly_by_id[r.region_id].area,
    )
    for region in unassigned_regions:
        rid = region.region_id
        if rid in region_to_room:
            continue
        adj_rooms = set()
        for nbr in neighbors_map.get(rid, ()):
            if nbr in region_to_room:
                adj_rooms.add(region_to_room[nbr])
        if not adj_rooms:
            continue

        chosen = None
        if len(adj_rooms) == 1:
            chosen = next(iter(adj_rooms))
        else:
            rect_keepers = []
            for room_idx in adj_rooms:
                room_rids = room_regions[room_idx]
                if not room_rids:
                    continue
                theta = regions_by_id[room_rids[0]].theta
                combined_ids = tuple(room_rids) + (rid,)
                refl = _reflex_of_union(combined_ids, regions_by_id, theta)
                if refl != 0:
                    continue
                aspect = _local_bbox_aspect(combined_ids, regions_by_id, theta)
                if aspect is None:
                    continue
                rect_keepers.append((room_idx, aspect))
            if rect_keepers:
                rect_keepers.sort(key=lambda x: (abs(x[1] - 1.0), x[0]))
                chosen = rect_keepers[0][0]

        if chosen is None:
            continue
        room_regions[chosen].append(rid)
        region_to_room[rid] = chosen


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

    # --- Seed determination ---
    K = fixture.K
    seeds_by_room: dict[int, int] = {}
    if fixture.auto_seed:
        has_public = fixture.hub_room_index is not None
        # Cell-aware seed placement: hub via global centrality, remaining
        # seeds allocated to vertex cells (biggest first; hub cell excluded
        # from extras).
        placements = auto_place_seeds_by_cells(
            shape, rg, territories, K=K, has_public=has_public,
        )
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

    # Pre-compute cross-piece contact projections (used by every piece's
    # vertex_cells_of_piece call) — gives each piece extra cut coords at
    # points where another piece's boundary endpoint lands on its edge.
    contact_xs_map, contact_ys_map = collect_cross_theta_contact_coords(
        shape, territories,
    )

    for territory in territories:
        # Regions in this territory
        terr_regions = [r for r in regions if r.part_id == territory.part_id]
        terr_seed_region_ids = [
            sid for sid in seeds_by_room.values()
            if regions_by_id[sid].part_id == territory.part_id
        ]
        eff_key = round(
            0.0 if territory.kind == KIND_CURVED else territory.theta, 9,
        )
        ex = contact_xs_map.get(eff_key, set())
        ey = contact_ys_map.get(eff_key, set())

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

            # Vertex cells (in global frame) — include cross-piece contact
            # projections so a piece adjacent to another piece gets extra
            # cuts at the neighbor's boundary endpoints.
            cells = vertex_cells_of_piece(
                piece, territory.theta,
                extra_cut_xs=ex, extra_cut_ys=ey,
            )

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
                    # 2+ seeds — aspect-minimizing guillotine partition with
                    # snap-to-region-edge (W7b).
                    # Work in local frame so cell is axis-aligned rect.
                    cell_global = cells[cell_idx]
                    cell_local = _rotate(cell_global, territory.theta, sign=-1)
                    cell_bbox_local = cell_local.bounds
                    seeds_local = [
                        (sid, _rotate_point(
                            region_poly_by_id[sid].centroid,
                            territory.theta, sign=-1,
                        ))
                        for sid in cell_seeds
                    ]
                    regions_local = [
                        (rid, _rotate_point(
                            region_poly_by_id[rid].centroid,
                            territory.theta, sign=-1,
                        ))
                        for rid in cell_regions
                    ]
                    region_local_bboxes = {
                        rid: _rotate(
                            region_poly_by_id[rid], territory.theta, sign=-1,
                        ).bounds
                        for rid in cell_regions
                    }
                    assignment = _guillotine_partition(
                        cell_bbox_local, seeds_local, regions_local,
                        region_local_bboxes,
                    )
                    for seed_id, region_ids in assignment.items():
                        room_idx = seed_to_room[seed_id]
                        for rid in region_ids:
                            if rid not in region_to_room:
                                room_regions[room_idx].append(rid)
                                region_to_room[rid] = room_idx

    # --- Post-processing: 3-stage absorption (W10) ---
    _absorb_remaining(
        shape=shape,
        rg=rg,
        territories=territories,
        room_regions=room_regions,
        region_to_room=region_to_room,
        regions_by_id=regions_by_id,
        region_poly_by_id=region_poly_by_id,
        neighbors_map=neighbors_map,
        hub_room_idx=fixture.hub_room_index,
    )

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
