"""Per-family recursive progressive decomposition — main algorithm.

Ported from references/cell_v3_2.md §9.

Strategy:
    1. Find the largest inscribed rectangle (LIR) and treat it as the family's main region.
    2. If the LIR is meaningful (covers ≥ `min_lir_ratio` of the polygon) and we have
       budget (depth/area), grid-fill the main region and recurse into each leftover piece.
    3. Family bookkeeping: same theta as parent → reuse parent's cell size + phase
       (seamless continuation across leftover pieces, like one big grid). Different theta
       → new family with its own proportional cell sizing from its own main rect.
    4. Terminal case (LIR too small or budget exhausted): grid-fill the polygon directly
       with the inherited or fallback theta/cells.
"""
from __future__ import annotations

import numpy as np
import shapely.affinity as sa
import shapely.geometry as sg

from .grid import (
    angle_diff,
    compute_proportional_cell_size,
    grid_no_skip_aniso,
    merge_below_50_aniso,
    piece_direct_theta,
)
from .lir import find_main_rect_refined


def recursive_progressive_per_family(polygon, target_cell_size=0.3, seed=42,
                                     max_depth=3, min_lir_ratio=0.4,
                                     min_recurse_area=8.0,
                                     lir_resolution=0.05,
                                     _depth=0,
                                     _parent_theta=None,
                                     _parent_phase=None,
                                     _parent_cell_w=None,
                                     _parent_cell_h=None,
                                     _family_id=0,
                                     _next_family_id=None):
    """Recursive per-family decomposition of a polygon into atom cells.

    Args:
        polygon: shapely.Polygon to decompose.
        target_cell_size: target cell side (default 0.3m). Actual cell size is
            family-proportional (integer N×M divides the family's main rect exactly).
        seed: RNG seed for phase-origin randomization (only used at the root family
            and when no LIR is found).
        max_depth: recursion depth cap (default 3).
        min_lir_ratio: if LIR area / polygon area < this, recursion stops at this
            polygon and it becomes a terminal (default 0.4).
        min_recurse_area: polygons below this area are always terminal regardless of
            depth (default 8 m²).
        lir_resolution: rasterization resolution for LIR search (default 0.05 m).

    Internal `_*` arguments carry parent context across the recursion (theta, phase,
    cell size, family id) and a shared mutable counter for the next family id.

    Returns:
        (all_cells, pieces_info, root_main_rect, next_family_id)

        - `all_cells`: list of `(shapely.Polygon, piece_id)` tuples. The piece_id
          indexes into `pieces_info`.
        - `pieces_info`: list of dicts {polygon, theta, role, name, depth, family_id,
          cell_w, cell_h, n_cells} — one entry per geometric piece (main / terminal).
        - `root_main_rect`: the LIR found at the top of this call (or None).
        - `next_family_id`: counter value for the family id allocator.
    """
    if _next_family_id is None:
        _next_family_id = [_family_id + 1]

    rng = np.random.default_rng(seed)
    all_cells = []
    pieces_info = []

    main_rect, main_theta, _ = find_main_rect_refined(
        polygon, resolution=lir_resolution)

    can_recurse = (_depth < max_depth and
                   polygon.area >= min_recurse_area and
                   main_rect is not None)
    has_meaningful_lir = (main_rect is not None and
                          main_rect.area >= polygon.area * min_lir_ratio)

    # Effective theta — LIR-derived if trustworthy, otherwise boundary-direction fallback,
    # otherwise inherit from parent (or 0 at root).
    if main_rect is not None and has_meaningful_lir:
        effective_theta = main_theta
    else:
        effective_theta = piece_direct_theta(polygon, 1.0)
        if effective_theta is None:
            effective_theta = _parent_theta if _parent_theta is not None else 0.0

    # Family decision: same-theta-as-parent piece inherits parent's cell size + phase
    # (seamless grid continuation), otherwise this is a new family with its own sizing.
    is_same_family = (_parent_theta is not None and
                      angle_diff(effective_theta, _parent_theta) < np.radians(2))

    if is_same_family:
        family_id = _family_id
        cell_w = _parent_cell_w
        cell_h = _parent_cell_h
        phase = _parent_phase
        effective_theta = _parent_theta  # snap to exact match
    else:
        family_id = _next_family_id[0]
        _next_family_id[0] += 1
        if main_rect is not None:
            cell_w, cell_h, phase = compute_proportional_cell_size(
                main_rect, effective_theta, target_cell_size)
        else:
            # Fallback: derive cells directly from the polygon's rotated bbox
            cx, cy = polygon.centroid.x, polygon.centroid.y
            rotated = sa.rotate(polygon, -np.degrees(effective_theta),
                                origin=(cx, cy))
            minx, miny, maxx, maxy = rotated.bounds
            W, H = maxx - minx, maxy - miny
            n_x = max(1, round(W / target_cell_size))
            n_y = max(1, round(H / target_cell_size))
            cell_w = W / n_x
            cell_h = H / n_y
            phase = (cx, cy, minx, miny)

    # === TERMINAL: just grid-fill this polygon and return ===
    if not (can_recurse and has_meaningful_lir):
        cells, _ = grid_no_skip_aniso(
            polygon, effective_theta, cell_w, cell_h,
            phase_origin=phase, seed=int(rng.integers(0, 2**31)))
        cells = merge_below_50_aniso(cells, cell_w, cell_h, 0.5)
        pieces_info.append({
            'polygon': polygon, 'theta': effective_theta,
            'role': 'terminal', 'name': f'd{_depth}_terminal',
            'depth': _depth, 'family_id': family_id,
            'cell_w': cell_w, 'cell_h': cell_h,
            'n_cells': len(cells),
        })
        for c in cells:
            all_cells.append((c, 0))
        return all_cells, pieces_info, main_rect, _next_family_id[0]

    # === RECURSIVE: grid-fill the main rect, recurse on each leftover piece ===
    main_region = main_rect.intersection(polygon)
    if isinstance(main_region, sg.MultiPolygon):
        main_subpieces = list(main_region.geoms)
    elif isinstance(main_region, sg.Polygon):
        main_subpieces = [main_region]
    else:
        main_subpieces = []
    main_subpieces = [p for p in main_subpieces if p.area >= 0.001]

    main_phase = phase
    for sub in main_subpieces:
        cells, p_returned = grid_no_skip_aniso(
            sub, effective_theta, cell_w, cell_h,
            phase_origin=main_phase,
            seed=int(rng.integers(0, 2**31)))
        cells = merge_below_50_aniso(cells, cell_w, cell_h, 0.5)
        if main_phase is None:
            main_phase = p_returned
        piece_id = len(pieces_info)
        pieces_info.append({
            'polygon': sub, 'theta': effective_theta,
            'role': 'main', 'name': f'd{_depth}_main',
            'depth': _depth, 'family_id': family_id,
            'cell_w': cell_w, 'cell_h': cell_h,
            'n_cells': len(cells),
        })
        for c in cells:
            all_cells.append((c, piece_id))

    remainder = polygon.difference(main_rect)
    if isinstance(remainder, sg.MultiPolygon):
        rem_pieces = list(remainder.geoms)
    elif isinstance(remainder, sg.Polygon):
        rem_pieces = [remainder]
    else:
        rem_pieces = []
    rem_pieces = [p for p in rem_pieces if p.area >= 0.001]

    for leftover in rem_pieces:
        sub_cells, sub_pieces, _, _ = recursive_progressive_per_family(
            leftover, target_cell_size,
            seed=int(rng.integers(0, 2**31)),
            max_depth=max_depth, min_lir_ratio=min_lir_ratio,
            min_recurse_area=min_recurse_area,
            lir_resolution=lir_resolution,
            _depth=_depth + 1,
            _parent_theta=effective_theta,
            _parent_phase=main_phase,
            _parent_cell_w=cell_w,
            _parent_cell_h=cell_h,
            _family_id=family_id,
            _next_family_id=_next_family_id,
        )
        offset = len(pieces_info)
        for cell, sub_pid in sub_cells:
            all_cells.append((cell, sub_pid + offset))
        pieces_info.extend(sub_pieces)

    return all_cells, pieces_info, main_rect, _next_family_id[0]
