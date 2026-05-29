"""Reflex-shape helpers for room absorption — Phase 6/7.

Plan reference: ``004_Step04_AlgorithmCore_Plan.md`` §4.3 + S04-D1.

Ported from Cell ``shape_gate.py``. Deferred out of Step 03 by S03-D16:
``shape_gate`` is a reflex helper consumed by ``growth_absorb`` (Phase 6/7
room absorption), **not** a Phase-5 gate stage — so it lands here in Step 04
alongside its only consumer. Adapted to the new schema: geometry helpers come
from ``room_layout.stages._helpers`` and ``Region`` from
``room_layout.stages.regionize``; the algorithm is unchanged (S04-D1).
"""

from __future__ import annotations

import shapely.geometry as sg
import shapely.geometry.polygon
import shapely.ops

from room_layout.stages._helpers import rotate_radians as _rotate
from room_layout.stages._helpers import to_shapely as _to_shapely
from room_layout.stages.regionize import Region

# Sentinel returned by ``_reflex_of_union`` when the union is empty or not a
# single Polygon (e.g., disconnected MultiPolygon). Treated as "definitely
# rejected" by the gate.
_REFLEX_INVALID = 99


def count_reflex_vertices(poly: sg.Polygon) -> int:
    """Number of concave (reflex) vertices on the polygon's exterior.

    The polygon is reoriented CCW first so the cross-product sign test is
    consistent.
    """
    if poly.is_empty:
        return 0
    oriented = shapely.geometry.polygon.orient(poly, sign=1.0)
    coords = list(oriented.exterior.coords)
    if len(coords) >= 2 and coords[0] == coords[-1]:
        coords = coords[:-1]  # drop closing duplicate
    n = len(coords)
    if n < 3:
        return 0
    count = 0
    for i in range(n):
        ax, ay = coords[(i - 1) % n]
        bx, by = coords[i]
        cx, cy = coords[(i + 1) % n]
        cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if cross < -1e-9:
            count += 1
    return count


def _reflex_of_union(
    region_ids: tuple[int, ...],
    regions_by_id: dict[int, Region],
    theta: float,
) -> int:
    """Reflex count of the union of regions rotated to local frame.

    Returns ``_REFLEX_INVALID`` if union is empty or non-Polygon. Fast-paths
    bbox-equivalent unions to 0 so FP rotation noise on rotated cases does
    not register phantom reflex vertices on truly axis-aligned shapes.
    """
    if not region_ids:
        return _REFLEX_INVALID
    polys: list[sg.Polygon] = []
    for rid in region_ids:
        r = regions_by_id[rid]
        p = _to_shapely(r.shape)
        if theta != 0.0:
            p = _rotate(p, theta, sign=-1)
        polys.append(p)
    union = shapely.ops.unary_union(polys)
    if union.is_empty or union.geom_type != "Polygon":
        return _REFLEX_INVALID

    # Fast path: union == its bbox (area-wise) → axis-aligned rectangle.
    # Bypasses cross-product reflex count which can register phantom reflex
    # on FP-noisy rotated polygons whose geometry is still rectangular.
    minx, miny, maxx, maxy = union.bounds
    bbox_area = (maxx - minx) * (maxy - miny)
    if abs(bbox_area - union.area) < 1e-6 * max(union.area, 1e-9):
        return 0
    return count_reflex_vertices(union)
