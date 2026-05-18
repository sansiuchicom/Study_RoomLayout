"""Tests for growth_priority.py (Phase 7 Round 4 v2 W6a)."""

from __future__ import annotations

import pytest

from celllayout_tf.cases import selected_cases
from celllayout_tf.growth_priority import (
    SeedAnchor,
    _side_priority_from_outward,
    bounded_voronoi,
    compute_seed_anchors,
)
from celllayout_tf.region_graph import build_region_graph
from celllayout_tf.regionize import regionize
from celllayout_tf.territory import resolve_territories


def _build(case_index: int):
    _, _, shape = selected_cases([case_index])[0]
    regions = regionize(shape)
    graph = build_region_graph(shape, regions=regions)
    territories = resolve_territories(shape)
    by_id = {r.region_id: r for r in regions}
    return shape, regions, graph, territories, by_id


# ---------- _side_priority_from_outward ----------


def test_side_priority_x_dominant_positive():
    """outward = (+3, +1): dominant_out = right, secondary_out = top."""
    pri = _side_priority_from_outward((3.0, 1.0), seed_id=1)
    assert pri == ("right", "top", "bottom", "left")


def test_side_priority_y_dominant_negative():
    """outward = (+1, -3): dominant_out = bottom, secondary_out = right."""
    pri = _side_priority_from_outward((1.0, -3.0), seed_id=1)
    assert pri == ("bottom", "right", "left", "top")


def test_side_priority_zero_outward_deterministic_via_seed_id():
    """Ambiguous outward → hash-based perturbation. Same seed_id → same priority."""
    p1 = _side_priority_from_outward((0.0, 0.0), seed_id=42)
    p2 = _side_priority_from_outward((0.0, 0.0), seed_id=42)
    assert p1 == p2  # determinism

    p3 = _side_priority_from_outward((0.0, 0.0), seed_id=43)
    # Different seed → likely different priority (not strictly required but
    # the implementation uses Random(seed_id) which produces distinct streams)
    # Just check both are valid 4-permutations of sides.
    assert set(p1) == {"top", "right", "bottom", "left"}
    assert set(p3) == {"top", "right", "bottom", "left"}


def test_side_priority_equal_magnitude_x_wins_tie():
    """When |dx| == |dy|, dx is dominant (>= rule)."""
    pri = _side_priority_from_outward((2.0, 2.0), seed_id=1)
    # dx >= |dy| with strict >= → x dominant → right is dom_out
    assert pri[0] == "right"


# ---------- bounded_voronoi ----------


def test_voronoi_single_seed_assigns_whole_territory():
    """case 1 (single rect, K=5 seeds in 1 territory): each seed gets some
    regions; together they partition the territory."""
    shape, regions, graph, terrs, by_id = _build(1)
    # Use first 3 regions as synthetic seeds
    territory = terrs[0]
    in_territory = [r for r in graph.regions if r.part_id == territory.part_id]
    assert len(in_territory) > 3
    seed_ids = tuple(sorted(r.region_id for r in in_territory)[:3])

    cells = bounded_voronoi(territory, seed_ids, graph)
    assert set(cells.keys()) == set(seed_ids)
    # Every region in territory assigned to exactly one cell
    all_assigned = [rid for cell in cells.values() for rid in cell]
    assert len(all_assigned) == len(set(all_assigned))
    assert set(all_assigned) == {r.region_id for r in in_territory}


def test_voronoi_one_seed_takes_all_when_alone():
    """Single seed in territory → entire territory in its cell."""
    shape, regions, graph, terrs, by_id = _build(1)
    territory = terrs[0]
    in_territory = [r for r in graph.regions if r.part_id == territory.part_id]
    seed_id = in_territory[0].region_id

    cells = bounded_voronoi(territory, (seed_id,), graph)
    assert len(cells) == 1
    assert set(cells[seed_id]) == {r.region_id for r in in_territory}


def test_voronoi_raises_on_seed_outside_territory():
    """Seed not in territory → ValueError."""
    shape, regions, graph, terrs, by_id = _build(22)  # multi-territory
    territory_0 = next(t for t in terrs if t.part_id == 0)
    # Find a region in a DIFFERENT territory
    foreign_region = next(
        r for r in graph.regions if r.part_id != territory_0.part_id
    )
    with pytest.raises(ValueError, match="not in territory"):
        bounded_voronoi(territory_0, (foreign_region.region_id,), graph)


# ---------- compute_seed_anchors (high-level integration) ----------


def test_compute_seed_anchors_single_territory_K5():
    """case 1, K=5 seeds → 5 SeedAnchors with valid side_priority."""
    shape, regions, graph, terrs, by_id = _build(1)
    in_territory = [r for r in graph.regions if r.part_id == terrs[0].part_id]
    seeds_by_room = {
        i: rid for i, rid in enumerate(
            sorted(r.region_id for r in in_territory)[:5]
        )
    }

    anchors = compute_seed_anchors(seeds_by_room, graph, terrs, by_id)
    assert set(anchors.keys()) == set(seeds_by_room.keys())
    for room_idx, sa in anchors.items():
        assert isinstance(sa, SeedAnchor)
        assert sa.seed_region_id == seeds_by_room[room_idx]
        assert sa.room_idx == room_idx
        # side_priority is a permutation of all 4 sides
        assert set(sa.side_priority) == {"top", "right", "bottom", "left"}


def test_compute_seed_anchors_multi_territory_case_22():
    """case 22 (main + wing): 2 territories. Seeds in each get own anchor.
    Cross-territory Voronoi is NOT computed — anchors per-territory."""
    shape, regions, graph, terrs, by_id = _build(22)
    # Pick one seed from each territory
    seed_main = next(r for r in graph.regions if r.part_id == 0).region_id
    seed_wing = next(r for r in graph.regions if r.part_id == 1).region_id
    seeds = {0: seed_main, 1: seed_wing}

    anchors = compute_seed_anchors(seeds, graph, terrs, by_id)
    assert set(anchors.keys()) == {0, 1}
    # Main seed's anchor is in main's local frame; wing's in wing's local
    # frame. Both should produce some non-zero outward (or fall back
    # gracefully). Just check they're SeedAnchor instances.
    assert all(isinstance(a, SeedAnchor) for a in anchors.values())


def test_compute_seed_anchors_outward_vector_points_away_from_other_seeds():
    """In a multi-seed cell, outward should point from the seed AWAY from
    the cell-cell boundary (i.e., toward the seed's outer side)."""
    shape, regions, graph, terrs, by_id = _build(1)
    in_territory = sorted(
        (r for r in graph.regions if r.part_id == terrs[0].part_id),
        key=lambda r: r.region_id,
    )
    # Use two seeds clearly far apart to make the outward meaningful.
    seed_a = in_territory[0].region_id   # presumably corner-ish
    seed_b = in_territory[-1].region_id  # opposite corner-ish
    seeds = {0: seed_a, 1: seed_b}

    anchors = compute_seed_anchors(seeds, graph, terrs, by_id)
    a_a, a_b = anchors[0], anchors[1]
    # The two seeds' outward vectors should point in roughly opposite
    # directions (their anchors meet near the Voronoi boundary).
    dot = (
        a_a.outward_vector[0] * a_b.outward_vector[0]
        + a_a.outward_vector[1] * a_b.outward_vector[1]
    )
    assert dot < 0, (
        f"two seeds at opposite ends should have opposite outward vectors; "
        f"got dot={dot}"
    )
