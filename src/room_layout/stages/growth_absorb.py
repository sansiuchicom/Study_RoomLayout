"""Leftover absorption for room partition growth — Phase 7 (Step 04 §4.10).

Plan reference: ``004_Step04_AlgorithmCore_Plan.md`` §4.10 + S04-D1.

Faithful port of Cell ``growth_absorb.py`` — the 3-stage post-growth
absorption of unassigned regions (W10). This is the sole consumer of
``shape_gate._reflex_of_union`` (the reflex helper deferred from Step 03 by
S03-D16).

Adaptations: imports swapped to ``room_layout.stages.*`` (the inline
``shape_gate`` import is hoisted — no import cycle, since ``shape_gate`` only
reaches ``regionize``); ``_local_bbox_aspect`` builds its polygon via
``to_shapely`` (identical to Cell's ``sg.Polygon(exterior, holes)``); the
``shape`` parameter is renamed ``floor`` (``FloorShape``) per S03-D13.
Algorithm unchanged.
"""

from __future__ import annotations

from collections import defaultdict

import shapely.ops

from room_layout.schema import FloorShape
from room_layout.stages._helpers import rotate_radians as _rotate
from room_layout.stages._helpers import to_shapely as _to_shapely
from room_layout.stages.growth_seed import _enumerate_cells_with_regions
from room_layout.stages.shape_gate import _reflex_of_union


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
        p = _to_shapely(r.shape)
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
    floor: FloorShape,
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
      For each territory whose room_count == 1, all unassigned regions in that
      territory go to that single room (shape unrestricted).

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
        # forbidden + Phase B assigns within one piece). For robustness use the
        # seed (first region) as canonical.
        r0 = regions_by_id[rids[0]]
        pkey = (r0.part_id, r0.piece_id)
        piece_room_count[pkey] += 1
        room_per_piece[pkey] = room_idx
    single_seed_pkeys = {pk for pk, c in piece_room_count.items() if c == 1}

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
            regions_by_id,
            theta,
            room_max_aspect.get(target, float("inf")),
        ):
            continue
        room_regions[target].append(rid)
        region_to_room[rid] = target

    # ----- Stage 2 -----
    all_cells = _enumerate_cells_with_regions(
        floor,
        rg,
        territories,
        region_poly_by_id,
    )
    # Cells with all regions unassigned (= no seed inside)
    cells_unassigned = [
        (idx, cell)
        for idx, cell in enumerate(all_cells)
        if all(rid not in region_to_room for rid in cell["regions"])
    ]
    # Biggest first
    cells_unassigned.sort(key=lambda x: -x[1]["area"])

    for cell_idx, cell in cells_unassigned:
        cell_unassigned = [rid for rid in cell["regions"] if rid not in region_to_room]
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
            combined_chosen,
            regions_by_id,
            theta_chosen,
            room_max_aspect.get(chosen, float("inf")),
        ):
            continue  # would violate aspect — leave cell unassigned
        for rid in cell_unassigned:
            room_regions[chosen].append(rid)
            region_to_room[rid] = chosen

    # ----- Stage 3 -----
    unassigned_regions = sorted(
        [r for r in regions_by_id.values() if r.region_id not in region_to_room],
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
            regions_by_id,
            theta_chosen,
            room_max_aspect.get(chosen, float("inf")),
        ):
            continue  # would violate aspect — leave region unassigned
        room_regions[chosen].append(rid)
        region_to_room[rid] = chosen
