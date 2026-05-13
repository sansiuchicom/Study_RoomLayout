"""Region adjacency graph.

Nodes are regions. Two regions are connected by an edge when at least one
atom-edge crosses from one region into the other. Region-edge metadata is
aggregated from the underlying atom contacts and recomputed geometry.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from math import atan2, cos, hypot, pi, sin

import shapely.geometry as sg

from .atom_graph import _shared_boundary_geom, build_atom_graph
from .atomize import Atom, atomize
from .dimensions import DimensionPolicy
from .regionize import Region, regionize
from .schema import ShapeInput, ShapePart


ANGLE_TOL = pi / 180.0
LINE_TOL = 1e-6
CONTIGUITY_TOL = 1e-6


@dataclass(frozen=True)
class RegionEdge:
    region_a: int
    region_b: int
    shared_boundary_length: float
    door_capable_length: float
    centroid_distance: float
    same_theta_group: bool
    exterior_contact: bool
    hole_contact: bool


@dataclass(frozen=True)
class RegionGraph:
    regions: tuple[Region, ...]
    edges: tuple[RegionEdge, ...]

    def neighbors(self, region_id: int) -> tuple[int, ...]:
        out: list[int] = []
        for e in self.edges:
            if e.region_a == region_id:
                out.append(e.region_b)
            elif e.region_b == region_id:
                out.append(e.region_a)
        return tuple(out)

    def edge_between(self, region_a: int, region_b: int) -> RegionEdge | None:
        a, b = sorted((region_a, region_b))
        for e in self.edges:
            if e.region_a == a and e.region_b == b:
                return e
        return None


@dataclass
class _RegionEdgeAccum:
    shared_boundary_length: float = 0.0
    exterior_contact: bool = False
    hole_contact: bool = False
    segments: list[sg.LineString] = field(default_factory=list)


def build_region_graph(
    shape: ShapeInput,
    atoms: tuple[Atom, ...] | None = None,
    regions: tuple[Region, ...] | None = None,
    policy: DimensionPolicy | None = None,
) -> RegionGraph:
    if atoms is None:
        atoms = atomize(shape, policy)
    if regions is None:
        regions = regionize(shape, atoms=atoms, policy=policy)
    if not atoms or not regions:
        return RegionGraph(regions=regions or (), edges=())

    atom_to_region: dict[int, int] = {}
    for region in regions:
        for atom_id in region.atom_ids:
            atom_to_region[atom_id] = region.region_id

    graph = build_atom_graph(shape, atoms=atoms, policy=policy)
    atom_polys = [_to_shapely(a.shape) for a in graph.atoms]

    accum: dict[tuple[int, int], _RegionEdgeAccum] = defaultdict(_RegionEdgeAccum)
    for edge in graph.edges:
        atom_a = graph.atoms[edge.atom_a]
        atom_b = graph.atoms[edge.atom_b]
        region_a = atom_to_region.get(atom_a.atom_id)
        region_b = atom_to_region.get(atom_b.atom_id)
        if region_a is None or region_b is None or region_a == region_b:
            continue

        key = tuple(sorted((region_a, region_b)))
        bucket = accum[key]
        bucket.shared_boundary_length += edge.shared_boundary_length
        bucket.exterior_contact = bucket.exterior_contact or edge.exterior_contact
        bucket.hole_contact = bucket.hole_contact or edge.hole_contact
        shared = _shared_boundary_geom(
            atom_polys[edge.atom_a],
            atom_polys[edge.atom_b],
        )
        bucket.segments.extend(_line_segments(shared))

    region_by_id = {r.region_id: r for r in regions}
    region_poly_by_id = {r.region_id: _to_shapely(r.shape) for r in regions}
    edges: list[RegionEdge] = []
    for (region_a, region_b), bucket in sorted(accum.items()):
        ra = region_by_id[region_a]
        rb = region_by_id[region_b]
        ca = region_poly_by_id[region_a].centroid
        cb = region_poly_by_id[region_b].centroid
        door_capable_length = min(
            _door_capable_length(bucket.segments),
            bucket.shared_boundary_length,
        )
        edges.append(
            RegionEdge(
                region_a=region_a,
                region_b=region_b,
                shared_boundary_length=bucket.shared_boundary_length,
                door_capable_length=door_capable_length,
                centroid_distance=hypot(ca.x - cb.x, ca.y - cb.y),
                same_theta_group=abs(ra.theta - rb.theta) < 1e-9,
                exterior_contact=bucket.exterior_contact,
                hole_contact=bucket.hole_contact,
            )
        )

    return RegionGraph(regions=regions, edges=tuple(edges))


def _door_capable_length(segments: list[sg.LineString]) -> float:
    """Return the longest contiguous straight shared-boundary run.

    Segment direction is grouped with a 1 degree tolerance. Collinearity and
    endpoint contiguity use metric tolerances because testfield coordinates are
    already clean meter values.
    """
    intervals_by_line: dict[
        tuple[int, int],
        list[tuple[float, float]],
    ] = defaultdict(list)
    for segment in segments:
        coords = list(segment.coords)
        if len(coords) < 2:
            continue
        x0, y0 = coords[0]
        x1, y1 = coords[-1]
        dx, dy = x1 - x0, y1 - y0
        length = hypot(dx, dy)
        if length < LINE_TOL:
            continue

        angle = atan2(dy, dx) % pi
        if angle >= pi - ANGLE_TOL:
            angle = 0.0
        angle_key = int(round(angle / ANGLE_TOL))
        angle_ref = angle_key * ANGLE_TOL
        ux, uy = cos(angle_ref), sin(angle_ref)
        offset = -uy * x0 + ux * y0
        offset_key = int(round(offset / LINE_TOL))
        t0 = ux * x0 + uy * y0
        t1 = ux * x1 + uy * y1
        lo, hi = sorted((t0, t1))
        intervals_by_line[(angle_key, offset_key)].append((lo, hi))

    longest = 0.0
    for intervals in intervals_by_line.values():
        intervals.sort()
        cur_lo, cur_hi = intervals[0]
        for lo, hi in intervals[1:]:
            if lo <= cur_hi + CONTIGUITY_TOL:
                cur_hi = max(cur_hi, hi)
            else:
                longest = max(longest, cur_hi - cur_lo)
                cur_lo, cur_hi = lo, hi
        longest = max(longest, cur_hi - cur_lo)
    return float(longest)


def _line_segments(geom) -> list[sg.LineString]:
    if geom.is_empty:
        return []
    if geom.geom_type == "LineString":
        return [geom] if geom.length > LINE_TOL else []
    if geom.geom_type == "MultiLineString":
        out: list[sg.LineString] = []
        for g in geom.geoms:
            out.extend(_line_segments(g))
        return out
    if geom.geom_type == "GeometryCollection":
        out = []
        for g in geom.geoms:
            out.extend(_line_segments(g))
        return out
    return []


def _to_shapely(part: ShapePart) -> sg.Polygon:
    return sg.Polygon(part.exterior, [list(h) for h in part.holes])
