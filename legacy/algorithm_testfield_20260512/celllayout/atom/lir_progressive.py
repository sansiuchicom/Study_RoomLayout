"""Auto LIR helpers used by the per-family progressive fill pipeline."""
import numpy as np
import shapely.affinity as sa
import shapely.geometry as sg
from matplotlib.path import Path


def rasterize_polygon(polygon, resolution=0.1):
    """Rasterize the polygon exterior to a binary matrix."""
    coords = list(polygon.exterior.coords)
    minx, miny, maxx, maxy = polygon.bounds
    nx = int(np.ceil((maxx - minx) / resolution)) + 1
    ny = int(np.ceil((maxy - miny) / resolution)) + 1
    xs = minx + (np.arange(nx) + 0.5) * resolution
    ys = miny + (np.arange(ny) + 0.5) * resolution
    grid_x, grid_y = np.meshgrid(xs, ys)
    points = np.column_stack([grid_x.ravel(), grid_y.ravel()])
    inside = Path(coords).contains_points(points).reshape(ny, nx)
    return inside, (minx, miny, resolution)


def max_rect_in_histogram(heights):
    """Largest rectangle in a histogram. Returns (left_idx, height, width)."""
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
    """Largest all-true rectangle in a binary matrix."""
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
    """Largest inscribed rectangle for a candidate orientation."""
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
        minx + i0 * res,
        miny + j0 * res,
        minx + (i0 + w) * res,
        miny + (j0 + h) * res,
    )
    return sa.rotate(rect_rotated, np.degrees(theta), origin=(cx, cy))


def candidate_angles_from_boundary(polygon, bin_deg=2.0, top_k=4):
    """Length-weighted boundary angle candidates, normalized to [0, pi/2)."""
    coords = list(polygon.exterior.coords)
    bin_size = np.radians(bin_deg)
    binned = {}
    for i in range(len(coords) - 1):
        dx = coords[i + 1][0] - coords[i][0]
        dy = coords[i + 1][1] - coords[i][1]
        length = np.hypot(dx, dy)
        if length < 0.05:
            continue
        angle = np.arctan2(dy, dx) % (np.pi / 2)
        key = round(angle / bin_size) * bin_size
        binned[key] = binned.get(key, 0.0) + length
    candidates = [k for k, _ in sorted(binned.items(), key=lambda x: -x[1])[:top_k]]
    if not any(abs(c) < bin_size for c in candidates):
        candidates.append(0.0)
    return candidates


def find_main_rect_refined(
    polygon,
    resolution=0.05,
    coarse_bin_deg=2.0,
    top_k_coarse=4,
    fine_step_deg=0.5,
    fine_range_deg=2.0,
    n_refine_centers=2,
):
    """Two-step LIR search: coarse boundary angles, then fine refinement."""
    coarse_angles = candidate_angles_from_boundary(
        polygon, bin_deg=coarse_bin_deg, top_k=top_k_coarse
    )

    coarse_results = []
    for theta in coarse_angles:
        rect = lir_at_angle(polygon, theta, resolution)
        if rect is not None:
            coarse_results.append(
                {"theta": theta, "rect": rect, "area": rect.area, "phase": "coarse"}
            )
    if not coarse_results:
        return None, 0.0, {}

    coarse_sorted = sorted(coarse_results, key=lambda r: -r["area"])
    fine_step = np.radians(fine_step_deg)
    n_steps = int(np.radians(fine_range_deg) / fine_step)
    fine_results = []
    tried = set(round(r["theta"] * 1e5) for r in coarse_results)
    for center_info in coarse_sorted[:n_refine_centers]:
        for i in range(-n_steps, n_steps + 1):
            if i == 0:
                continue
            theta = (center_info["theta"] + i * fine_step) % (np.pi / 2)
            key = round(theta * 1e5)
            if key in tried:
                continue
            tried.add(key)
            rect = lir_at_angle(polygon, theta, resolution)
            if rect is not None:
                fine_results.append(
                    {"theta": theta, "rect": rect, "area": rect.area, "phase": "fine"}
                )

    best = max(coarse_results + fine_results, key=lambda r: r["area"])
    return best["rect"], best["theta"], {"best": best}
