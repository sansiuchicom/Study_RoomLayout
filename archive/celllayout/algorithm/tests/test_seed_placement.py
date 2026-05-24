"""Tests for shared seed placement helpers."""

from __future__ import annotations

from celllayout_tf.cases import selected_cases
from celllayout_tf.region_graph import build_region_graph
from celllayout_tf.seed_placement import (
    pick_top_centrality,
    region_area,
    region_degree,
)
from celllayout_tf.territory import resolve_territories


def _build(case_index: int):
    """Build (shape, graph, territories) for the given 1-based case."""
    _idx, _name, shape = selected_cases([case_index])[0]
    graph = build_region_graph(shape)
    territories = resolve_territories(shape)
    return shape, graph, territories


def test_region_degree_matches_neighbors():
    _, graph, _ = _build(1)
    for r in graph.regions:
        assert region_degree(r.region_id, graph) == len(
            graph.neighbors(r.region_id)
        )


def test_region_area_positive():
    _, graph, _ = _build(1)
    for r in graph.regions:
        assert region_area(r) > 0


def test_pick_top_centrality_empty_returns_none():
    _, graph, _ = _build(1)
    assert pick_top_centrality([], graph) is None


def test_pick_top_centrality_returns_max_degree_region():
    _, graph, _ = _build(1)
    picked = pick_top_centrality(graph.regions, graph)
    assert picked is not None
    max_deg = max(region_degree(r.region_id, graph) for r in graph.regions)
    assert region_degree(picked.region_id, graph) == max_deg


def test_pick_top_centrality_tie_break_by_area():
    """At equal degree, the largest-area region wins."""
    _, graph, _ = _build(1)
    picked = pick_top_centrality(graph.regions, graph)
    assert picked is not None
    picked_deg = region_degree(picked.region_id, graph)
    same_deg = [
        r for r in graph.regions
        if region_degree(r.region_id, graph) == picked_deg
    ]
    assert region_area(picked) == max(region_area(r) for r in same_deg)


def test_pick_top_centrality_restricted_to_part_case_22():
    _, graph, terrs = _build(22)
    for t in terrs:
        members = tuple(r for r in graph.regions if r.part_id == t.part_id)
        picked = pick_top_centrality(members, graph)
        assert picked is not None
        assert picked.part_id == t.part_id


