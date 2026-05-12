"""Overlap resolution: turn input ``ShapePart`` list into disjoint territories.

Rule: when two parts overlap, count each part's exterior vertices that are
strictly inside the other. The part with FEWER intruding vertices is the host
and keeps its full polygon; the other part loses the overlap zone.

Tiebreakers (in order):
    1. axis-aligned > rotated > curved
    2. larger area
    3. earlier in parts list
"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, hypot, pi, sin

import shapely.geometry as sg
from shapely.geometry.polygon import orient as _orient
from shapely.ops import unary_union

from .schema import ShapeInput, ShapePart, part_theta


KIND_AXIS_ALIGNED = "axis_aligned"
KIND_ROTATED = "rotated"
KIND_CURVED = "curved"
_KIND_ORDER = {KIND_AXIS_ALIGNED: 0, KIND_ROTATED: 1, KIND_CURVED: 2}


@dataclass(frozen=True)
class Territory:
    part_id: int
    theta: float
    kind: str
    pieces: tuple[ShapePart, ...]

    @property
    def is_empty(self) -> bool:
        return len(self.pieces) == 0


def part_kind(part: ShapePart) -> str:
    """Classify a part by edge-angle consistency."""
    theta = part_theta(part)
    verts = part.exterior
    n = len(verts)
    aligned = 0
    total = 0
    eps_angle = 1e-3
    for i in range(n):
        x0, y0 = verts[i]
        x1, y1 = verts[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        if hypot(dx, dy) < 1e-9:
            continue
        edge_theta = atan2(dy, dx) % (pi / 2)
        if _angle_diff_mod_half_pi(edge_theta, theta) < eps_angle:
            aligned += 1
        total += 1
    if total == 0 or aligned / total < 0.95:
        return KIND_CURVED
    if abs(theta) < eps_angle or abs(theta - pi / 2) < eps_angle:
        return KIND_AXIS_ALIGNED
    return KIND_ROTATED


def resolve_territories(shape: ShapeInput) -> tuple[Territory, ...]:
    """Return one ``Territory`` per input part, with overlap zones removed."""
    parts = shape.parts
    polys = [_to_shapely(p) for p in parts]
    kinds = [part_kind(p) for p in parts]
    thetas = [part_theta(p) for p in parts]

    territories = list(polys)

    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            if not polys[i].intersects(polys[j]):
                continue
            inter = polys[i].intersection(polys[j])
            if inter.is_empty or inter.area < 1e-9:
                continue
            winner = _pair_winner(i, j, parts, polys, kinds)
            loser = j if winner == i else i
            territories[loser] = territories[loser].difference(polys[winner])

    out = []
    for idx, geom in enumerate(territories):
        pieces = tuple(_from_shapely(p) for p in _polygon_parts(geom))
        out.append(
            Territory(
                part_id=idx,
                theta=thetas[idx],
                kind=kinds[idx],
                pieces=pieces,
            )
        )
    return tuple(out)


def _pair_winner(
    i: int,
    j: int,
    parts: tuple[ShapePart, ...],
    polys: list,
    kinds: list[str],
) -> int:
    count_i_in_j = _count_exterior_vertices_inside(parts[i], polys[j])
    count_j_in_i = _count_exterior_vertices_inside(parts[j], polys[i])

    if count_i_in_j < count_j_in_i:
        return i
    if count_i_in_j > count_j_in_i:
        return j

    rank_i = _KIND_ORDER[kinds[i]]
    rank_j = _KIND_ORDER[kinds[j]]
    if rank_i < rank_j:
        return i
    if rank_i > rank_j:
        return j

    if polys[i].area > polys[j].area:
        return i
    if polys[i].area < polys[j].area:
        return j

    return i


def _count_exterior_vertices_inside(part: ShapePart, host_polygon) -> int:
    count = 0
    for x, y in part.exterior:
        if host_polygon.contains(sg.Point(x, y)):
            count += 1
    return count


def _angle_diff_mod_half_pi(a: float, b: float) -> float:
    d = abs((a - b) % (pi / 2))
    return min(d, pi / 2 - d)


def _to_shapely(part: ShapePart) -> sg.Polygon:
    return sg.Polygon(part.exterior, [list(h) for h in part.holes])


def _from_shapely(poly) -> ShapePart:
    poly = _orient(poly, sign=1.0)
    ext = tuple(tuple(map(float, p)) for p in list(poly.exterior.coords)[:-1])
    holes = tuple(
        tuple(tuple(map(float, p)) for p in list(ring.coords)[:-1])
        for ring in poly.interiors
    )
    return ShapePart(exterior=ext, holes=holes)


def _polygon_parts(geom) -> list:
    if geom.is_empty:
        return []
    if isinstance(geom, sg.Polygon):
        return [geom]
    if isinstance(geom, sg.MultiPolygon):
        return [p for p in geom.geoms if isinstance(p, sg.Polygon) and not p.is_empty]
    if hasattr(geom, "geoms"):
        out = []
        for part in geom.geoms:
            out.extend(_polygon_parts(part))
        return out
    return []
