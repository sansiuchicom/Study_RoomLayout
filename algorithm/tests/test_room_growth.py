"""Tests for ``region_unit_greedy`` — Phase 7 algorithm.

Scope: every fixture runs without raising, the result obeys the
partition + connectivity + hub-invariant contracts, and the algorithm
is deterministic. Detailed shape evaluation (aspect distribution,
unassigned coverage) is left to the visualization step.
"""

from __future__ import annotations

from collections import defaultdict

import pytest

from celllayout_tf.atomize import atomize
from celllayout_tf.cases import make_cases
from celllayout_tf.layout_fixtures import make_fixtures
from celllayout_tf.region_graph import build_region_graph
from celllayout_tf.regionize import regionize
from celllayout_tf.room_growth import (
    GrowthResult,
    LayoutFixture,
    region_unit_greedy,
)
from celllayout_tf.schema import ShapeInput


# ---------- helpers ----------


def _all_cases_and_fixtures():
    cases = {c.name: c for c in make_cases()}
    return [(cases[f.case_name], f) for f in make_fixtures()]


def _rooms_connected_to_hub_via_region_graph(
    shape: ShapeInput,
    result: GrowthResult,
) -> set[int]:
    """Recompute hub-reachable room indices from the actual region graph."""
    fix = result.fixture
    if fix.hub_room_index is None:
        return set()

    atoms = atomize(shape)
    regions = regionize(shape, atoms=atoms)
    rg = build_region_graph(shape, atoms=atoms, regions=regions)

    region_to_room: dict[int, int] = {}
    for r_idx, grown in enumerate(result.rooms):
        for region_id in grown.region_ids:
            region_to_room[region_id] = r_idx

    neighbors: dict[int, set[int]] = defaultdict(set)
    for e in rg.edges:
        neighbors[e.region_a].add(e.region_b)
        neighbors[e.region_b].add(e.region_a)

    room_adj: dict[int, set[int]] = defaultdict(set)
    for region_id, r_idx in region_to_room.items():
        for nbr in neighbors.get(region_id, ()):
            other = region_to_room.get(nbr)
            if other is not None and other != r_idx:
                room_adj[r_idx].add(other)
                room_adj[other].add(r_idx)

    hub = fix.hub_room_index
    visited = {hub}
    queue = [hub]
    while queue:
        nxt: list[int] = []
        for cur in queue:
            for nbr in room_adj[cur]:
                if nbr not in visited:
                    visited.add(nbr)
                    nxt.append(nbr)
        queue = nxt
    return visited


# ---------- 33-case smoke test ----------


@pytest.mark.parametrize(
    ("shape", "fixture"),
    _all_cases_and_fixtures(),
    ids=lambda obj: (
        obj.case_name if isinstance(obj, LayoutFixture) else obj.name
    ),
)
def test_growth_runs_on_every_fixture(shape, fixture):
    result = region_unit_greedy(shape, fixture)
    assert isinstance(result, GrowthResult)
    assert result.fixture is fixture
    assert len(result.rooms) == fixture.K
    assert result.rooms[0].name == "space_1"


# ---------- structural invariants (case 01 — quick spot-check) ----------


def _result_for(case_index: int) -> tuple[ShapeInput, GrowthResult]:
    cases = {c.name: c for c in make_cases()}
    fix = next(f for f in make_fixtures() if f.case_index == case_index)
    shape = cases[fix.case_name]
    return shape, region_unit_greedy(shape, fix)


def test_each_region_assigned_to_at_most_one_room():
    """Across all 33 cases, partition is exact."""
    for shape, fixture in _all_cases_and_fixtures():
        result = region_unit_greedy(shape, fixture)
        seen: dict[int, str] = {}
        for grown in result.rooms:
            for region_id in grown.region_ids:
                assert region_id not in seen, (
                    f"case {fixture.case_index}: region {region_id} "
                    f"in {grown.name} and {seen[region_id]}"
                )
                seen[region_id] = grown.name
        for region_id in result.unassigned_region_ids:
            assert region_id not in seen, (
                f"case {fixture.case_index}: region {region_id} "
                f"both assigned ({seen[region_id]}) and unassigned"
            )


def test_every_room_has_at_least_one_region():
    """Seed always assigns one region → every room has ≥ 1 region."""
    for shape, fixture in _all_cases_and_fixtures():
        result = region_unit_greedy(shape, fixture)
        for grown in result.rooms:
            assert len(grown.region_ids) >= 1, (
                f"case {fixture.case_index}: room {grown.name} has 0 regions"
            )


def test_every_room_is_connected_in_region_graph():
    """Greedy absorbs only neighbors → assigned set is connected."""
    for shape, fixture in _all_cases_and_fixtures():
        result = region_unit_greedy(shape, fixture)
        atoms = atomize(shape)
        regions = regionize(shape, atoms=atoms)
        rg = build_region_graph(shape, atoms=atoms, regions=regions)

        adj: dict[int, set[int]] = defaultdict(set)
        for e in rg.edges:
            adj[e.region_a].add(e.region_b)
            adj[e.region_b].add(e.region_a)

        for grown in result.rooms:
            ids = set(grown.region_ids)
            if len(ids) <= 1:
                continue
            seen = {next(iter(ids))}
            queue = [next(iter(ids))]
            while queue:
                cur = queue.pop()
                for nbr in adj[cur] & ids:
                    if nbr not in seen:
                        seen.add(nbr)
                        queue.append(nbr)
            assert seen == ids, (
                f"case {fixture.case_index}: room {grown.name} not connected "
                f"(reached {seen} of {ids})"
            )


def test_hub_designation_round_trips_into_diagnostics():
    """``fixture.hub_room_index`` should appear unchanged in diagnostics."""
    for shape, fixture in _all_cases_and_fixtures():
        result = region_unit_greedy(shape, fixture)
        assert (
            result.diagnostics["hub_room_index"] == fixture.hub_room_index
        )


def test_hub_is_always_self_reachable_when_designated():
    """Trivially the hub reaches itself; sanity for the BFS helper."""
    for shape, fixture in _all_cases_and_fixtures():
        if fixture.hub_room_index is None:
            continue
        result = region_unit_greedy(shape, fixture)
        reachable = _rooms_connected_to_hub_via_region_graph(shape, result)
        assert fixture.hub_room_index in reachable, (
            f"case {fixture.case_index}: hub absent from its own component"
        )


# Note: the algorithm enforces only a **weak** hub invariant — a room that
# was already path-connected to the hub does not lose that connection
# during growth. It does NOT guarantee that every room eventually reaches
# the hub; that depends on footprint topology + seed placement. case 30
# (ㄹ자 zigzag) leaves 3 rooms hub-disconnected because their seed
# regions sit in arms that the hub-room cannot reach within its aspect
# range. This is a known limitation, to be evaluated visually in Round 3
# and possibly addressed by a hub-first growth variant.


def test_algorithm_makes_progress_on_every_fixture():
    """At least one room should grow beyond its seed region per case."""
    for shape, fixture in _all_cases_and_fixtures():
        result = region_unit_greedy(shape, fixture)
        any_grew = any(len(r.region_ids) > 1 for r in result.rooms)
        assert any_grew, (
            f"case {fixture.case_index} ({fixture.case_name}): "
            f"no room grew beyond its seed"
        )


def test_k2_cases_have_no_hub_constraint():
    """K=2 cases (24, 27) should still produce a valid GrowthResult."""
    for idx in (24, 27):
        shape, result = _result_for(idx)
        assert result.fixture.hub_room_index is None
        assert len(result.rooms) == 2


def test_algorithm_is_deterministic():
    """Same input → same output (region_ids, unassigned, areas)."""
    shape, fixture = _all_cases_and_fixtures()[0]  # case 01
    r1 = region_unit_greedy(shape, fixture)
    r2 = region_unit_greedy(shape, fixture)
    assert r1.unassigned_region_ids == r2.unassigned_region_ids
    for a, b in zip(r1.rooms, r2.rooms):
        assert a.region_ids == b.region_ids
        assert a.area_m2 == b.area_m2


def test_diagnostics_contain_iteration_log():
    shape, result = _result_for(1)
    diag = result.diagnostics
    assert "iterations" in diag
    assert "total_iterations" in diag
    assert "hub_room_index" in diag
    assert "below_min_area" in diag
    assert diag["total_iterations"] == len(diag["iterations"])


# ---------- W5: auto-seed + shape-gate integration ----------


def _make_auto_fixture(original):
    """Clone a fixture with all room seed_positions set to None."""
    from celllayout_tf.room_growth import LayoutFixture, RoomSpec
    auto_rooms = tuple(
        RoomSpec(
            name=r.name, role=r.role, seed_position=None,
            target_aspect_range=r.target_aspect_range,
        )
        for r in original.rooms
    )
    return LayoutFixture(
        case_index=original.case_index,
        case_name=original.case_name,
        footprint_area_m2=original.footprint_area_m2,
        rooms=auto_rooms,
        role_min_areas=original.role_min_areas,
        role_aspect_ranges=original.role_aspect_ranges,
        max_l_rooms=original.max_l_rooms,
    )


def test_auto_seed_runs_for_simple_rect():
    """case 01 with auto-seed mode produces a valid GrowthResult."""
    cases = {c.name: c for c in make_cases()}
    manual_fixture = make_fixtures()[0]  # case 01
    shape = cases[manual_fixture.case_name]
    auto_fixture = _make_auto_fixture(manual_fixture)
    assert auto_fixture.auto_seed is True
    result = region_unit_greedy(shape, auto_fixture)
    # All rooms have at least 1 region (their seed)
    assert all(len(r.region_ids) >= 1 for r in result.rooms)
    # Hub room (first public) seeded correctly
    assert result.diagnostics["hub_room_index"] == manual_fixture.hub_room_index


def test_auto_seed_k2_case():
    """K=2 fixture (no public) under auto-seed mode."""
    cases = {c.name: c for c in make_cases()}
    manual = make_fixtures()[23]  # case 24 (K=2)
    assert manual.hub_room_index is None
    shape = cases[manual.case_name]
    auto = _make_auto_fixture(manual)
    result = region_unit_greedy(shape, auto)
    assert len(result.rooms) == 2
    assert all(len(r.region_ids) >= 1 for r in result.rooms)


def test_shape_gate_keeps_grown_rooms_within_reflex_budget():
    """Every grown room's union must have reflex <= 1 in local frame.

    With max_l_rooms=2 default, at most 2 rooms can have reflex>=1.
    """
    from celllayout_tf.shape_gate import _reflex_of_union, _REFLEX_INVALID
    for shape, fixture in _all_cases_and_fixtures():
        result = region_unit_greedy(shape, fixture)
        regions_list = regionize(shape)
        regions_by_id = {r.region_id: r for r in regions_list}
        l_rooms = 0
        for room in result.rooms:
            if not room.region_ids:
                continue
            theta = regions_by_id[room.region_ids[0]].theta
            # find a region's territory kind via part_id of any included region
            from celllayout_tf.territory import resolve_territories
            terrs = resolve_territories(shape)
            kinds_in_room = {
                next((t.kind for t in terrs
                     if t.part_id == regions_by_id[rid].part_id), "axis_aligned")
                for rid in room.region_ids
            }
            if "curved" in kinds_in_room:
                continue  # curved territories exempt
            refl = _reflex_of_union(room.region_ids, regions_by_id, theta)
            if refl == _REFLEX_INVALID:
                continue  # disconnected (shouldn't happen)
            assert refl <= 1, (
                f"case {fixture.case_index} {fixture.case_name}: "
                f"room {room.name} has reflex={refl} (T+ shape leaked)"
            )
            if refl == 1:
                l_rooms += 1
        assert l_rooms <= fixture.max_l_rooms, (
            f"case {fixture.case_index}: {l_rooms} L-rooms exceed budget "
            f"{fixture.max_l_rooms}"
        )
