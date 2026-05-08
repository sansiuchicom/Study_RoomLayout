"""LIR (Largest Inscribed Rectangle) search.

Ported from references/cell_v3_2.md §4.

Pipeline:
    rasterize_polygon       — polygon → binary mask (matplotlib.Path-based, vectorized)
    max_rect_in_histogram   — O(N) stack-based maximal rectangle in a histogram
    max_rect_in_mask        — O(M*N) maximal rectangle in a binary 2D mask
    lir_at_angle            — LIR within polygon.exterior at a given rotation angle
    candidate_angles_from_boundary
                            — length-weighted binning of polygon edge angles → top-K candidates
    find_main_rect_refined  — 2-step LIR search: coarse candidates + fine refinement

Holes are intentionally ignored: the algorithm finds the LIR of the polygon's
outer boundary; later cell-level intersection naturally avoids holes.
"""
from __future__ import annotations

import numpy as np
import shapely
import shapely.affinity as sa
import shapely.geometry as sg


def rasterize_polygon(polygon, resolution=0.1):
    """Rasterize polygon interior to a binary 2D mask.

    Uses `shapely.contains_xy` (vectorized; shapely>=2.0) over a uniform grid
    of cell-center sample points spaced by `resolution` in polygon-coordinate
    units. v3.2 reference uses matplotlib.Path; switched to shapely.contains_xy
    here to keep matplotlib out of runtime dependencies.

    Returns:
        (mask, (minx, miny, resolution)) — `mask` is a (ny, nx) bool array;
        the tuple gives the world-coordinate origin and pitch needed to map
        mask indices back to coordinates.
    """
    minx, miny, maxx, maxy = polygon.bounds
    nx = int(np.ceil((maxx - minx) / resolution)) + 1
    ny = int(np.ceil((maxy - miny) / resolution)) + 1
    xs = minx + (np.arange(nx) + 0.5) * resolution
    ys = miny + (np.arange(ny) + 0.5) * resolution
    grid_x, grid_y = np.meshgrid(xs, ys)
    inside = shapely.contains_xy(polygon, grid_x.ravel(), grid_y.ravel()).reshape(ny, nx)
    return inside, (minx, miny, resolution)


def max_rect_in_histogram(heights):
    """Maximal rectangle in a histogram. O(N) via monotonic stack.

    Returns:
        (left_idx, height, width) — the maximal rectangle's left column index
        within the histogram, its height (in bar units), and its width.
        For an empty input, returns (0, 0, 0).
    """
    stack = []
    n = len(heights)
    best = (0, 0, 0)
    best_area = 0
    for i in range(n + 1):
        h = heights[i] if i < n else 0
        while stack and heights[stack[-1]] > h:
            top = stack.pop()
            top_h = heights[top]
            left = stack[-1] + 1 if stack else 0
            width = i - left
            area = top_h * width
            if area > best_area:
                best_area = area
                best = (left, top_h, width)
        stack.append(i)
    return best


def max_rect_in_mask(mask):
    """Maximal axis-aligned all-True rectangle in a binary 2D mask. O(M*N).

    Builds, row by row, a column-wise "stacked-True heights" histogram and
    runs `max_rect_in_histogram` on each row.

    Returns:
        (i0, j0, w, h) — top-left mask-index column/row of the maximal rect,
        plus its width and height in mask cells. None if the mask is empty.
    """
    rows, cols = mask.shape
    if rows == 0 or cols == 0:
        return None
    heights = np.zeros(cols, dtype=int)
    best = None
    best_area = 0
    for j in range(rows):
        heights = np.where(mask[j], heights + 1, 0)
        left, h, w = max_rect_in_histogram(heights.tolist())
        if h * w > best_area:
            best_area = h * w
            best = (left, j - h + 1, w, h)
    return best


def lir_at_angle(polygon, theta, resolution=0.1):
    """Largest inscribed axis-aligned rectangle at rotation `theta` (radians).

    The polygon is rotated by -theta about its centroid so that the desired
    LIR direction becomes axis-aligned, rasterized, and `max_rect_in_mask`
    finds the largest interior rectangle. The result is rotated back.

    Holes are ignored — only `polygon.exterior` is rasterized. Cell-level
    intersection downstream re-applies hole geometry.

    Returns: a `shapely.geometry.box` rotated to the original orientation,
    or None if no positive rectangle can be inscribed.
    """
    cx, cy = polygon.centroid.x, polygon.centroid.y
    rotated = sa.rotate(polygon, -np.degrees(theta), origin=(cx, cy))
    exterior_only = sg.Polygon(rotated.exterior)
    mask, (minx, miny, res) = rasterize_polygon(exterior_only, resolution)
    result = max_rect_in_mask(mask)
    if result is None:
        return None
    i0, j0, w, h = result
    if w == 0 or h == 0:
        return None
    rect_rotated = sg.box(
        minx + i0 * res, miny + j0 * res,
        minx + (i0 + w) * res, miny + (j0 + h) * res,
    )
    return sa.rotate(rect_rotated, np.degrees(theta), origin=(cx, cy))


def candidate_angles_from_boundary(polygon, bin_deg=2.0, top_k=4):
    """Pick LIR-search angle candidates from the polygon's boundary edges.

    Each exterior edge contributes its angle (mod π/2) weighted by edge
    length. Angles are binned at `bin_deg` resolution; the `top_k` heaviest
    bins are returned. 0° (axis-aligned) is always included.

    Returns: list of angles in radians within [0, π/2).
    """
    coords = list(polygon.exterior.coords)
    bin_size = np.radians(bin_deg)
    binned = {}
    for i in range(len(coords) - 1):
        dx = coords[i + 1][0] - coords[i][0]
        dy = coords[i + 1][1] - coords[i][1]
        L = np.hypot(dx, dy)
        if L < 0.05:
            continue
        angle = np.arctan2(dy, dx) % (np.pi / 2)
        key = round(angle / bin_size) * bin_size
        binned[key] = binned.get(key, 0) + L
    sorted_bins = sorted(binned.items(), key=lambda x: -x[1])
    candidates = [k for k, _ in sorted_bins[:top_k]]
    if not any(abs(c) < bin_size for c in candidates):
        candidates.append(0.0)
    return candidates


def find_main_rect_refined(polygon, resolution=0.05,
                           coarse_bin_deg=2.0, top_k_coarse=4,
                           fine_step_deg=0.5, fine_range_deg=2.0,
                           n_refine_centers=2):
    """Two-step LIR search: coarse boundary-binned candidates + fine refinement.

    1. Coarse: gather angle candidates via `candidate_angles_from_boundary`,
       compute LIR at each.
    2. Fine: around the top `n_refine_centers` coarse winners, sweep ±`fine_range_deg`
       at `fine_step_deg` resolution to refine.

    Returns:
        (rect, theta, info) where `rect` is the maximal LIR (shapely.box rotated),
        `theta` is its angle in radians, and `info` carries diagnostic data.
        Returns (None, 0.0, {}) if no LIR can be found.
    """
    coarse_angles = candidate_angles_from_boundary(
        polygon, bin_deg=coarse_bin_deg, top_k=top_k_coarse)

    coarse_results = []
    for theta in coarse_angles:
        rect = lir_at_angle(polygon, theta, resolution)
        if rect is not None:
            coarse_results.append({
                'theta': theta, 'rect': rect,
                'area': rect.area, 'phase': 'coarse',
            })
    if not coarse_results:
        return None, 0.0, {}

    coarse_sorted = sorted(coarse_results, key=lambda r: -r['area'])
    fine_step = np.radians(fine_step_deg)
    n_steps = int(np.radians(fine_range_deg) / fine_step)
    fine_results = []
    tried = set(round(r['theta'] * 1e5) for r in coarse_results)
    for center_info in coarse_sorted[:n_refine_centers]:
        for i in range(-n_steps, n_steps + 1):
            if i == 0:
                continue
            theta = (center_info['theta'] + i * fine_step) % (np.pi / 2)
            key = round(theta * 1e5)
            if key in tried:
                continue
            tried.add(key)
            rect = lir_at_angle(polygon, theta, resolution)
            if rect is not None:
                fine_results.append({
                    'theta': theta, 'rect': rect,
                    'area': rect.area, 'phase': 'fine',
                })

    all_results = coarse_results + fine_results
    best = max(all_results, key=lambda r: r['area'])
    return best['rect'], best['theta'], {'best': best}
