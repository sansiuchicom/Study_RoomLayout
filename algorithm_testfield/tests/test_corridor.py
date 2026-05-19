"""Tests for Phase 8 corridor carving — W2 (Stage 1 base corridor).

W2 contract: ``carve_corridors`` runs Stage 1 on every fixture and returns
a ``CorridoredLayout`` where

  - every non-hub room is reachable from the hub via region adjacency,
    walking through ``base_corridor_region_ids`` transparently;
  - every room's regions form a single connected component;
  - the partition is exact (each region belongs to exactly one of: a
    room, base corridor, or leftover unassigned).

Stage 2 (detour shortcut) and cleanup behaviours are covered when W3/W4 land.
"""

from __future__ import annotations

from collections import defaultdict, deque

import pytest

from celllayout_tf.atomize import atomize
from celllayout_tf.cases import make_cases
from celllayout_tf.corridor import CorridoredLayout, carve_corridors
from celllayout_tf.layout_fixtures import make_fixtures
from celllayout_tf.region_graph import build_region_graph
from celllayout_tf.regionize import regionize
from celllayout_tf.growth_partition import region_partition_growth
from celllayout_tf.room_growth import LayoutFixture


def _all_cases_and_fixtures():
    cases = {c.name: c for c in make_cases()}
    return [(cases[f.case_name], f) for f in make_fixtures()]


def _region_adj_for(shape):
    atoms = atomize(shape)
    regions = regionize(shape, atoms=atoms)
    rg = build_region_graph(shape, atoms=atoms, regions=regions)
    adj: dict[int, set[int]] = defaultdict(set)
    for e in rg.edges:
        adj[e.region_a].add(e.region_b)
        adj[e.region_b].add(e.region_a)
    for r in regions:
        adj.setdefault(r.region_id, set())
    return adj, {r.region_id for r in regions}


# ---------- LayoutFixture.detour_threshold ----------


def test_layout_fixture_default_detour_threshold_is_2_5():
    fix = next(iter(make_fixtures()))
    assert fix.detour_threshold == 2.5


def test_layout_fixture_rejects_threshold_below_one():
    base = next(iter(make_fixtures()))
    with pytest.raises(ValueError, match="detour_threshold"):
        LayoutFixture(
            case_index=base.case_index,
            case_name=base.case_name,
            footprint_area_m2=base.footprint_area_m2,
            rooms=base.rooms,
            role_min_areas=dict(base.role_min_areas),
            role_aspect_ranges=dict(base.role_aspect_ranges),
            max_l_rooms=base.max_l_rooms,
            detour_threshold=0.5,
        )


def test_layout_fixture_accepts_custom_threshold():
    base = next(iter(make_fixtures()))
    fix = LayoutFixture(
        case_index=base.case_index,
        case_name=base.case_name,
        footprint_area_m2=base.footprint_area_m2,
        rooms=base.rooms,
        role_min_areas=dict(base.role_min_areas),
        role_aspect_ranges=dict(base.role_aspect_ranges),
        max_l_rooms=base.max_l_rooms,
        detour_threshold=1.5,
    )
    assert fix.detour_threshold == 1.5


# ---------- carve_corridors smoke ----------


@pytest.mark.parametrize(
    ("shape", "fixture"),
    _all_cases_and_fixtures(),
    ids=lambda obj: (
        obj.case_name if isinstance(obj, LayoutFixture) else obj.name
    ),
)
def test_carve_corridors_runs_on_every_fixture(shape, fixture):
    growth = region_partition_growth(shape, fixture)
    layout = carve_corridors(shape, growth)
    assert isinstance(layout, CorridoredLayout)
    assert layout.fixture is fixture


def test_corridor_region_ids_concatenates_base_and_shortcut():
    growth = region_partition_growth(*_all_cases_and_fixtures()[0])
    layout = CorridoredLayout(
        fixture=growth.fixture,
        rooms=growth.rooms,
        base_corridor_region_ids=(1, 2, 3),
        shortcut_corridor_region_ids=(7, 8),
        leftover_region_ids=(),
    )
    assert layout.corridor_region_ids == (1, 2, 3, 7, 8)


# ---------- Stage 1 invariants ----------


def test_w2_partition_is_exact():
    """Every region appears in exactly one of: a room, base corridor, leftover."""
    for shape, fixture in _all_cases_and_fixtures():
        growth = region_partition_growth(shape, fixture)
        layout = carve_corridors(shape, growth)
        _adj, all_region_ids = _region_adj_for(shape)

        seen: dict[int, str] = {}
        for room_idx, grown in enumerate(layout.rooms):
            for rid in grown.region_ids:
                assert rid not in seen, (
                    f"case {fixture.case_index}: region {rid} in both "
                    f"{seen[rid]} and room#{room_idx}"
                )
                seen[rid] = f"room#{room_idx}"
        for rid in layout.base_corridor_region_ids:
            assert rid not in seen, (
                f"case {fixture.case_index}: region {rid} in both "
                f"{seen[rid]} and base_corridor"
            )
            seen[rid] = "base_corridor"
        for rid in layout.leftover_region_ids:
            assert rid not in seen, (
                f"case {fixture.case_index}: region {rid} in both "
                f"{seen[rid]} and leftover"
            )
            seen[rid] = "leftover"
        missing = all_region_ids - set(seen)
        assert not missing, (
            f"case {fixture.case_index}: regions {sorted(missing)} not "
            f"accounted for in any owner"
        )


def test_w2_every_room_single_component():
    """Each room's region set stays one connected component on region adjacency.

    Pass-1 retry (cut-vertex + simulation) must keep every room intact; if
    retries are exhausted the carve is skipped (room reaches via cleanup later).
    """
    for shape, fixture in _all_cases_and_fixtures():
        growth = region_partition_growth(shape, fixture)
        layout = carve_corridors(shape, growth)
        adj, _ = _region_adj_for(shape)

        for room_idx, grown in enumerate(layout.rooms):
            region_set = set(grown.region_ids)
            if not region_set:
                continue
            start = next(iter(region_set))
            seen = {start}
            queue = deque([start])
            while queue:
                cur = queue.popleft()
                for nbr in adj[cur]:
                    if nbr in region_set and nbr not in seen:
                        seen.add(nbr)
                        queue.append(nbr)
            assert seen == region_set, (
                f"case {fixture.case_index} room#{room_idx} ({grown.name}): "
                f"disconnected — components reach {len(seen)}/{len(region_set)} "
                f"regions"
            )


def test_w2_every_non_hub_room_reachable_from_hub():
    """Hub + base_corridor must transitively reach every non-empty non-hub room.

    Reachability is computed at room granularity: rooms A and B are adjacent
    if any region in A 4-adjoins any region in B. Hub regions and
    base_corridor regions act as one transparent supernode the BFS walks
    through.
    """
    for shape, fixture in _all_cases_and_fixtures():
        if fixture.hub_room_index is None:
            continue  # K=2 원룸: no hub, no reachability claim
        growth = region_partition_growth(shape, fixture)
        layout = carve_corridors(shape, growth)
        adj, _ = _region_adj_for(shape)

        region_to_room: dict[int, int] = {}
        for room_idx, grown in enumerate(layout.rooms):
            for rid in grown.region_ids:
                region_to_room[rid] = room_idx
        corridor_set = set(layout.base_corridor_region_ids)
        hub_idx = fixture.hub_room_index

        # BFS from hub-region union through (hub regions ∪ corridor),
        # collect any other-room region we touch.
        start_regions = set(layout.rooms[hub_idx].region_ids)
        if not start_regions:
            continue
        passable = start_regions | corridor_set
        seen_rooms = {hub_idx}
        seen_regions = set(start_regions)
        queue = deque(start_regions)
        while queue:
            cur = queue.popleft()
            for nbr in adj[cur]:
                room_of_nbr = region_to_room.get(nbr)
                if room_of_nbr is not None and room_of_nbr != hub_idx:
                    seen_rooms.add(room_of_nbr)
                if nbr in passable and nbr not in seen_regions:
                    seen_regions.add(nbr)
                    queue.append(nbr)

        unreached = []
        for room_idx, grown in enumerate(layout.rooms):
            if room_idx == hub_idx:
                continue
            if not grown.region_ids:
                continue
            if room_idx not in seen_rooms:
                unreached.append((room_idx, grown.name))
        assert not unreached, (
            f"case {fixture.case_index}: rooms unreachable from hub: "
            f"{unreached}; base_corridor={layout.base_corridor_region_ids}"
        )


def test_w2_diagnostics_records_each_room_decision():
    """Stage 1 should produce a per-room log entry for every non-hub room."""
    for shape, fixture in _all_cases_and_fixtures():
        if fixture.hub_room_index is None:
            continue
        growth = region_partition_growth(shape, fixture)
        layout = carve_corridors(shape, growth)
        stage1 = layout.diagnostics.get("stage1", {})
        log = stage1.get("log", [])
        logged_rooms = {entry["room"] for entry in log}
        expected = {
            i for i in range(len(growth.rooms))
            if i != fixture.hub_room_index
        }
        assert logged_rooms == expected, (
            f"case {fixture.case_index}: expected log entries for rooms "
            f"{sorted(expected)}, got {sorted(logged_rooms)}"
        )
