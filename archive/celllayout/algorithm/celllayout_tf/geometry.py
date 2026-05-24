"""Shared Shapely geometry helpers for RoomLayoutCell."""

from __future__ import annotations

from math import degrees

import shapely.affinity as sa
import shapely.geometry as sg
from shapely.geometry.polygon import orient as _orient

from .schema import ShapePart


def to_shapely(part: ShapePart) -> sg.Polygon:
    """Convert a ``ShapePart`` to a Shapely polygon."""
    return sg.Polygon(part.exterior, [list(h) for h in part.holes])


def from_shapely(poly: sg.Polygon) -> ShapePart:
    """Convert a Shapely polygon to a CCW-oriented ``ShapePart``."""
    poly = _orient(poly, sign=1.0)
    ext = tuple(tuple(map(float, p)) for p in list(poly.exterior.coords)[:-1])
    holes = tuple(
        tuple(tuple(map(float, p)) for p in list(ring.coords)[:-1])
        for ring in poly.interiors
    )
    return ShapePart(exterior=ext, holes=holes)


def polygon_parts(geom) -> list[sg.Polygon]:
    """Flatten polygonal geometries into non-empty polygons."""
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


def line_length(geom) -> float:
    """Total length of line components inside a Shapely geometry."""
    if geom.is_empty:
        return 0.0
    if geom.geom_type == "LineString":
        return float(geom.length)
    if geom.geom_type == "MultiLineString":
        return sum(float(g.length) for g in geom.geoms)
    if geom.geom_type == "GeometryCollection":
        return sum(line_length(g) for g in geom.geoms)
    return 0.0


def rotate_radians(geom, theta_rad: float, *, sign: int = 1, origin=(0, 0)):
    """Rotate a Shapely geometry by ``sign * theta_rad`` around ``origin``."""
    if abs(theta_rad) < 1e-12:
        return geom
    return sa.rotate(geom, sign * degrees(theta_rad), origin=origin)
