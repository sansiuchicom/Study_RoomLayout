from collections import deque

import shapely.geometry as sg

from celllayout_tf.cases import selected_cases
from celllayout_tf.region_graph import RegionGraph, build_region_graph
from celllayout_tf.schema import ShapeInput, ShapePart


def _connected_component(graph: RegionGraph, start: int) -> set[int]:
    visited = {start}
    queue = deque([start])
    while queue:
        n = queue.popleft()
        for nb in graph.neighbors(n):
            if nb not in visited:
                visited.add(nb)
                queue.append(nb)
    return visited


def _region_poly(region):
    return sg.Polygon(region.shape.exterior, [list(h) for h in region.shape.holes])


def test_simple_rect_region_graph_is_connected():
    shape = ShapeInput(
        "rect",
        (ShapePart(exterior=((0, 0), (12, 0), (12, 8), (0, 8))),),
    )
    graph = build_region_graph(shape)

    assert len(graph.regions) > 0
    assert len(graph.edges) > 0
    component = _connected_component(graph, graph.regions[0].region_id)
    assert component == {r.region_id for r in graph.regions}


def test_region_edges_are_unique_ordered_and_bidirectionally_queryable():
    case = selected_cases([9])[0][2]
    graph = build_region_graph(case)

    seen = set()
    for edge in graph.edges:
        assert edge.region_a < edge.region_b
        key = (edge.region_a, edge.region_b)
        assert key not in seen
        seen.add(key)
        assert graph.edge_between(edge.region_a, edge.region_b) == edge
        assert graph.edge_between(edge.region_b, edge.region_a) == edge


def test_region_edge_shared_boundaries_are_positive():
    case = selected_cases([1])[0][2]
    graph = build_region_graph(case)

    assert graph.edges
    for edge in graph.edges:
        assert edge.shared_boundary_length > 0


def test_hole_separated_regions_are_not_directly_adjacent():
    case = selected_cases([17])[0][2]  # ㅁ자 big hole: hole x=[3,11], y=[3,7]
    graph = build_region_graph(case)

    left = [
        r.region_id
        for r in graph.regions
        if (
            _region_poly(r).centroid.x < 3.0
            and 3.0 < _region_poly(r).centroid.y < 7.0
        )
    ]
    right = [
        r.region_id
        for r in graph.regions
        if (
            _region_poly(r).centroid.x > 11.0
            and 3.0 < _region_poly(r).centroid.y < 7.0
        )
    ]
    assert left
    assert right
    for a in left:
        for b in right:
            assert graph.edge_between(a, b) is None


def test_case_13_disjoint_pieces_of_same_part_are_not_adjacent():
    case = selected_cases([13])[0][2]  # 十자 symmetric
    graph = build_region_graph(case)
    region_by_id = {r.region_id: r for r in graph.regions}

    for edge in graph.edges:
        ra = region_by_id[edge.region_a]
        rb = region_by_id[edge.region_b]
        assert not (
            ra.part_id == rb.part_id and ra.piece_id != rb.piece_id
        ), edge


def test_rotated_l_shape_region_graph_is_connected_across_part_boundary():
    case = selected_cases([20])[0][2]  # ㄱ자 rotated 30°
    graph = build_region_graph(case)

    component = _connected_component(graph, graph.regions[0].region_id)
    assert component == {r.region_id for r in graph.regions}


def test_case_17_regions_around_hole_form_connected_ring():
    case = selected_cases([17])[0][2]  # ㅁ자 big hole
    graph = build_region_graph(case)

    component = _connected_component(graph, graph.regions[0].region_id)
    assert component == {r.region_id for r in graph.regions}
    assert any(edge.hole_contact for edge in graph.edges)
