"""Tests for stages/seed_placement.py centrality + BFS helpers (Step 04 §4.5).

Uses a small synthetic line graph (r1 - r2 - r3) so degree / area-tie-break /
BFS are pinned deterministically, independent of the geometry pipeline.
"""

from __future__ import annotations

from room_layout.schema import ShapePart
from room_layout.stages.region_graph import RegionEdge, RegionGraph
from room_layout.stages.regionize import Region
from room_layout.stages.seed_placement import (
    _bfs_all_distances,
    pick_top_centrality,
    region_area,
    region_degree,
)


def _square(side: float) -> ShapePart:
    return ShapePart(exterior=((0.0, 0.0), (side, 0.0), (side, side), (0.0, side)))


def _region(rid: int, side: float) -> Region:
    return Region(
        region_id=rid,
        shape=_square(side),
        atom_ids=(),
        part_id=0,
        piece_id=0,
        theta=0.0,
        cut_history=(),
    )


def _edge(a: int, b: int) -> RegionEdge:
    return RegionEdge(
        region_a=a,
        region_b=b,
        shared_boundary_length=1.0,
        centroid_distance=2.0,
        same_theta_group=True,
        exterior_contact=False,
        hole_contact=False,
    )


def _line_graph() -> RegionGraph:
    # r1 (area 1) - r2 (area 9) - r3 (area 4)
    regions = (_region(1, 1.0), _region(2, 3.0), _region(3, 2.0))
    return RegionGraph(regions=regions, edges=(_edge(1, 2), _edge(2, 3)))


def test_region_degree():
    g = _line_graph()
    assert region_degree(1, g) == 1
    assert region_degree(2, g) == 2
    assert region_degree(3, g) == 1


def test_region_area():
    assert region_area(_region(9, 2.0)) == 4.0


def test_pick_top_centrality_empty_returns_none():
    assert pick_top_centrality([], _line_graph()) is None


def test_pick_top_centrality_max_degree():
    g = _line_graph()
    picked = pick_top_centrality(g.regions, g)
    assert picked is not None and picked.region_id == 2  # degree 2


def test_pick_top_centrality_tie_break_by_area():
    g = _line_graph()
    # r1 and r3 both have degree 1; r3 (area 4) > r1 (area 1) wins.
    r1, _r2, r3 = g.regions
    picked = pick_top_centrality([r1, r3], g)
    assert picked is r3


def test_bfs_all_distances():
    g = _line_graph()
    assert _bfs_all_distances(1, g) == {1: 0, 2: 1, 3: 2}
    assert _bfs_all_distances(2, g) == {2: 0, 1: 1, 3: 1}


def test_bfs_unreachable_absent_from_map():
    # isolated region 4 (no edges) → not reachable from 1
    regions = (_region(1, 1.0), _region(4, 1.0))
    g = RegionGraph(regions=regions, edges=())
    dists = _bfs_all_distances(1, g)
    assert 4 not in dists
