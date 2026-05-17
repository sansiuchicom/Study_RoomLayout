"""Tests for ``seed_placement.py`` W1 helpers (Phase 7 Round 4)."""

from __future__ import annotations

from celllayout_tf.cases import selected_cases
from celllayout_tf.region_graph import build_region_graph
from celllayout_tf.seed_placement import (
    pick_top_centrality,
    region_area,
    region_degree,
    regions_in_territory,
    territory_of_region,
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


def test_territory_of_region_single_part_all_match():
    """Single-part case: every region maps to the single territory."""
    _, graph, terrs = _build(1)
    assert len(terrs) == 1
    for r in graph.regions:
        t = territory_of_region(r, terrs)
        assert t is not None
        assert t.part_id == r.part_id


def test_territory_of_region_case_22_main_wing_two_territories():
    """case 22 main+wing: 2 surviving territories, every region resolves."""
    _, graph, terrs = _build(22)
    assert len(terrs) == 2, f"expected 2 territories, got {len(terrs)}"
    counts: dict[int, int] = {t.part_id: 0 for t in terrs}
    for r in graph.regions:
        t = territory_of_region(r, terrs)
        assert t is not None
        counts[t.part_id] += 1
    for part_id, n in counts.items():
        assert n >= 1, f"territory {part_id} has no region"


def test_territory_of_region_case_28_curved_three_territories():
    """case 28 curved-ㄱ: 3 territories (2 rect + 1 disk)."""
    _, graph, terrs = _build(28)
    assert len(terrs) == 3, f"expected 3 territories, got {len(terrs)}"
    counts: dict[int, int] = {t.part_id: 0 for t in terrs}
    for r in graph.regions:
        t = territory_of_region(r, terrs)
        assert t is not None
        counts[t.part_id] += 1
    for part_id, n in counts.items():
        assert n >= 1, f"territory {part_id} has no region"


def test_regions_in_territory_partition_case_22():
    """``regions_in_territory`` partitions all regions across territories."""
    _, graph, terrs = _build(22)
    seen: set[int] = set()
    for t in terrs:
        for r in regions_in_territory(t, graph):
            assert r.region_id not in seen
            seen.add(r.region_id)
    assert seen == {r.region_id for r in graph.regions}


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


def test_pick_top_centrality_restricted_to_territory_case_22():
    """Phase B coverage uses pick_top_centrality on per-territory subset."""
    _, graph, terrs = _build(22)
    for t in terrs:
        members = regions_in_territory(t, graph)
        picked = pick_top_centrality(members, graph)
        assert picked is not None
        assert picked.part_id == t.part_id
