"""Shared geometry helpers for the atomic subdivision testfield."""

from __future__ import annotations

from collections.abc import Iterable

import shapely
import shapely.geometry as sg


def snap(geom, precision: float):
    """Snap a geometry to the shared precision grid."""
    return shapely.set_precision(geom, precision)


def polygon_parts(geom) -> list[sg.Polygon]:
    """Return polygon parts from Polygon/MultiPolygon/GeometryCollection input."""
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


def polygon_boundary_lines(poly: sg.Polygon) -> list:
    """Return exterior and hole rings as linework."""
    lines = [sg.LineString(poly.exterior.coords)]
    lines.extend(sg.LineString(ring.coords) for ring in poly.interiors)
    return lines


def iter_linework(geoms: Iterable) -> list:
    """Flatten line-like geometry collections into a list of geometries."""
    out = []
    for geom in geoms:
        if geom is None or geom.is_empty:
            continue
        if isinstance(geom, (sg.LineString, sg.LinearRing, sg.MultiLineString)):
            out.append(geom)
        elif hasattr(geom, "geoms"):
            out.extend(iter_linework(geom.geoms))
    return out
