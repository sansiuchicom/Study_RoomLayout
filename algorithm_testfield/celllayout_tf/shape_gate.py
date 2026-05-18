"""Shape gate for Phase 7 Round 4 growth.

Three layered checks decide whether absorbing a candidate region keeps the
room's shape within policy:

  1. cross-theta — every region in the room must share a theta-group.
  2. curved exemption — any region in a curved territory bypasses Layer 3.
  3. reflex count + global L budget:
       reflex(local-frame union) == 0  → always OK (rectangle)
       reflex(local-frame union) >= 2  → never OK (T/U/Z/+/...)
       reflex(local-frame union) == 1  → OK iff this room was already L,
                                          or fewer than ``max_l_rooms`` other
                                          rooms currently hold an L slot.

A room that is already L can keep absorbing as long as the result stays
reflex==1 — no new slot consumed. A room going L→rect (corner filled in)
frees its slot at the next gate query.
"""

from __future__ import annotations

from math import degrees
from typing import Callable

import shapely.affinity
import shapely.geometry as sg
import shapely.geometry.polygon
import shapely.ops

from .regionize import Region
from .territory import Territory


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


def _to_local_polygon(region: Region) -> sg.Polygon:
    poly = sg.Polygon(
        region.shape.exterior, [list(h) for h in region.shape.holes]
    )
    if region.theta != 0.0:
        poly = shapely.affinity.rotate(poly, -degrees(region.theta), origin=(0, 0))
    return poly


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
        p = sg.Polygon(r.shape.exterior, [list(h) for h in r.shape.holes])
        if theta != 0.0:
            p = shapely.affinity.rotate(p, -degrees(theta), origin=(0, 0))
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


ShapeGate = Callable[
    [int, tuple[int, ...], dict[int, tuple[int, ...]], dict[int, Region]],
    bool,
]


def make_shape_gate(
    territories: tuple[Territory, ...],
    max_l_rooms: int,
) -> ShapeGate:
    """Build a stateless gate function bound to territory kinds + L budget.

    The returned callable is pure — it queries ``rooms_state_before`` to
    determine the current global L count, so the caller doesn't manage
    slot state itself.
    """
    kind_by_part: dict[int, str] = {t.part_id: t.kind for t in territories}

    def gate(
        room_idx: int,
        room_region_ids_after: tuple[int, ...],
        rooms_state_before: dict[int, tuple[int, ...]],
        regions_by_id: dict[int, Region],
    ) -> bool:
        if not room_region_ids_after:
            return False

        # Layer 1 — cross-theta
        rs_after = [regions_by_id[rid] for rid in room_region_ids_after]
        thetas = {round(r.theta, 9) for r in rs_after}
        if len(thetas) > 1:
            return False
        theta = next(iter(thetas))

        # Layer 2 — curved exemption
        kinds = {kind_by_part.get(r.part_id, "axis_aligned") for r in rs_after}
        if "curved" in kinds:
            return True

        # Layer 3 — reflex + L budget
        new_reflex = _reflex_of_union(
            room_region_ids_after, regions_by_id, theta
        )
        if new_reflex == 0:
            return True
        if new_reflex >= 2:
            return False
        # new_reflex == 1 (L shape)
        before_ids = rooms_state_before.get(room_idx, ())
        if before_ids:
            before_theta = regions_by_id[before_ids[0]].theta
            before_reflex = _reflex_of_union(
                before_ids, regions_by_id, before_theta
            )
        else:
            before_reflex = 0
        if before_reflex == 1:
            return True  # already L, no new slot consumed
        # Going rect (or invalid) → L: count other rooms currently L.
        other_l_count = 0
        for idx, ids in rooms_state_before.items():
            if idx == room_idx or not ids:
                continue
            other_theta = regions_by_id[ids[0]].theta
            if _reflex_of_union(ids, regions_by_id, other_theta) == 1:
                other_l_count += 1
        return other_l_count < max_l_rooms

    return gate
