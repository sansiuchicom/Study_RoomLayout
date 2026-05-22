"""Tests for Phase 8 corridor carving."""

from __future__ import annotations

from collections import deque

import pytest

from celllayout_tf.corridor import CorridoredLayout
from celllayout_tf.layout_fixtures import make_fixtures
from celllayout_tf.room_growth import LayoutFixture


# ---------- LayoutFixture.detour_threshold ----------


def test_layout_fixture_default_detour_threshold_is_2_0():
    fix = next(iter(make_fixtures()))
    assert fix.detour_threshold == 2.0


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


_FIXTURE_IDS = tuple(
    f"{fixture.case_index:02d}-{fixture.case_name}"
    for fixture in make_fixtures()
)


@pytest.mark.parametrize("case_idx", range(len(_FIXTURE_IDS)), ids=_FIXTURE_IDS)
def test_carve_corridors_runs_on_every_fixture(corridor_cases, case_idx):
    case = corridor_cases[case_idx]
    assert isinstance(case.layout, CorridoredLayout)
    assert case.layout.fixture is case.fixture


def test_corridor_region_ids_concatenates_base_and_shortcut(growth_cases):
    growth = growth_cases[0].growth
    layout = CorridoredLayout(
        fixture=growth.fixture,
        rooms=growth.rooms,
        base_corridor_region_ids=(1, 2, 3),
        shortcut_corridor_region_ids=(7, 8),
        leftover_region_ids=(),
    )
    assert layout.corridor_region_ids == (1, 2, 3, 7, 8)


# ---------- Stage 1 invariants ----------


def test_w2_partition_is_exact(corridor_cases):
    """Every region appears in exactly one of: a room, corridor, or leftover."""
    for case in corridor_cases:
        fixture = case.fixture
        layout = case.layout
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
        for rid in layout.shortcut_corridor_region_ids:
            assert rid not in seen, (
                f"case {fixture.case_index}: region {rid} in both "
                f"{seen[rid]} and shortcut_corridor"
            )
            seen[rid] = "shortcut_corridor"
        for rid in layout.leftover_region_ids:
            assert rid not in seen, (
                f"case {fixture.case_index}: region {rid} in both "
                f"{seen[rid]} and leftover"
            )
            seen[rid] = "leftover"
        missing = case.all_region_ids - set(seen)
        assert not missing, (
            f"case {fixture.case_index}: regions {sorted(missing)} not "
            f"accounted for in any owner"
        )


def test_w2_every_room_single_component(corridor_cases):
    """Each room's region set stays one connected component."""
    for case in corridor_cases:
        fixture = case.fixture
        adj = case.region_adj
        for room_idx, grown in enumerate(case.layout.rooms):
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
                f"disconnected; components reach {len(seen)}/{len(region_set)} "
                f"regions"
            )


def test_w2_every_non_hub_room_reachable_from_hub(corridor_cases):
    """Hub plus corridor must transitively reach every non-empty non-hub room."""
    for case in corridor_cases:
        fixture = case.fixture
        if fixture.hub_room_index is None:
            continue
        layout = case.layout
        adj = case.region_adj

        region_to_room: dict[int, int] = {}
        for room_idx, grown in enumerate(layout.rooms):
            for rid in grown.region_ids:
                region_to_room[rid] = room_idx
        corridor_set = set(layout.corridor_region_ids)
        hub_idx = fixture.hub_room_index

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


def test_w2_diagnostics_records_each_room_decision(corridor_cases):
    """Stage 1 should produce a per-room log entry for every non-hub room."""
    for case in corridor_cases:
        fixture = case.fixture
        if fixture.hub_room_index is None:
            continue
        stage1 = case.layout.diagnostics.get("stage1", {})
        log = stage1.get("log", [])
        logged_rooms = {entry["room"] for entry in log}
        expected = {
            i for i in range(len(case.growth.rooms))
            if i != fixture.hub_room_index
        }
        assert logged_rooms == expected, (
            f"case {fixture.case_index}: expected log entries for rooms "
            f"{sorted(expected)}, got {sorted(logged_rooms)}"
        )
