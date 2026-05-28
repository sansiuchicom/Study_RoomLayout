"""Tests for ``room_layout.stages.region_graph`` — work item 4.10a / Plan §4.10.

Unit tests on small shapes: RegionGraph structure (dataclass, not
networkx), edge metadata, neighbors / edge_between methods, linear-chain
adjacency, empty handling, atoms/regions-param consistency.
"""

from room_layout.schema import FloorShape, ShapePart
from room_layout.stages.atomize import atomize
from room_layout.stages.region_graph import RegionEdge, RegionGraph, build_region_graph
from room_layout.stages.regionize import regionize


def _rect(x0, y0, x1, y1) -> ShapePart:
    return ShapePart(exterior=((x0, y0), (x1, y0), (x1, y1), (x0, y1)))


def _floor(*parts) -> FloorShape:
    return FloorShape(level=1, parts=list(parts), floor_to_floor_height=3.0)


def test_build_region_graph_returns_regiongraph():
    g = build_region_graph(_floor(_rect(0, 0, 6, 2)))
    assert isinstance(g, RegionGraph)
    assert all(isinstance(e, RegionEdge) for e in g.edges)


def test_region_graph_preserves_regions():
    floor = _floor(_rect(0, 0, 6, 2))
    atoms = atomize(floor)
    regions = regionize(floor, atoms=atoms)
    g = build_region_graph(floor, atoms=atoms, regions=regions)
    assert g.regions == regions


def test_region_graph_linear_chain_adjacency():
    # 6x2 → 4 regions side by side → 3 adjacencies (a path)
    g = build_region_graph(_floor(_rect(0, 0, 6, 2)))
    assert len(g.regions) == 4
    assert len(g.edges) == 3


def test_region_graph_edge_metadata_positive():
    g = build_region_graph(_floor(_rect(0, 0, 6, 2)))
    assert g.edges
    for e in g.edges:
        assert e.shared_boundary_length > 0
        assert e.centroid_distance > 0


def test_region_graph_edge_indices_ordered():
    g = build_region_graph(_floor(_rect(0, 0, 6, 2)))
    for e in g.edges:
        assert e.region_a < e.region_b


def test_region_graph_neighbors_and_edge_between():
    g = build_region_graph(_floor(_rect(0, 0, 6, 2)))
    for e in g.edges:
        assert e.region_b in g.neighbors(e.region_a)
        assert g.edge_between(e.region_a, e.region_b) is e
        # order-insensitive lookup
        assert g.edge_between(e.region_b, e.region_a) is e


def test_region_graph_same_theta_within_axis_aligned():
    g = build_region_graph(_floor(_rect(0, 0, 6, 2)))
    assert all(e.same_theta_group for e in g.edges)  # all theta 0


def test_region_graph_edge_between_missing_returns_none():
    g = build_region_graph(_floor(_rect(0, 0, 6, 2)))
    assert g.edge_between(0, 999) is None


def test_region_graph_empty_returns_empty():
    assert build_region_graph(_floor(_rect(0, 0, 2, 2)), atoms=(), regions=()) == RegionGraph(
        (), ()
    )


def test_region_graph_explicit_args_match_internal():
    floor = _floor(_rect(0, 0, 6, 2))
    atoms = atomize(floor)
    regions = regionize(floor, atoms=atoms)
    full = build_region_graph(floor, atoms=atoms, regions=regions)
    assert build_region_graph(floor).edges == full.edges
