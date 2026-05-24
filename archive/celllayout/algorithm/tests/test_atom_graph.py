import math
from collections import deque

from celllayout_tf.atom_graph import AtomGraph, build_atom_graph
from celllayout_tf.cases import selected_cases
from celllayout_tf.schema import ShapeInput, ShapePart


def _connected_component(graph: AtomGraph, start: int) -> set[int]:
    visited = {start}
    queue = deque([start])
    while queue:
        n = queue.popleft()
        for nb in graph.neighbors(n):
            if nb not in visited:
                visited.add(nb)
                queue.append(nb)
    return visited


def test_simple_rect_graph_is_fully_connected():
    shape = ShapeInput(
        "rect",
        (ShapePart(exterior=((0, 0), (12, 0), (12, 8), (0, 8))),),
    )
    graph = build_atom_graph(shape)

    assert len(graph.atoms) > 0
    component = _connected_component(graph, 0)
    assert len(component) == len(graph.atoms)


def test_edges_are_unique_and_ordered():
    case = selected_cases([9])[0][2]  # ㄱ자 standard
    graph = build_atom_graph(case)

    seen = set()
    for e in graph.edges:
        assert e.atom_a < e.atom_b
        key = (e.atom_a, e.atom_b)
        assert key not in seen
        seen.add(key)


def test_shared_boundary_lengths_are_positive():
    case = selected_cases([1])[0][2]
    graph = build_atom_graph(case)
    assert graph.edges
    for e in graph.edges:
        assert e.shared_boundary_length > 0


def test_total_neighbor_count_equals_2x_edges():
    case = selected_cases([1])[0][2]
    graph = build_atom_graph(case)
    total = sum(len(graph.neighbors(i)) for i in range(len(graph.atoms)))
    assert total == 2 * len(graph.edges)


def test_hole_separated_atoms_are_not_connected_across_the_hole():
    # ㅁ small hole: hole is [4.5, 3]–[8.5, 6.5]. An atom on the left of the
    # hole and one on the right at the same y should not be directly adjacent.
    case = selected_cases([16])[0][2]
    graph = build_atom_graph(case)

    left_idx = right_idx = None
    for i, a in enumerate(graph.atoms):
        cx, cy = a.centroid
        if 4.5 <= cy <= 5.0:
            if 4.0 <= cx < 4.5 and left_idx is None:
                left_idx = i
            elif 8.5 < cx <= 9.0 and right_idx is None:
                right_idx = i
    assert left_idx is not None
    assert right_idx is not None
    assert right_idx not in graph.neighbors(left_idx)


def test_case_33_has_cross_part_edges_between_m_and_wing():
    case = selected_cases([33])[0][2]
    graph = build_atom_graph(case)
    cross = [e for e in graph.edges if not e.same_part]
    assert cross, "expected cross-part edges between ㅁ and wing"
    for e in cross:
        pa = graph.atoms[e.atom_a].part_id
        pb = graph.atoms[e.atom_b].part_id
        assert {pa, pb} == {0, 1}


def test_case_13_disjoint_pieces_of_same_part_are_not_connected():
    case = selected_cases([13])[0][2]
    graph = build_atom_graph(case)
    for e in graph.edges:
        a = graph.atoms[e.atom_a]
        b = graph.atoms[e.atom_b]
        if a.part_id == b.part_id and a.piece_id != b.piece_id:
            raise AssertionError(
                f"unexpected edge across disjoint pieces of part {a.part_id}"
            )


def test_rotated_same_theta_parts_keep_cross_part_edges():
    case = selected_cases([20])[0][2]  # ㄱ자 rotated 30°
    graph = build_atom_graph(case)
    cross = [e for e in graph.edges if not e.same_part]
    assert cross
    assert all(e.shared_boundary_length > 0.05 for e in cross)


def test_exterior_contact_flag_set_for_atoms_on_outer_wall():
    case = selected_cases([1])[0][2]
    graph = build_atom_graph(case)
    # at least one edge should have an endpoint on the outer wall
    assert any(e.exterior_contact for e in graph.edges)


def test_hole_contact_flag_set_for_atoms_around_hole():
    case = selected_cases([16])[0][2]
    graph = build_atom_graph(case)
    assert any(e.hole_contact for e in graph.edges)


def test_case_22_main_atoms_form_connected_grid_within_main():
    case = selected_cases([22])[0][2]
    graph = build_atom_graph(case)
    main_atoms = [i for i, a in enumerate(graph.atoms) if a.part_id == 0]
    assert main_atoms
    # BFS restricted to same-part edges
    visited = {main_atoms[0]}
    queue = deque([main_atoms[0]])
    main_set = set(main_atoms)
    while queue:
        n = queue.popleft()
        for e in graph.edges:
            if e.atom_a == n and e.atom_b in main_set and e.atom_b not in visited:
                visited.add(e.atom_b)
                queue.append(e.atom_b)
            elif e.atom_b == n and e.atom_a in main_set and e.atom_a not in visited:
                visited.add(e.atom_a)
                queue.append(e.atom_a)
    assert visited == main_set
