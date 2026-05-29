"""Cell construction helpers for room partition growth — Phase 7 (Step 04 §4.8).

Plan reference: ``004_Step04_AlgorithmCore_Plan.md`` §4.8 + S04-D1.

Faithful port of Cell ``growth_cells.py`` — reflex-vertex cell decomposition
(``vertex_cells_of_piece``) + aspect-minimizing guillotine partition
(``_guillotine_partition``). Only the geometry-helper imports are swapped to
``room_layout.stages._helpers``; the inline ``Counter`` import is hoisted.
"""

from __future__ import annotations

from collections import Counter, defaultdict

import shapely.geometry as sg
import shapely.geometry.polygon
import shapely.ops

from room_layout.schema import ShapePart
from room_layout.stages._helpers import rotate_radians as _rotate
from room_layout.stages._helpers import to_shapely as _to_shapely


def reflex_vertices_local(piece: ShapePart, theta: float) -> list[tuple[float, float]]:
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
    piece: ShapePart,
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
    ``[piece]`` in global frame.
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
                    g for g in result.geoms if g.geom_type == "Polygon" and g.area > 1e-3
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
                    g for g in result.geoms if g.geom_type == "Polygon" and g.area > 1e-3
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
    seed_max_aspect: dict[int, float] | None = None,
) -> dict[int, list[int]]:
    """Recursive aspect-minimizing guillotine partition of a rect cell.

    Each cut is a single straight axis-aligned line (in local frame). Cut
    position starts at the midpoint between adjacent seeds along the chosen
    axis, then SNAPS to the nearest frequent region-edge coord between those
    seeds (so the cut prefers landing on an actual region boundary rather
    than slicing through region interiors). Among all (axis, gap) candidates,
    picks the one minimizing the max aspect of the two resulting sub-rects.

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
            midpoint,
            "x",
            region_local_bboxes,
            region_ids,
            xl,
            xr,
        )
        if cut <= x_L + 1e-9 or cut >= x_R - 1e-9:
            continue
        left_w = cut - x_L
        right_w = x_R - cut
        left_aspect = max(left_w, cell_h) / min(left_w, cell_h)
        right_aspect = max(right_w, cell_h) / min(right_w, cell_h)
        # W12: aspect gate at leaf sub-rect (1-seed sub-rect must satisfy its
        # room's max aspect). Multi-seed sub-rects recurse; checked there.
        if seed_max_aspect is not None:
            left_seeds_x = seeds_x[: i + 1]
            right_seeds_x = seeds_x[i + 1 :]
            if len(left_seeds_x) == 1:
                mx = seed_max_aspect.get(left_seeds_x[0][0], float("inf"))
                if left_aspect > mx:
                    continue
            if len(right_seeds_x) == 1:
                mx = seed_max_aspect.get(right_seeds_x[0][0], float("inf"))
                if right_aspect > mx:
                    continue
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
            midpoint,
            "y",
            region_local_bboxes,
            region_ids,
            yb,
            yt,
        )
        if cut <= y_B + 1e-9 or cut >= y_T - 1e-9:
            continue
        bot_h = cut - y_B
        top_h = y_T - cut
        bot_aspect = max(cell_w, bot_h) / min(cell_w, bot_h)
        top_aspect = max(cell_w, top_h) / min(cell_w, top_h)
        if seed_max_aspect is not None:
            bot_seeds_y = seeds_y[: i + 1]
            top_seeds_y = seeds_y[i + 1 :]
            if len(bot_seeds_y) == 1:
                mx = seed_max_aspect.get(bot_seeds_y[0][0], float("inf"))
                if bot_aspect > mx:
                    continue
            if len(top_seeds_y) == 1:
                mx = seed_max_aspect.get(top_seeds_y[0][0], float("inf"))
                if top_aspect > mx:
                    continue
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
    out.update(
        _guillotine_partition(cell_a, group_a, regions_a, region_local_bboxes, seed_max_aspect)
    )
    out.update(
        _guillotine_partition(cell_b, group_b, regions_b, region_local_bboxes, seed_max_aspect)
    )
    return out
