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

from collections import defaultdict

import shapely.geometry as sg
import shapely.ops

from math import hypot

from .atomize import atomize
from .dimensions import DimensionPolicy
from .geometry import rotate_radians as _rotate, to_shapely as _to_shapely
from .region_graph import RegionGraph, build_region_graph
from .regionize import regionize
from .seed_placement import (
    SeedPlacement,
    _bfs_all_distances,
    pick_top_centrality,
    region_area,
)
from .growth_cells import (
    _assign_to_cells,
    _guillotine_partition,
    _snap_to_region_edge,
    reflex_vertices_local,
    vertex_cells_of_piece,
)
from .territory import (
    KIND_CURVED,
    Territory,
    collect_cross_theta_contact_coords,
    resolve_territories,
)


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

    # Logical territory = (part_id, piece_idx) — disconnected pieces of the
    # same part treated separately so case 13's two cross arms are distinct.
    cells_by_piece: dict[tuple[int, int], list[int]] = defaultdict(list)
    piece_areas: dict[tuple[int, int], float] = defaultdict(float)
    for idx, cell in enumerate(all_cells):
        pkey = (cell["territory"].part_id, cell["piece_idx"])
        cells_by_piece[pkey].append(idx)
        piece_areas[pkey] += cell["area"]

    seeds: list[SeedPlacement] = []
    used: set[int] = set()
    hub_cell_idx: int | None = None
    cell_seed_count: dict[int, int] = {i: 0 for i in range(len(all_cells))}
    piece_seed_count: dict[tuple[int, int], int] = defaultdict(int)
    # Distance bookkeeping (W13): seeds are picked to maximize min-hop to
    # existing seeds, with Euclidean centroid distance as tie-break.
    seed_region_ids: list[int] = []
    bfs_cache: dict[int, dict[int, int]] = {}

    # Phase A — Hub
    if has_public:
        hub = pick_top_centrality(region_graph.regions, region_graph)
        assert hub is not None
        seeds.append(SeedPlacement(region=hub, phase="hub"))
        used.add(hub.region_id)
        seed_region_ids.append(hub.region_id)
        for idx, cell in enumerate(all_cells):
            if hub.region_id in cell["regions"]:
                hub_cell_idx = idx
                cell_seed_count[idx] += 1
                piece_seed_count[
                    (cell["territory"].part_id, cell["piece_idx"])
                ] += 1
                break

    # Phase B — Piece coverage (1 seed per uncovered surviving piece)
    uncovered_pkeys = sorted(
        [pk for pk in cells_by_piece if piece_seed_count[pk] == 0],
        key=lambda pk: -piece_areas[pk],
    )
    for pkey in uncovered_pkeys:
        if len(seeds) >= K:
            break
        piece_cells_idx = sorted(
            cells_by_piece[pkey], key=lambda i: -all_cells[i]["area"],
        )
        for biggest_idx in piece_cells_idx:
            cell = all_cells[biggest_idx]
            candidates = [
                regions_by_id[rid] for rid in cell["regions"] if rid not in used
            ]
            picked = _farthest_or_centrality(
                candidates, seed_region_ids,
                region_graph, region_poly_by_id, bfs_cache,
            )
            if picked is None:
                continue
            seeds.append(SeedPlacement(region=picked, phase="coverage"))
            used.add(picked.region_id)
            seed_region_ids.append(picked.region_id)
            cell_seed_count[biggest_idx] += 1
            piece_seed_count[pkey] += 1
            break  # next uncovered piece

    # Phase C — Load-balanced extras (per piece)
    while len(seeds) < K:
        candidate_pkeys: list[tuple[int, int]] = []
        for pkey, t_cells in cells_by_piece.items():
            non_hub = [i for i in t_cells if i != hub_cell_idx]
            if not non_hub:
                continue
            if any(
                any(rid not in used for rid in all_cells[i]["regions"])
                for i in non_hub
            ):
                candidate_pkeys.append(pkey)

        target_cell_idx: int
        target_pkey: tuple[int, int]
        if candidate_pkeys:
            target_pkey = max(
                candidate_pkeys,
                key=lambda pk: (
                    piece_areas[pk] / max(1, piece_seed_count[pk]),
                    piece_areas[pk],
                ),
            )
            target_cells = [
                i for i in cells_by_piece[target_pkey]
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
            target_pkey = (
                all_cells[hub_cell_idx]["territory"].part_id,
                all_cells[hub_cell_idx]["piece_idx"],
            )

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
            picked = _farthest_or_centrality(
                candidate_regions, seed_region_ids,
                region_graph, region_poly_by_id, bfs_cache,
            )
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
        seed_region_ids.append(picked.region_id)
        cell_seed_count[target_cell_idx] += 1
        piece_seed_count[target_pkey] += 1

    return tuple(seeds)


_INF_HOP = 10**9


def _farthest_or_centrality(
    candidate_regions,
    seed_region_ids,
    region_graph,
    region_poly_by_id,
    bfs_cache: dict,
):
    """Pick region farthest from existing seeds: hop primary, Euclidean tie.

    Ranking key: (min_hop DESC, min_euclidean DESC, area DESC, -region_id).
    Falls back to ``pick_top_centrality`` when no existing seeds yet.

    ``bfs_cache``: dict[seed_id, dict[region_id, hop_distance]], mutated.
    """
    if not candidate_regions:
        return None
    if not seed_region_ids:
        return pick_top_centrality(candidate_regions, region_graph)

    # Populate cache lazily
    for sid in seed_region_ids:
        if sid not in bfs_cache:
            bfs_cache[sid] = _bfs_all_distances(sid, region_graph)

    existing_centroids = [
        region_poly_by_id[sid].centroid for sid in seed_region_ids
    ]

    def key(r):
        rc = region_poly_by_id[r.region_id].centroid
        min_hop = min(
            bfs_cache[sid].get(r.region_id, _INF_HOP)
            for sid in seed_region_ids
        )
        min_euc = min(
            hypot(rc.x - ec.x, rc.y - ec.y) for ec in existing_centroids
        )
        return (min_hop, min_euc, region_area(r), -r.region_id)

    return max(candidate_regions, key=key)


def _aspect_ok_for_max(
    region_ids,
    regions_by_id: dict,
    theta: float,
    max_aspect: float,
) -> bool:
    """True if union's local-frame bbox aspect ≤ max_aspect (or degenerate)."""
    aspect = _local_bbox_aspect(region_ids, regions_by_id, theta)
    if aspect is None:
        return True
    return aspect <= max_aspect


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
            p = _rotate(p, theta, sign=-1)
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
    room_max_aspect: dict[int, float],
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

    # ----- Stage 1 — per-piece single-seed bulk absorb -----
    # A "piece" is (part_id, piece_id). Disconnected pieces of the same part
    # (e.g., case 13 cross's two arms) are treated as separate logical units
    # so a single seed in one arm does NOT absorb the other arm.
    piece_room_count: dict[tuple[int, int], int] = defaultdict(int)
    room_per_piece: dict[tuple[int, int], int] = {}
    for room_idx, rids in room_regions.items():
        if not rids:
            continue
        # All assigned regions of one room come from one piece (cross-theta
        # forbidden + Phase B assigns within one piece). For robustness use
        # the seed (first region) as canonical.
        r0 = regions_by_id[rids[0]]
        pkey = (r0.part_id, r0.piece_id)
        piece_room_count[pkey] += 1
        room_per_piece[pkey] = room_idx
    single_seed_pkeys = {
        pk for pk, c in piece_room_count.items() if c == 1
    }

    for rid in list(regions_by_id.keys()):
        if rid in region_to_room:
            continue
        r = regions_by_id[rid]
        pkey = (r.part_id, r.piece_id)
        if pkey not in single_seed_pkeys:
            continue
        target = room_per_piece[pkey]
        # Aspect gate: skip absorption that would push room aspect over limit
        theta = regions_by_id[room_regions[target][0]].theta
        if not _aspect_ok_for_max(
            tuple(room_regions[target]) + (rid,),
            regions_by_id, theta,
            room_max_aspect.get(target, float("inf")),
        ):
            continue
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
        # Aspect gate
        theta_chosen = regions_by_id[room_regions[chosen][0]].theta
        combined_chosen = tuple(room_regions[chosen]) + tuple(cell_unassigned)
        if not _aspect_ok_for_max(
            combined_chosen, regions_by_id, theta_chosen,
            room_max_aspect.get(chosen, float("inf")),
        ):
            continue  # would violate aspect — leave cell unassigned
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
        # Aspect gate
        theta_chosen = regions_by_id[room_regions[chosen][0]].theta
        if not _aspect_ok_for_max(
            tuple(room_regions[chosen]) + (rid,),
            regions_by_id, theta_chosen,
            room_max_aspect.get(chosen, float("inf")),
        ):
            continue  # would violate aspect — leave region unassigned
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

    # --- Per-room max aspect (W12: hard aspect gate, per RoomSpec) ---
    room_max_aspect: dict[int, float] = {}
    for i, spec in enumerate(fixture.rooms):
        rng = fixture.resolved_aspect_range(spec)
        room_max_aspect[i] = rng[1] if rng is not None else float("inf")

    # --- Partition: per piece, per cell ---
    # Initialize each room with its seed FIRST so region_ids[0] always points
    # at the seed (for diagnostics + viz markers). Main loop / stages skip
    # regions already in region_to_room, so this doesn't double-process.
    room_regions: dict[int, list[int]] = {i: [] for i in range(K)}
    region_to_room: dict[int, int] = {}
    for room_idx, seed_id in seeds_by_room.items():
        room_regions[room_idx].append(seed_id)
        region_to_room[seed_id] = room_idx

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
                    # whole cell → that room, with W12 aspect gate per region
                    room_idx = seed_to_room[cell_seeds[0]]
                    room_theta = regions_by_id[cell_seeds[0]].theta
                    room_max = room_max_aspect.get(room_idx, float("inf"))
                    for rid in cell_regions:
                        if rid in region_to_room:
                            continue
                        combined = tuple(room_regions[room_idx]) + (rid,)
                        if not _aspect_ok_for_max(
                            combined, regions_by_id, room_theta, room_max,
                        ):
                            continue  # aspect violation — stays unassigned
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
                        (sid, _rotate(
                            region_poly_by_id[sid].centroid,
                            territory.theta, sign=-1,
                        ))
                        for sid in cell_seeds
                    ]
                    regions_local = [
                        (rid, _rotate(
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
                    seed_max_aspect_local = {
                        sid: room_max_aspect.get(
                            seed_to_room[sid], float("inf"),
                        )
                        for sid in cell_seeds
                    }
                    assignment = _guillotine_partition(
                        cell_bbox_local, seeds_local, regions_local,
                        region_local_bboxes,
                        seed_max_aspect_local,
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
        room_max_aspect=room_max_aspect,
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
