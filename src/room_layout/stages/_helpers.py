"""Stage geometry utilities — shapely bridges + orientation inference.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.5.

Ported from Cell ``geometry.py`` (+ ``part_theta`` from Cell ``schema.py``)
and adapted to the new ``room_layout.schema.ShapePart``. Phase 3–5 modules
(atomize / regionize / territory / region_graph / shape_gate) use all six:

    to_shapely      ShapePart → shapely Polygon
    from_shapely    shapely Polygon → ShapePart (CCW-oriented)
    polygon_parts   flatten Multi* / GeometryCollection → list[Polygon]
    line_length     total length of line components in a geometry
    rotate_radians  rotate a geometry by radians (no-op below 1e-12)
    part_theta      infer a part's orientation from its first real edge

`part_theta` lives here rather than in ``room_layout.schema`` (where Cell
kept it) per Pipeline §2.1 — orientation is an *algorithm-inferred*
quantity, not part of the D001 data contract — and S03-D6 (stage
internals are not re-exported from the public surface).
"""

from math import atan2, degrees, hypot, pi

import shapely.affinity as sa
import shapely.geometry as sg
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient

from room_layout.schema import ShapePart


def to_shapely(part: ShapePart) -> sg.Polygon:
    """Convert a ``ShapePart`` to a shapely ``Polygon``."""
    return sg.Polygon(part.exterior, [list(h) for h in part.holes])


def from_shapely(poly: sg.Polygon) -> ShapePart:
    """Convert a shapely ``Polygon`` to a CCW-oriented ``ShapePart``.

    Forces exterior CCW + holes CW via ``shapely.geometry.polygon.orient``
    (matching the new ``ShapePart`` convention) and strips shapely's
    closing duplicate point. Degenerate / self-intersecting polygons are
    rejected by ``ShapePart.__post_init__`` — a deliberate tightening over
    Cell's lax schema (catches bad atoms at the boundary).
    """
    poly = orient(poly, sign=1.0)
    exterior = tuple(tuple(map(float, p)) for p in list(poly.exterior.coords)[:-1])
    holes = tuple(
        tuple(tuple(map(float, p)) for p in list(ring.coords)[:-1]) for ring in poly.interiors
    )
    return ShapePart(exterior=exterior, holes=holes)


def polygon_parts(geom: BaseGeometry) -> list[sg.Polygon]:
    """Flatten any polygonal geometry into a list of non-empty polygons."""
    if geom.is_empty:
        return []
    if isinstance(geom, sg.Polygon):
        return [geom]
    if isinstance(geom, sg.MultiPolygon):
        return [p for p in geom.geoms if isinstance(p, sg.Polygon) and not p.is_empty]
    if hasattr(geom, "geoms"):
        out: list[sg.Polygon] = []
        for part in geom.geoms:
            out.extend(polygon_parts(part))
        return out
    return []


def line_length(geom: BaseGeometry) -> float:
    """Total length of the line components inside a shapely geometry."""
    if geom.is_empty:
        return 0.0
    if geom.geom_type == "LineString":
        return float(geom.length)
    if geom.geom_type == "MultiLineString":
        return sum(float(g.length) for g in geom.geoms)
    if geom.geom_type == "GeometryCollection":
        return sum(line_length(g) for g in geom.geoms)
    return 0.0


def rotate_radians(
    geom: BaseGeometry,
    theta_rad: float,
    *,
    sign: int = 1,
    origin: tuple[float, float] | str = (0, 0),
) -> BaseGeometry:
    """Rotate ``geom`` by ``sign * theta_rad`` (radians) about ``origin``.

    No-op (returns the input unchanged) for rotations below 1e-12 rad, so
    axis-aligned parts skip the shapely round-trip.
    """
    if abs(theta_rad) < 1e-12:
        return geom
    return sa.rotate(geom, sign * degrees(theta_rad), origin=origin)


def part_theta(part: ShapePart) -> float:
    """Return the part's orientation in radians on ``[0, pi/2)``.

    Reads ``atan2`` of the first non-degenerate exterior edge. Exact for
    axis-aligned or straight-edged parts. For curved parts (high-vertex
    disks / ellipses) the first edge is the tangent at the first vertex —
    treat the result as approximate.
    """
    verts = part.exterior
    n = len(verts)
    for i in range(n):
        x0, y0 = verts[i]
        x1, y1 = verts[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        if hypot(dx, dy) > 1e-9:
            return float(atan2(dy, dx) % (pi / 2))
    return 0.0
