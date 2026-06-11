"""Atom adjacency graph — Phase 4 (region_graph dependency).

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.10 + S03-D13.

Ported from Cell ``atom_graph.py`` and adapted to the new schema: the
stage takes a ``FloorShape`` (S03-D13). Algorithm unchanged.

Nodes are atoms. Two atoms are connected by an edge when their polygons
share a boundary segment of positive length (point-only contact is not
an edge).

Each edge carries metadata for downstream phases (regionizer, corridor
router):

    shared_boundary_length  length of the shared boundary segment(s)
    centroid_distance       Euclidean distance between atom centroids
    same_part               True iff both atoms come from the same part + piece
    theta_diff              orientation difference (radians, mod π/2)
    exterior_contact        True iff *at least one endpoint* of the shared
                            boundary lies on the footprint exterior ring. This
                            means the shared edge is anchored to the outer wall
                            at a point — it does NOT mean the edge runs along
                            the wall (an atom-atom edge is always interior). A
                            single touch is enough, and ``region_graph`` OR-
                            aggregates it across all atom-edges of a region
                            pair, so the flag fires broadly. Downstream
                            consumers (Step 04 corridor) must confirm this
                            "endpoint-anchored" meaning is what they want before
                            treating it as "adjacent to the exterior wall".
    hole_contact            same test against a footprint hole ring.

Internal per S03-D6 — consumed by ``region_graph`` (and Phase 8 corridor
in Step 04); not re-exported from the public surface.
"""

from dataclasses import dataclass, field
from math import hypot, pi

import shapely.geometry as sg
from shapely.ops import unary_union
from shapely.strtree import STRtree

from room_layout.schema import FloorShape
from room_layout.stages._helpers import line_length, polygon_parts, to_shapely
from room_layout.stages.atomize import Atom, atomize
from room_layout.stages.dimensions import DimensionPolicy

CONTACT_TOL = 1e-6


@dataclass(frozen=True)
class AtomEdge:
    # atom_a / atom_b are ``Atom.atom_id`` values (NOT positional indices into
    # ``AtomGraph.atoms``); ids are sparse after sliver absorption. atom_a < atom_b.
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
    # atom_id -> adjacent atom_ids, built once so neighbors() is O(1) not O(E).
    _adjacency: dict[int, tuple[int, ...]] = field(
        init=False, repr=False, compare=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        adj: dict[int, list[int]] = {a.atom_id: [] for a in self.atoms}
        for e in self.edges:
            adj[e.atom_a].append(e.atom_b)
            adj[e.atom_b].append(e.atom_a)
        object.__setattr__(self, "_adjacency", {k: tuple(v) for k, v in adj.items()})

    def neighbors(self, atom_id: int) -> tuple[int, ...]:
        """Atom ids adjacent to ``atom_id`` (empty tuple if id is unknown)."""
        return self._adjacency.get(atom_id, ())


def build_atom_graph(
    floor: FloorShape,
    atoms: tuple[Atom, ...] | None = None,
    policy: DimensionPolicy | None = None,
) -> AtomGraph:
    if atoms is None:
        atoms = atomize(floor, policy)
    if not atoms:
        return AtomGraph(atoms=(), edges=())

    polys = [to_shapely(a.shape) for a in atoms]
    tree = STRtree(polys)

    # 인접 = 물리적으로 의미 있는 공유변. geometry_snap(0.01m) 미만은 float
    # drift 유령 — hole 모서리 좌표가 두 계산 경로(snap anchor vs hole ring)로
    # ~1e-7 어긋나면 점 접촉이어야 할 atom 쌍이 마이크로 겹침 변을 가짐
    # (ResearchBIM 통합 실측: 유령 17개 전부 ≤4.4e-7 m vs 정상 edge ≥0.15 m —
    # 7자릿수 dead zone). 이전 1e-9 는 수치 0 판정일 뿐 의미 필터가 아니었음.
    min_edge_length = (policy or DimensionPolicy()).geometry_snap

    footprint = unary_union(
        [sg.Polygon(p.exterior, [list(h) for h in p.holes]) for p in floor.parts]
    )
    exterior_lines = _outline_lines(footprint, ring="exterior")
    hole_lines = _outline_lines(footprint, ring="interior")

    edges: list[AtomEdge] = []
    seen: set[tuple[int, int]] = set()
    for i, poly_i in enumerate(polys):
        candidates = tree.query(poly_i.buffer(CONTACT_TOL))
        for j in candidates:
            j = int(j)
            if j <= i:
                continue
            key = (i, j)
            if key in seen:
                continue
            seen.add(key)

            poly_j = polys[j]
            shared = _shared_boundary_geom(poly_i, poly_j)
            length = line_length(shared)
            if length < min_edge_length:
                continue

            ca = atoms[i].centroid
            cb = atoms[j].centroid
            cd = hypot(ca[0] - cb[0], ca[1] - cb[1])

            same_part = (
                atoms[i].part_id == atoms[j].part_id and atoms[i].piece_id == atoms[j].piece_id
            )
            theta_diff = _angle_diff_mod_half_pi(atoms[i].theta, atoms[j].theta)

            endpoints = _line_endpoints(shared)
            ext_contact = _any_endpoint_on_lines(endpoints, exterior_lines)
            hole_contact = _any_endpoint_on_lines(endpoints, hole_lines)

            a_id, b_id = sorted((atoms[i].atom_id, atoms[j].atom_id))
            edges.append(
                AtomEdge(
                    atom_a=a_id,
                    atom_b=b_id,
                    shared_boundary_length=length,
                    centroid_distance=cd,
                    same_part=same_part,
                    theta_diff=theta_diff,
                    exterior_contact=ext_contact,
                    hole_contact=hole_contact,
                )
            )

    return AtomGraph(atoms=atoms, edges=tuple(edges))


def _shared_boundary_geom(poly_a, poly_b):
    """Return exact or tolerance-recovered shared boundary geometry.

    Rotated parts that should share a boundary can land a few
    floating-point ulps apart after separate affine transforms. Exact
    polygon intersection then returns no line contact, which would
    disconnect the graph. The fallback keeps only boundary portions whose
    length is much larger than the tolerance, so point-only contacts
    still stay out of the graph.
    """
    exact = poly_a.intersection(poly_b)
    if line_length(exact) > 1e-9:
        return exact
    if poly_a.distance(poly_b) > CONTACT_TOL:
        return exact

    approx = poly_a.boundary.intersection(
        poly_b.boundary.buffer(CONTACT_TOL, cap_style=2, join_style=2)
    )
    if line_length(approx) > CONTACT_TOL * 10:
        return approx
    return exact


def _outline_lines(footprint, *, ring: str) -> list[sg.LineString]:
    out: list[sg.LineString] = []
    for poly in polygon_parts(footprint):
        rings = [poly.exterior] if ring == "exterior" else list(poly.interiors)
        for r in rings:
            if r is None or r.is_empty:
                continue
            out.append(sg.LineString(r.coords))
    return out


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
