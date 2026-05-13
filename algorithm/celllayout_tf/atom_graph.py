"""Atom adjacency graph.

Nodes are atoms. Two atoms are connected by an edge when their polygons share
a boundary segment of positive length (point-only contact is not an edge).

Each edge carries metadata for downstream phases (regionizer, corridor router):

    shared_boundary_length  length of the shared boundary segment(s)
    centroid_distance       Euclidean distance between atom centroids
    same_part               True iff both atoms come from the same part and piece
    theta_diff              orientation difference (radians, mod π/2)
    exterior_contact        True iff the shared boundary endpoints lie on the
                            footprint exterior (this edge runs along the outer
                            wall of the building)
    hole_contact            True iff the shared boundary endpoints lie on a
                            footprint hole boundary
"""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot, pi

import shapely.geometry as sg
from shapely.ops import unary_union
from shapely.strtree import STRtree

from .atomize import Atom, atomize
from .dimensions import DimensionPolicy
from .schema import ShapeInput, ShapePart


@dataclass(frozen=True)
class AtomEdge:
    atom_a: int
    atom_b: int
    shared_boundary_length: float
    centroid_distance: float
    same_part: bool
    theta_diff: float
    exterior_contact: bool
    hole_contact: bool


@dataclass(frozen=True)
class AtomGraph:
    atoms: tuple[Atom, ...]
    edges: tuple[AtomEdge, ...]

    def neighbors(self, atom_id: int) -> tuple[int, ...]:
        out: list[int] = []
        for e in self.edges:
            if e.atom_a == atom_id:
                out.append(e.atom_b)
            elif e.atom_b == atom_id:
                out.append(e.atom_a)
        return tuple(out)


def build_atom_graph(
    shape: ShapeInput,
    atoms: tuple[Atom, ...] | None = None,
    policy: DimensionPolicy | None = None,
) -> AtomGraph:
    if atoms is None:
        atoms = atomize(shape, policy)
    if not atoms:
        return AtomGraph(atoms=(), edges=())

    polys = [_to_shapely(a.shape) for a in atoms]
    tree = STRtree(polys)

    footprint = unary_union(
        [
            sg.Polygon(p.exterior, [list(h) for h in p.holes])
            for p in shape.parts
        ]
    )
    exterior_lines = _outline_lines(footprint, ring="exterior")
    hole_lines = _outline_lines(footprint, ring="interior")

    edges: list[AtomEdge] = []
    seen: set[tuple[int, int]] = set()
    for i, poly_i in enumerate(polys):
        candidates = tree.query(poly_i)
        for j in candidates:
            j = int(j)
            if j <= i:
                continue
            key = (i, j)
            if key in seen:
                continue
            seen.add(key)

            poly_j = polys[j]
            shared = poly_i.intersection(poly_j)
            length = _line_length(shared)
            if length < 1e-9:
                continue

            ca = atoms[i].centroid
            cb = atoms[j].centroid
            cd = hypot(ca[0] - cb[0], ca[1] - cb[1])

            same_part = (
                atoms[i].part_id == atoms[j].part_id
                and atoms[i].piece_id == atoms[j].piece_id
            )
            theta_diff = _angle_diff_mod_half_pi(atoms[i].theta, atoms[j].theta)

            endpoints = _line_endpoints(shared)
            ext_contact = _any_endpoint_on_lines(endpoints, exterior_lines)
            hole_contact = _any_endpoint_on_lines(endpoints, hole_lines)

            edges.append(
                AtomEdge(
                    atom_a=i,
                    atom_b=j,
                    shared_boundary_length=length,
                    centroid_distance=cd,
                    same_part=same_part,
                    theta_diff=theta_diff,
                    exterior_contact=ext_contact,
                    hole_contact=hole_contact,
                )
            )

    return AtomGraph(atoms=atoms, edges=tuple(edges))


def _outline_lines(footprint, *, ring: str) -> list[sg.LineString]:
    out: list[sg.LineString] = []
    for poly in _polygon_parts(footprint):
        rings = [poly.exterior] if ring == "exterior" else list(poly.interiors)
        for r in rings:
            if r is None or r.is_empty:
                continue
            out.append(sg.LineString(r.coords))
    return out


def _line_length(geom) -> float:
    if geom.is_empty:
        return 0.0
    if geom.geom_type == "LineString":
        return float(geom.length)
    if geom.geom_type == "MultiLineString":
        return sum(float(g.length) for g in geom.geoms)
    if geom.geom_type == "GeometryCollection":
        total = 0.0
        for g in geom.geoms:
            total += _line_length(g)
        return total
    return 0.0


def _line_endpoints(geom) -> list[sg.Point]:
    if geom.is_empty:
        return []
    if geom.geom_type == "LineString":
        coords = list(geom.coords)
        return [sg.Point(coords[0]), sg.Point(coords[-1])]
    if geom.geom_type == "MultiLineString":
        out: list[sg.Point] = []
        for ls in geom.geoms:
            coords = list(ls.coords)
            out.append(sg.Point(coords[0]))
            out.append(sg.Point(coords[-1]))
        return out
    if geom.geom_type == "GeometryCollection":
        out = []
        for g in geom.geoms:
            out.extend(_line_endpoints(g))
        return out
    return []


def _any_endpoint_on_lines(endpoints, lines, tol: float = 1e-6) -> bool:
    if not endpoints or not lines:
        return False
    for p in endpoints:
        for ln in lines:
            if ln.distance(p) < tol:
                return True
    return False


def _angle_diff_mod_half_pi(a: float, b: float) -> float:
    d = abs((a - b) % (pi / 2))
    return min(d, pi / 2 - d)


def _to_shapely(part: ShapePart) -> sg.Polygon:
    return sg.Polygon(part.exterior, [list(h) for h in part.holes])


def _polygon_parts(geom) -> list:
    if geom.is_empty:
        return []
    if isinstance(geom, sg.Polygon):
        return [geom]
    if isinstance(geom, sg.MultiPolygon):
        return list(geom.geoms)
    if hasattr(geom, "geoms"):
        out = []
        for part in geom.geoms:
            out.extend(_polygon_parts(part))
        return out
    return []
