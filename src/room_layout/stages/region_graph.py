"""Region adjacency graph — Phase 6.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.10 + S03-D13.

Ported from Cell ``region_graph.py`` and adapted to the new schema: the
stage takes a ``FloorShape`` (S03-D13). Algorithm unchanged.

Aggregates the atom adjacency graph up to region granularity: an edge
between two regions accumulates the shared boundary length + contact
flags of every atom-edge that crosses the region boundary.

``build_region_graph`` returns a plain ``RegionGraph`` dataclass (not a
``networkx.Graph``), so it serializes via ``to_dict`` with no adapter.
Per S03-D15 the golden pins only the ``edges`` (the regions are already
covered by ``regionize.json``).

Internal per S03-D6 — not re-exported from the public surface.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from math import hypot

from room_layout.schema import FloorShape
from room_layout.stages._helpers import to_shapely
from room_layout.stages.atom_graph import build_atom_graph
from room_layout.stages.atomize import Atom, atomize
from room_layout.stages.dimensions import DimensionPolicy
from room_layout.stages.regionize import Region, regionize


@dataclass(frozen=True)
class RegionEdge:
    region_a: int
    region_b: int
    shared_boundary_length: float
    centroid_distance: float
    same_theta_group: bool
    exterior_contact: bool
    hole_contact: bool


@dataclass(frozen=True)
class RegionGraph:
    regions: tuple[Region, ...]
    edges: tuple[RegionEdge, ...]
    # built once so neighbors() / edge_between() are O(1) not O(E).
    _adjacency: dict[int, tuple[int, ...]] = field(
        init=False, repr=False, compare=False, default_factory=dict
    )
    _edge_by_pair: dict[tuple[int, int], RegionEdge] = field(
        init=False, repr=False, compare=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        adj: dict[int, list[int]] = {r.region_id: [] for r in self.regions}
        pair: dict[tuple[int, int], RegionEdge] = {}
        for e in self.edges:
            adj.setdefault(e.region_a, []).append(e.region_b)
            adj.setdefault(e.region_b, []).append(e.region_a)
            pair[(e.region_a, e.region_b)] = e  # edges are stored region_a < region_b
        object.__setattr__(self, "_adjacency", {k: tuple(v) for k, v in adj.items()})
        object.__setattr__(self, "_edge_by_pair", pair)

    def neighbors(self, region_id: int) -> tuple[int, ...]:
        """Region ids adjacent to ``region_id`` (empty tuple if id is unknown)."""
        return self._adjacency.get(region_id, ())

    def edge_between(self, region_a: int, region_b: int) -> "RegionEdge | None":
        return self._edge_by_pair.get(tuple(sorted((region_a, region_b))))


@dataclass
class _RegionEdgeAccum:
    shared_boundary_length: float = 0.0
    exterior_contact: bool = False
    hole_contact: bool = False


def build_region_graph(
    floor: FloorShape,
    atoms: tuple[Atom, ...] | None = None,
    regions: tuple[Region, ...] | None = None,
    policy: DimensionPolicy | None = None,
) -> RegionGraph:
    if atoms is None:
        atoms = atomize(floor, policy)
    if regions is None:
        regions = regionize(floor, atoms=atoms, policy=policy)
    if not atoms or not regions:
        return RegionGraph(regions=regions or (), edges=())

    atom_to_region: dict[int, int] = {}
    for region in regions:
        for atom_id in region.atom_ids:
            atom_to_region[atom_id] = region.region_id

    graph = build_atom_graph(floor, atoms=atoms, policy=policy)
    accum: dict[tuple[int, int], _RegionEdgeAccum] = defaultdict(_RegionEdgeAccum)
    for edge in graph.edges:
        region_a = atom_to_region.get(edge.atom_a)
        region_b = atom_to_region.get(edge.atom_b)
        if region_a is None or region_b is None or region_a == region_b:
            continue

        key = tuple(sorted((region_a, region_b)))
        bucket = accum[key]
        bucket.shared_boundary_length += edge.shared_boundary_length
        bucket.exterior_contact = bucket.exterior_contact or edge.exterior_contact
        bucket.hole_contact = bucket.hole_contact or edge.hole_contact
    region_by_id = {r.region_id: r for r in regions}
    region_poly_by_id = {r.region_id: to_shapely(r.shape) for r in regions}
    edges: list[RegionEdge] = []
    for (region_a, region_b), bucket in sorted(accum.items()):
        ra = region_by_id[region_a]
        rb = region_by_id[region_b]
        ca = region_poly_by_id[region_a].centroid
        cb = region_poly_by_id[region_b].centroid
        edges.append(
            RegionEdge(
                region_a=region_a,
                region_b=region_b,
                shared_boundary_length=bucket.shared_boundary_length,
                centroid_distance=hypot(ca.x - cb.x, ca.y - cb.y),
                same_theta_group=abs(ra.theta - rb.theta) < 1e-9,
                exterior_contact=bucket.exterior_contact,
                hole_contact=bucket.hole_contact,
            )
        )

    return RegionGraph(regions=regions, edges=tuple(edges))
