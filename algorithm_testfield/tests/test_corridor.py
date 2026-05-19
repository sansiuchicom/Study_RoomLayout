"""Tests for Phase 8 corridor carving — W1 skeleton level.

W1 only verifies the contract: ``carve_corridors`` runs on every fixture,
returns a ``CorridoredLayout`` with the partition unchanged (identity
passthrough), and the new ``LayoutFixture.detour_threshold`` field is
wired through with validation. Stage-by-stage carving behaviour is
covered as W2/W3/W4 land.
"""

from __future__ import annotations

import pytest

from celllayout_tf.cases import make_cases
from celllayout_tf.corridor import CorridoredLayout, carve_corridors
from celllayout_tf.layout_fixtures import make_fixtures
from celllayout_tf.room_growth import (
    LayoutFixture,
    RoomSpec,
    region_unit_greedy,
)


def _all_cases_and_fixtures():
    cases = {c.name: c for c in make_cases()}
    return [(cases[f.case_name], f) for f in make_fixtures()]


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


# ---------- carve_corridors W1 contract ----------


@pytest.mark.parametrize(
    ("shape", "fixture"),
    _all_cases_and_fixtures(),
    ids=lambda obj: (
        obj.case_name if isinstance(obj, LayoutFixture) else obj.name
    ),
)
def test_carve_corridors_runs_on_every_fixture(shape, fixture):
    growth = region_unit_greedy(shape, fixture)
    layout = carve_corridors(shape, growth)
    assert isinstance(layout, CorridoredLayout)
    assert layout.fixture is fixture


def test_w1_passthrough_does_not_modify_room_partition():
    """Until W2 lands, the carve step is identity — rooms equal growth."""
    for shape, fixture in _all_cases_and_fixtures():
        growth = region_unit_greedy(shape, fixture)
        layout = carve_corridors(shape, growth)
        assert layout.rooms == growth.rooms
        assert layout.base_corridor_region_ids == ()
        assert layout.shortcut_corridor_region_ids == ()
        assert layout.leftover_region_ids == growth.unassigned_region_ids


def test_corridor_region_ids_concatenates_base_and_shortcut():
    growth = region_unit_greedy(*_all_cases_and_fixtures()[0])
    layout = CorridoredLayout(
        fixture=growth.fixture,
        rooms=growth.rooms,
        base_corridor_region_ids=(1, 2, 3),
        shortcut_corridor_region_ids=(7, 8),
        leftover_region_ids=(),
    )
    assert layout.corridor_region_ids == (1, 2, 3, 7, 8)
