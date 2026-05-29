"""Tests for stages/room_growth.py growth types + role defaults (Step 04 §4.6)."""

from __future__ import annotations

import pytest

from room_layout.stages.room_growth import (
    DEFAULT_ROLE_ASPECT_RANGES,
    DEFAULT_ROLE_MIN_AREAS,
    ROLE_VALUES,
    GrownRoom,
    GrowthResult,
    LayoutFixture,
    RoomSpec,
)

# ---------- role defaults ----------


def test_role_values_are_four_class():
    assert ROLE_VALUES == frozenset({"public", "private", "service", "wet"})


def test_default_tables_cover_all_roles_and_are_valid():
    for role in ROLE_VALUES:
        assert DEFAULT_ROLE_MIN_AREAS[role] >= 0
        a_min, a_max = DEFAULT_ROLE_ASPECT_RANGES[role]
        assert 1.0 <= a_min <= a_max


# ---------- RoomSpec ----------


def test_roomspec_valid():
    r = RoomSpec("space_1", "public", (3.0, 4.0))
    assert r.name == "space_1" and r.role == "public"


def test_roomspec_rejects_empty_name():
    with pytest.raises(ValueError, match="name must be non-empty"):
        RoomSpec("", "public", None)


def test_roomspec_rejects_bad_role():
    with pytest.raises(ValueError, match="role must be one of"):
        RoomSpec("x", "hub", None)  # hub is 7-class only, not a GrowthRole


def test_roomspec_rejects_bad_seed_len():
    with pytest.raises(ValueError, match="seed_position"):
        RoomSpec("x", "wet", (1.0, 2.0, 3.0))  # type: ignore[arg-type]


def test_roomspec_rejects_bad_aspect_range():
    with pytest.raises(ValueError, match="target_aspect_range"):
        RoomSpec("x", "wet", None, target_aspect_range=(4.0, 2.0))


# ---------- LayoutFixture ----------


def _fixture(rooms: tuple[RoomSpec, ...], **kw) -> LayoutFixture:
    return LayoutFixture(
        case_index=1,
        case_name="t",
        footprint_area_m2=100.0,
        rooms=rooms,
        role_min_areas=dict(DEFAULT_ROLE_MIN_AREAS),
        role_aspect_ranges=dict(DEFAULT_ROLE_ASPECT_RANGES),
        **kw,
    )


def test_fixture_properties():
    rooms = (
        RoomSpec("a", "private", (1.0, 1.0)),
        RoomSpec("b", "public", (2.0, 2.0)),
        RoomSpec("c", "wet", (3.0, 3.0)),
    )
    f = _fixture(rooms)
    assert f.K == 3
    assert f.auto_seed is False
    assert f.hub_room_index == 1  # first public


def test_fixture_auto_seed_when_all_none():
    rooms = (RoomSpec("a", "public", None), RoomSpec("b", "wet", None))
    assert _fixture(rooms).auto_seed is True


def test_fixture_hub_none_when_no_public():
    rooms = (RoomSpec("a", "private", None), RoomSpec("b", "wet", None))
    assert _fixture(rooms).hub_room_index is None


def test_fixture_rejects_empty_rooms():
    with pytest.raises(ValueError, match="no rooms"):
        _fixture(())


def test_fixture_rejects_mixed_seed_mode():
    rooms = (RoomSpec("a", "public", (1.0, 1.0)), RoomSpec("b", "wet", None))
    with pytest.raises(ValueError, match="mixed mode"):
        _fixture(rooms)


def test_fixture_rejects_nonpositive_footprint():
    with pytest.raises(ValueError, match="footprint_area_m2 must be > 0"):
        LayoutFixture(
            case_index=1,
            case_name="t",
            footprint_area_m2=0.0,
            rooms=(RoomSpec("a", "public", None),),
            role_min_areas=dict(DEFAULT_ROLE_MIN_AREAS),
            role_aspect_ranges=dict(DEFAULT_ROLE_ASPECT_RANGES),
        )


def test_fixture_rejects_missing_role_table_entry():
    rooms = (RoomSpec("a", "public", None),)
    with pytest.raises(ValueError, match="role_min_areas missing"):
        LayoutFixture(
            case_index=1,
            case_name="t",
            footprint_area_m2=100.0,
            rooms=rooms,
            role_min_areas={"private": 4.0},
            role_aspect_ranges=dict(DEFAULT_ROLE_ASPECT_RANGES),
        )


def test_resolved_aspect_range_override_and_fallback():
    override = RoomSpec("a", "public", None, target_aspect_range=(1.0, 2.0))
    fallback = RoomSpec("b", "wet", None)
    f = _fixture((override, fallback))
    assert f.resolved_aspect_range(override) == (1.0, 2.0)
    assert f.resolved_aspect_range(fallback) == (1.0, 4.0)


def test_resolved_min_area():
    r = RoomSpec("a", "public", None)
    assert _fixture((r,)).resolved_min_area(r) == 8.0


# ---------- result types ----------


def test_grown_room_and_result():
    f = _fixture((RoomSpec("a", "public", None),))
    gr = GrownRoom(name="a", role="public", region_ids=(1, 2, 3), area_m2=9.0)
    res = GrowthResult(fixture=f, rooms=(gr,), unassigned_region_ids=(7,))
    assert res.rooms[0].region_ids == (1, 2, 3)
    assert res.unassigned_region_ids == (7,)
    assert res.diagnostics == {}
