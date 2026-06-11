"""Tests for ``room_layout.stages.atom_graph`` — work item 4.10a / Plan §4.10.

Unit tests on small shapes: AtomGraph structure, edge validity (positive
shared length, valid endpoints, symmetry), exterior contact, neighbors,
empty handling, atoms-param consistency.
"""

from room_layout.schema import FloorShape, ShapePart
from room_layout.stages.atom_graph import AtomEdge, AtomGraph, build_atom_graph
from room_layout.stages.atomize import Atom, atomize


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


def test_atom_graph_edge_atom_ids_ordered_and_valid():
    g = build_atom_graph(_floor(_rect(0, 0, 2, 2)))
    valid_ids = {a.atom_id for a in g.atoms}
    for e in g.edges:
        assert e.atom_a < e.atom_b
        assert e.atom_a in valid_ids and e.atom_b in valid_ids


def test_atom_graph_neighbors_symmetric():
    g = build_atom_graph(_floor(_rect(0, 0, 2, 2)))
    for e in g.edges:
        assert e.atom_b in g.neighbors(e.atom_a)
        assert e.atom_a in g.neighbors(e.atom_b)


def test_atom_graph_neighbors_keyed_by_atom_id_not_index():
    # After sliver absorption atom_id is sparse (id != position in `atoms`).
    # neighbors() must key on atom_id, not the list index. Hand-build a graph
    # with a gap in the ids to lock this in.
    atoms = tuple(
        Atom(
            atom_id=i,
            shape=_rect(0, 0, 1, 1),
            part_id=0,
            piece_id=0,
            theta=0.0,
            is_feature_sliver=False,
        )
        for i in (0, 5, 9)
    )

    def _edge(a: int, b: int) -> AtomEdge:
        return AtomEdge(a, b, 1.0, 1.0, True, 0.0, False, False)

    g = AtomGraph(atoms=atoms, edges=(_edge(0, 5), _edge(5, 9)))
    assert set(g.neighbors(5)) == {0, 9}
    assert g.neighbors(0) == (5,)
    assert g.neighbors(9) == (5,)
    # id 1 is a *position*, not an atom_id here; an index-based lookup would
    # wrongly return atom 5's neighbors.
    assert g.neighbors(1) == ()


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


def test_atom_graph_filters_float_drift_micro_edges():
    """hole 모서리 float drift 의 마이크로(서브-snap) 겹침 변은 인접이 아니다.

    좌표 = ResearchBIM_synthetic-bim 통합 실측 (seed5 atom 96/67, full
    precision): 계단 hole 모서리 y 가 두 계산 경로(snap anchor vs hole ring)로
    1e-7 어긋나, 모서리 점 접촉이어야 할 두 atom 이 x=1.2 선에서 3.17e-7 m
    겹침 변을 가짐. 이전 필터(1e-9 = 수치 0 판정)는 이를 edge 로 만들어
    성장/흡수가 유령 인접으로 오배정 (점-목 거실 팔 — PlanBIM 142 §10).
    geometry_snap 미만 변은 edge 가 아니어야 한다.
    """
    a = Atom(
        atom_id=0,
        shape=ShapePart(exterior=(
            (1.2, 6.045976999999998),
            (1.5499999999999998, 6.045976999999998),
            (1.5499999999999998, 6.345977),
            (1.2, 6.345977),
        )),
        part_id=0, piece_id=0, theta=0.0, is_feature_sliver=False,
    )
    b = Atom(
        atom_id=1,
        shape=ShapePart(exterior=(
            (0.8999999999999999, 6.345976683126426),
            (1.2, 6.345976683126426),
            (1.2, 6.695977),
            (0.8999999999999999, 6.695977),
        )),
        part_id=0, piece_id=0, theta=0.0, is_feature_sliver=False,
    )
    g = build_atom_graph(_floor(_rect(0, 5, 2, 7)), atoms=(a, b))
    assert g.edges == (), (
        f"drift 유령 edge 생성됨: {[(e.atom_a, e.atom_b, e.shared_boundary_length) for e in g.edges]}"
    )
