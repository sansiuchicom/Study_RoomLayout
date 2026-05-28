"""Tests for ``room_layout.stages.atom_graph`` — work item 4.10a / Plan §4.10.

Unit tests on small shapes: AtomGraph structure, edge validity (positive
shared length, valid endpoints, symmetry), exterior contact, neighbors,
empty handling, atoms-param consistency.
"""

from room_layout.schema import FloorShape, ShapePart
from room_layout.stages.atom_graph import AtomEdge, AtomGraph, build_atom_graph
from room_layout.stages.atomize import atomize


def _rect(x0, y0, x1, y1) -> ShapePart:
    return ShapePart(exterior=((x0, y0), (x1, y0), (x1, y1), (x0, y1)))


def _floor(*parts) -> FloorShape:
    return FloorShape(level=1, parts=list(parts), floor_to_floor_height=3.0)


def test_build_atom_graph_returns_atomgraph():
    g = build_atom_graph(_floor(_rect(0, 0, 1, 1)))
    assert isinstance(g, AtomGraph)
    assert all(isinstance(e, AtomEdge) for e in g.edges)


def test_atom_graph_preserves_atoms():
    floor = _floor(_rect(0, 0, 1, 1))
    atoms = atomize(floor)
    g = build_atom_graph(floor, atoms=atoms)
    assert g.atoms == atoms


def test_atom_graph_3x3_grid_has_12_edges():
    # 1x1 → split_interval(1.0) = [0.35, 0.30, 0.35] → clean 3x3 grid.
    # Horizontal adjacencies: 2 gaps x 3 rows = 6; vertical: 6 → 12 edges.
    g = build_atom_graph(_floor(_rect(0, 0, 1, 1)))
    assert len(g.atoms) == 9
    assert len(g.edges) == 12


def test_atom_graph_edges_have_positive_shared_length():
    g = build_atom_graph(_floor(_rect(0, 0, 2, 2)))
    assert g.edges
    assert all(e.shared_boundary_length > 0 for e in g.edges)


def test_atom_graph_edge_indices_ordered_and_valid():
    g = build_atom_graph(_floor(_rect(0, 0, 2, 2)))
    n = len(g.atoms)
    for e in g.edges:
        assert 0 <= e.atom_a < e.atom_b < n


def test_atom_graph_neighbors_symmetric():
    g = build_atom_graph(_floor(_rect(0, 0, 2, 2)))
    for e in g.edges:
        assert e.atom_b in g.neighbors(e.atom_a)
        assert e.atom_a in g.neighbors(e.atom_b)


def test_atom_graph_has_exterior_contact_edges():
    # every atom of a plain rect touches the footprint exterior somewhere
    g = build_atom_graph(_floor(_rect(0, 0, 2, 2)))
    assert any(e.exterior_contact for e in g.edges)


def test_atom_graph_same_part_within_single_part():
    g = build_atom_graph(_floor(_rect(0, 0, 2, 2)))
    assert all(e.same_part for e in g.edges)  # single part → all same_part


def test_atom_graph_empty_atoms_returns_empty():
    assert build_atom_graph(_floor(_rect(0, 0, 1, 1)), atoms=()) == AtomGraph((), ())


def test_atom_graph_explicit_atoms_match_internal():
    floor = _floor(_rect(0, 0, 2, 2))
    assert build_atom_graph(floor) == build_atom_graph(floor, atoms=atomize(floor))
