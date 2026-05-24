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

from .atomize import atomize
from .dimensions import DimensionPolicy
from .geometry import rotate_radians as _rotate, to_shapely as _to_shapely
from .growth_absorb import (
    _absorb_remaining,
    _aspect_ok_for_max,
    _local_bbox_aspect,
)
from .growth_cells import (
    _assign_to_cells,
    _guillotine_partition,
    _snap_to_region_edge,
    reflex_vertices_local,
    vertex_cells_of_piece,
)
from .growth_seed import (
    _enumerate_cells_with_regions,
    _farthest_or_centrality,
    auto_place_seeds_by_cells,
)
from .region_graph import build_region_graph
from .regionize import regionize
from .territory import (
    KIND_CURVED,
    collect_cross_theta_contact_coords,
    resolve_territories,
)


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
