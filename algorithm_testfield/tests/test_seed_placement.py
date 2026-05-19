"""Tests for ``seed_placement.py`` W1 helpers + W2 pipeline (Phase 7 Round 4)."""

from __future__ import annotations

import pytest

from celllayout_tf.cases import selected_cases
from celllayout_tf.region_graph import build_region_graph
from celllayout_tf.schema import ShapeInput, ShapePart
from celllayout_tf.seed_placement import (
    SeedPlacement,
    auto_place_seeds,
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


# ---------- W2: auto_place_seeds ----------


def _phases(seeds: tuple[SeedPlacement, ...]) -> list[str]:
    return [s.phase for s in seeds]


def _territory_ids_covered(
    seeds: tuple[SeedPlacement, ...]
) -> set[int]:
    return {s.region.part_id for s in seeds}


def test_auto_place_seeds_single_territory_K5_hub_plus_fps():
    """case 1: single territory, K=5 → 1 hub + 4 fps."""
    _, graph, terrs = _build(1)
    assert len(terrs) == 1
    seeds = auto_place_seeds(graph, terrs, K=5, has_public=True)
    assert len(seeds) == 5
    assert _phases(seeds) == ["hub", "fps", "fps", "fps", "fps"]
    assert _territory_ids_covered(seeds) == {terrs[0].part_id}


def test_auto_place_seeds_case_22_K4_two_territories_both_covered():
    """case 22 main+wing: K=4, 2 territories → hub + coverage + 2 fps."""
    _, graph, terrs = _build(22)
    assert len(terrs) == 2
    seeds = auto_place_seeds(graph, terrs, K=4, has_public=True)
    assert len(seeds) == 4
    assert _phases(seeds) == ["hub", "coverage", "fps", "fps"]
    assert _territory_ids_covered(seeds) == {t.part_id for t in terrs}


def test_auto_place_seeds_case_23_K5_three_territories_all_covered():
    _, graph, terrs = _build(23)
    assert len(terrs) == 3
    seeds = auto_place_seeds(graph, terrs, K=5, has_public=True)
    assert len(seeds) == 5
    assert _phases(seeds) == ["hub", "coverage", "coverage", "fps", "fps"]
    assert _territory_ids_covered(seeds) == {t.part_id for t in terrs}


def test_auto_place_seeds_case_24_K2_no_public_two_territories():
    """case 24 K=2, no public → 0 hub + 2 coverage (one per territory)."""
    _, graph, terrs = _build(24)
    assert len(terrs) == 2
    seeds = auto_place_seeds(graph, terrs, K=2, has_public=False)
    assert len(seeds) == 2
    assert _phases(seeds) == ["coverage", "coverage"]
    assert _territory_ids_covered(seeds) == {t.part_id for t in terrs}


def test_auto_place_seeds_case_27_K2_no_public_single_territory():
    """case 27 K=2 with 1 territory → coverage + fps in same territory."""
    _, graph, terrs = _build(27)
    assert len(terrs) == 1
    seeds = auto_place_seeds(graph, terrs, K=2, has_public=False)
    assert len(seeds) == 2
    assert _phases(seeds) == ["coverage", "fps"]
    assert _territory_ids_covered(seeds) == {terrs[0].part_id}


def test_auto_place_seeds_case_28_K4_three_territories():
    _, graph, terrs = _build(28)
    assert len(terrs) == 3
    seeds = auto_place_seeds(graph, terrs, K=4, has_public=True)
    assert len(seeds) == 4
    assert _phases(seeds) == ["hub", "coverage", "coverage", "fps"]
    assert _territory_ids_covered(seeds) == {t.part_id for t in terrs}


def test_auto_place_seeds_all_seeds_unique_case_22():
    _, graph, terrs = _build(22)
    seeds = auto_place_seeds(graph, terrs, K=4, has_public=True)
    ids = [s.region.region_id for s in seeds]
    assert len(ids) == len(set(ids))


def test_auto_place_seeds_invalid_K_raises():
    _, graph, terrs = _build(1)
    with pytest.raises(ValueError):
        auto_place_seeds(graph, terrs, K=0, has_public=True)


def _disjoint_rects() -> ShapeInput:
    """4 disjoint rect parts with strictly descending areas."""
    return ShapeInput(
        "synthetic_4_disjoint_rects",
        (
            ShapePart(exterior=((0, 0), (10, 0), (10, 5), (0, 5))),       # 50
            ShapePart(exterior=((20, 0), (28, 0), (28, 4), (20, 4))),     # 32
            ShapePart(exterior=((20, 10), (24, 10), (24, 14), (20, 14))), # 16
            ShapePart(exterior=((30, 10), (32, 10), (32, 12), (30, 12))), # 4
        ),
    )


def test_auto_place_seeds_territories_exceed_K_drops_smallest():
    """4 disjoint territories, K=2 → top 2 by area covered, smallest 2 dropped."""
    shape = _disjoint_rects()
    graph = build_region_graph(shape)
    terrs = resolve_territories(shape)
    assert len(terrs) == 4

    seeds = auto_place_seeds(graph, terrs, K=2, has_public=False)
    assert len(seeds) == 2
    assert _phases(seeds) == ["coverage", "coverage"]
    # Top 2 by area = part_id 0 (area 50) and part_id 1 (area 32).
    covered_part_ids = _territory_ids_covered(seeds)
    assert covered_part_ids == {0, 1}, (
        f"expected top-2 by area {{0, 1}}, got {covered_part_ids}"
    )


def test_auto_place_seeds_disjoint_territories_with_hub():
    """Hub election picks from any territory; remaining coverage fills top-K."""
    shape = _disjoint_rects()
    graph = build_region_graph(shape)
    terrs = resolve_territories(shape)
    seeds = auto_place_seeds(graph, terrs, K=3, has_public=True)
    assert len(seeds) == 3
    assert seeds[0].phase == "hub"
    # Hub's territory + 2 more coverage territories (top by area excluding hub's).
    assert _phases(seeds) == ["hub", "coverage", "coverage"]
    assert len(_territory_ids_covered(seeds)) == 3
