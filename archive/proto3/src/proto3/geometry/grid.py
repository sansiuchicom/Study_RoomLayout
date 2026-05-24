"""Anisotropic grid + 50% merge rule + theta helpers.

Ported from references/cell_v3_2.md §6, §7, §8.

Pipeline:
    compute_proportional_cell_size — derive (cell_w, cell_h, base_phase) from a main rect
                                     and target size so the rect divides into integer N×M
                                     cells (zero sliver).
    grid_no_skip_aniso              — tile a piece with anisotropic grid; preserve every
                                     polygon-cell intersection part (MultiPolygon all-parts;
                                     v3.2 critical fix #1).
    merge_below_50_aniso            — absorb cells smaller than `threshold_ratio` × cell area
                                     into the neighbor sharing the longest real boundary;
                                     buffer-free neighbor detection (v3.2 fix #2) and orphan
                                     preservation (v3.2 fix #3).
    piece_direct_theta              — fallback dominant orientation from a piece's straight
                                     boundary segments (used when LIR can't be trusted).
    angle_diff                      — angular distance in the [0, π/2) reduced domain.
"""
from __future__ import annotations

import numpy as np
import shapely.affinity as sa
import shapely.geometry as sg


def compute_proportional_cell_size(main_rect, main_theta, target):
    """Derive `(cell_w, cell_h, base_phase)` so `main_rect` divides into integer N×M cells.

    The main rect is rotated by -`main_theta` to make it axis-aligned; its width and
    height are partitioned into N and M cells where `N = round(W / target)` (and likewise
    M). The resulting `cell_w`, `cell_h` are typically slightly different from `target`
    but their integer multiples match the rect exactly — zero sliver inside the family.

    Returns:
        (cell_w, cell_h, base_phase) where `base_phase = (cx, cy, minx, miny)` records
        the rotation centroid and the rotated-frame grid origin so the same phase chain
        can be reused across leftover pieces of the same family.
    """
    cx, cy = main_rect.centroid.x, main_rect.centroid.y
    rotated = sa.rotate(main_rect, -np.degrees(main_theta), origin=(cx, cy))
    minx, miny, maxx, maxy = rotated.bounds
    W = maxx - minx
    H = maxy - miny
    n_x = max(1, round(W / target))
    n_y = max(1, round(H / target))
    cell_w = W / n_x
    cell_h = H / n_y
    base_phase = (cx, cy, minx, miny)
    return cell_w, cell_h, base_phase


def grid_no_skip_aniso(piece, theta, cell_w, cell_h,
                       phase_origin=None, seed=42, min_create_area=1e-6):
    """Tile a piece with an anisotropic grid; preserve every polygon-cell intersection part.

    The piece is rotated by -`theta` so the grid becomes axis-aligned, sampled cell-by-cell,
    and intersected with the rotated polygon. Each non-empty intersection becomes a cell.

    **Critical fix vs prior versions**: when a cell's intersection is a `MultiPolygon`
    (e.g., the polygon pinches the cell into two parts), every part is preserved as its
    own cell rather than dropping all but the largest — otherwise polygon area silently
    leaks into "white space."

    Args:
        piece: source polygon (shapely.Polygon)
        theta: family rotation in radians
        cell_w, cell_h: anisotropic cell dimensions (typically from
            `compute_proportional_cell_size`)
        phase_origin: optional `(cx, cy, ox, oy)` to reuse the family's phase chain.
            If None, a random offset is chosen using `seed`.
        seed: RNG seed for the random phase origin (only used when `phase_origin is None`).
        min_create_area: drop intersection parts below this area (default 1e-6).

    Returns:
        `(cells, phase_origin)` — list of cells in the original (un-rotated) frame,
        plus the phase origin used (for downstream pieces in the same family).
    """
    if phase_origin is None:
        rng = np.random.default_rng(seed)
        cx, cy = piece.centroid.x, piece.centroid.y
        ox, oy = rng.uniform(0, cell_w), rng.uniform(0, cell_h)
    else:
        cx, cy, ox, oy = phase_origin

    rotated = sa.rotate(piece, -np.degrees(theta), origin=(cx, cy))
    minx, miny, maxx, maxy = rotated.bounds
    minx_g = np.floor((minx - ox) / cell_w) * cell_w + ox - cell_w
    miny_g = np.floor((miny - oy) / cell_h) * cell_h + oy - cell_h
    maxx_g = np.ceil((maxx - ox) / cell_w) * cell_w + ox + cell_w
    maxy_g = np.ceil((maxy - oy) / cell_h) * cell_h + oy + cell_h
    nx = int(np.round((maxx_g - minx_g) / cell_w))
    ny = int(np.round((maxy_g - miny_g) / cell_h))

    cells = []
    for j in range(ny):
        for i in range(nx):
            x0 = minx_g + i * cell_w
            y0 = miny_g + j * cell_h
            cell = sg.box(x0, y0, x0 + cell_w, y0 + cell_h)
            inter = cell.intersection(rotated)
            if inter.is_empty:
                continue
            if isinstance(inter, sg.MultiPolygon):
                parts = [g for g in inter.geoms
                         if isinstance(g, sg.Polygon) and g.area >= min_create_area]
            elif isinstance(inter, sg.Polygon):
                parts = [inter] if inter.area >= min_create_area else []
            else:
                parts = []
                if hasattr(inter, 'geoms'):
                    for g in inter.geoms:
                        if isinstance(g, sg.Polygon) and g.area >= min_create_area:
                            parts.append(g)
            cells.extend(parts)

    return (
        [sa.rotate(c, np.degrees(theta), origin=(cx, cy)) for c in cells],
        (cx, cy, ox, oy),
    )


def merge_below_50_aniso(cells, cell_w, cell_h,
                         threshold_ratio=0.5, max_iter=100):
    """Absorb cells smaller than `threshold_ratio` × cell area into a real-boundary neighbor.

    Iteratively picks the smallest below-threshold cell and merges it into the neighbor
    that shares the longest real boundary segment.

    **Critical fixes vs prior versions**:
    1. Neighbors are detected via actual shared boundary length (buffer-free), preventing
       merges of cells that only "almost touch" (which would form `MultiPolygon` results
       and re-introduce sliver fragmentation).
    2. Cells with no real-boundary neighbor (true orphans) are kept rather than nullified
       — a small atom is still better than empty space in the polygon.

    Args:
        cells: list of `shapely.Polygon` (or geometries with `.area`).
        cell_w, cell_h: nominal cell dimensions used to compute the absorption threshold.
        threshold_ratio: 0.5 means cells below half a full cell area are absorbed.
        max_iter: hard iteration cap for safety.

    Returns: list of cells (possibly merged) with all `None` entries removed.
    """
    threshold = cell_w * cell_h * threshold_ratio
    cells = list(cells)
    skip_indices = set()  # orphan cells flagged once and never revisited

    for _ in range(max_iter):
        smallest_idx, smallest_area = None, float('inf')
        for i, c in enumerate(cells):
            if c is None or i in skip_indices:
                continue
            if c.area < threshold and c.area < smallest_area:
                smallest_area = c.area
                smallest_idx = i
        if smallest_idx is None:
            break

        small = cells[smallest_idx]
        # Real shared boundary only — no buffer, to keep MultiPolygon merges from re-fragmenting
        neighbors = []
        for j, other in enumerate(cells):
            if j == smallest_idx or other is None:
                continue
            inter = small.intersection(other)
            if inter.is_empty:
                continue
            if hasattr(inter, 'length') and inter.length > 0.001:
                neighbors.append((j, other.area, inter.length))

        if not neighbors:
            # True orphan — keep it; better a small atom than empty polygon area
            skip_indices.add(smallest_idx)
            continue

        # Prefer the longest shared boundary (most natural merge direction)
        biggest_j = max(neighbors, key=lambda x: x[2])[0]
        merged = small.union(cells[biggest_j])
        if isinstance(merged, sg.Polygon):
            cells[biggest_j] = merged
        elif isinstance(merged, sg.MultiPolygon):
            # Safety: preserve every part rather than drop the smaller ones
            geoms = sorted(merged.geoms, key=lambda g: -g.area)
            cells[biggest_j] = geoms[0]
            for extra in geoms[1:]:
                cells.append(extra)
        cells[smallest_idx] = None

    return [c for c in cells if c is not None]


def piece_direct_theta(piece, min_straight_length=1.0):
    """Infer a piece's dominant orientation from its long straight boundary segments.

    Used as a fallback when LIR-based detection isn't trustworthy (e.g., circular pieces
    where any rotation yields a similar inscribed rectangle).

    Each boundary segment longer than `min_straight_length` contributes its angle (mod π/2)
    weighted by length. The 4-fold complex average folds π/2 symmetry; if the resulting
    weight magnitude is below 10% of total weight, no clear direction exists and `None`
    is returned.

    Returns: theta in radians within [0, π/2), or None if direction is undetermined.
    """
    coords = list(piece.exterior.coords)
    angles, weights = [], []
    for i in range(len(coords) - 1):
        e_len = np.hypot(
            coords[i + 1][0] - coords[i][0],
            coords[i + 1][1] - coords[i][1],
        )
        if e_len < min_straight_length:
            continue
        dx = coords[i + 1][0] - coords[i][0]
        dy = coords[i + 1][1] - coords[i][1]
        angles.append(np.arctan2(dy, dx) % (np.pi / 2))
        weights.append(e_len)
    if not angles:
        return None
    s = sum(w * np.sin(4 * a) for w, a in zip(weights, angles))
    c = sum(w * np.cos(4 * a) for w, a in zip(weights, angles))
    if np.hypot(s, c) < 0.1 * sum(weights):
        return None
    return (np.arctan2(s, c) / 4) % (np.pi / 2)


def angle_diff(a, b):
    """Angular distance between two angles in the [0, π/2) reduced domain.

    Treats angles modulo π/2 (i.e., 0° and 90° are the same direction). Useful for
    comparing dominant orientations where rotational symmetry of axis-aligned grids
    makes π/2 the natural period.
    """
    d = abs(a - b) % (np.pi / 2)
    return min(d, np.pi / 2 - d)
