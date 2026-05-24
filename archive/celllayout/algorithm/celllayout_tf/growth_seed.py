"""Cell-aware seed placement helpers for room partition growth."""

from __future__ import annotations

from collections import defaultdict
from math import hypot

import shapely.geometry as sg

from .geometry import to_shapely as _to_shapely
from .growth_cells import vertex_cells_of_piece
from .region_graph import RegionGraph
from .seed_placement import (
    SeedPlacement,
    _INF_HOP,
    _bfs_all_distances,
    pick_top_centrality,
    region_area,
)
from .territory import (
    KIND_CURVED,
    Territory,
    collect_cross_theta_contact_coords,
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
