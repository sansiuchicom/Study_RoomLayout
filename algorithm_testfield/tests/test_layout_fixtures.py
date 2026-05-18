"""Sanity tests for Phase 7 layout fixtures.

Round 1 scope: schema validation + 33 fixtures loadable + seeds inside
footprints. Algorithm itself (region_unit_greedy) lands in Round 2.
"""

from __future__ import annotations

import shapely.geometry as sg
from shapely.ops import unary_union

from celllayout_tf.cases import make_cases
from celllayout_tf.layout_fixtures import (
    DEFAULT_ROLE_ASPECT_RANGES,
    DEFAULT_ROLE_MIN_AREAS,
    make_fixtures,
    selected_fixtures,
)
from celllayout_tf.room_growth import LayoutFixture, RoomSpec
from celllayout_tf.schema import ShapePart


# Expected role distribution per K (mirrors PHASE7_Fixtures.md).
_EXPECTED_ROLE_DISTRIBUTION: dict[int, tuple[str, ...]] = {
    2: ("private", "wet"),
    3: ("public", "private", "wet"),
    4: ("public", "private", "private", "wet"),
    5: ("public", "private", "private", "private", "wet"),
    6: ("public", "private", "private", "private", "wet", "wet"),
    7: ("public", "private", "private", "private", "wet", "wet", "service"),
}


def _to_shapely(part: ShapePart) -> sg.Polygon:
    return sg.Polygon(part.exterior, [list(h) for h in part.holes])


def _footprint(shape) -> sg.Polygon | sg.MultiPolygon:
    return unary_union([_to_shapely(p) for p in shape.parts])


def test_make_fixtures_returns_33():
    fixtures = make_fixtures()
    assert len(fixtures) == 33
    assert all(isinstance(f, LayoutFixture) for f in fixtures)


def test_fixture_case_indices_are_1_to_33():
    fixtures = make_fixtures()
    assert [f.case_index for f in fixtures] == list(range(1, 34))


def test_selected_fixtures_one_based_and_filters_out_of_range():
    selected = selected_fixtures([1, 24, 33, 999])
    assert [f.case_index for f in selected] == [1, 24, 33]


def test_selected_fixtures_empty_list_returns_all():
    assert len(selected_fixtures()) == 33
    assert len(selected_fixtures(None)) == 33


def test_every_fixture_has_expected_role_distribution():
    for fixture in make_fixtures():
        actual = tuple(r.role for r in fixture.rooms)
        expected = _EXPECTED_ROLE_DISTRIBUTION[fixture.K]
        assert actual == expected, (
            f"case {fixture.case_index} ({fixture.case_name}): "
            f"role distribution {actual} != expected {expected}"
        )


def test_every_room_name_is_space_n_in_listed_order():
    for fixture in make_fixtures():
        for idx, room in enumerate(fixture.rooms, start=1):
            assert room.name == f"space_{idx}", (
                f"case {fixture.case_index}: room {idx} named {room.name!r}"
            )


def test_hub_room_index_is_first_public_or_none():
    """K>=3 → first room (always public); K=2 → None."""
    for fixture in make_fixtures():
        hub_idx = fixture.hub_room_index
        if fixture.K == 2:
            assert hub_idx is None, (
                f"case {fixture.case_index}: K=2 should have no hub"
            )
        else:
            assert hub_idx == 0, (
                f"case {fixture.case_index}: hub should be room 0"
            )
            assert fixture.rooms[0].role == "public"


def test_resolved_aspect_range_falls_back_to_role_default():
    fixture = make_fixtures()[0]  # case 01, K=5
    for room in fixture.rooms:
        assert room.target_aspect_range is None  # no per-room override
        assert (
            fixture.resolved_aspect_range(room)
            == DEFAULT_ROLE_ASPECT_RANGES[room.role]
        )


def test_resolved_min_area_uses_role_table():
    fixture = make_fixtures()[0]
    for room in fixture.rooms:
        assert (
            fixture.resolved_min_area(room)
            == DEFAULT_ROLE_MIN_AREAS[room.role]
        )


def test_every_seed_lies_strictly_inside_its_footprint():
    cases = {c.name: c for c in make_cases()}
    for fixture in make_fixtures():
        shape = cases[fixture.case_name]
        footprint = _footprint(shape)
        for room in fixture.rooms:
            if room.seed_position is None:
                continue  # auto-placement; bounds verified by growth path
            pt = sg.Point(*room.seed_position)
            assert footprint.contains(pt), (
                f"case {fixture.case_index} ({fixture.case_name}): "
                f"seed {room.name} at {room.seed_position} is not inside "
                f"footprint (or sits on the boundary)"
            )


def test_no_two_seeds_share_the_exact_same_coordinate():
    """Distinct coords; same-region check needs regionize and lives in Round 2."""
    for fixture in make_fixtures():
        seen: set[tuple[float, float]] = set()
        for room in fixture.rooms:
            if room.seed_position is None:
                continue
            assert room.seed_position not in seen, (
                f"case {fixture.case_index}: two seeds at "
                f"{room.seed_position}"
            )
            seen.add(room.seed_position)


def test_role_tables_share_same_defaults_across_all_fixtures():
    fixtures = make_fixtures()
    for f in fixtures:
        assert f.role_min_areas == DEFAULT_ROLE_MIN_AREAS
        assert f.role_aspect_ranges == DEFAULT_ROLE_ASPECT_RANGES


def test_roomspec_rejects_bad_role():
    import pytest
    with pytest.raises(ValueError, match="role must be one of"):
        RoomSpec("x", "kitchen", (0.0, 0.0))  # type: ignore[arg-type]


def test_roomspec_rejects_bad_aspect_range():
    import pytest
    with pytest.raises(ValueError, match="target_aspect_range must satisfy"):
        RoomSpec("x", "public", (0.0, 0.0), target_aspect_range=(2.0, 1.0))


def test_layoutfixture_rejects_missing_role_tables():
    import pytest
    rooms = (RoomSpec("space_1", "public", (0.0, 0.0)),)
    with pytest.raises(ValueError, match="role_min_areas missing"):
        LayoutFixture(
            case_index=1, case_name="x", footprint_area_m2=10.0,
            rooms=rooms,
            role_min_areas={},  # missing 'public'
            role_aspect_ranges={"public": (1.0, 2.0)},
        )
    with pytest.raises(ValueError, match="role_aspect_ranges missing"):
        LayoutFixture(
            case_index=1, case_name="x", footprint_area_m2=10.0,
            rooms=rooms,
            role_min_areas={"public": 5.0},
            role_aspect_ranges={},  # missing 'public'
        )


# ---------- W3: seed_position optional (auto-placement support) ----------


def _minimal_fixture(rooms: tuple[RoomSpec, ...]) -> LayoutFixture:
    return LayoutFixture(
        case_index=1, case_name="x", footprint_area_m2=10.0,
        rooms=rooms,
        role_min_areas=DEFAULT_ROLE_MIN_AREAS,
        role_aspect_ranges=DEFAULT_ROLE_ASPECT_RANGES,
    )


def test_roomspec_accepts_seed_position_none():
    """Auto-placement: seed_position may be None."""
    spec = RoomSpec("space_1", "public", None)
    assert spec.seed_position is None


def test_layoutfixture_auto_seed_true_when_all_none():
    rooms = (
        RoomSpec("space_1", "public", None),
        RoomSpec("space_2", "private", None),
    )
    fixture = _minimal_fixture(rooms)
    assert fixture.auto_seed is True


def test_layoutfixture_auto_seed_false_when_all_tuple():
    """All 33 existing fixtures: manual placement, auto_seed=False."""
    for f in make_fixtures():
        assert f.auto_seed is False


def test_layoutfixture_rejects_mixed_seed_positions():
    """Mixed None + tuple is ambiguous (which seeds are fixed?) — reject."""
    import pytest
    rooms = (
        RoomSpec("space_1", "public", None),
        RoomSpec("space_2", "private", (1.0, 1.0)),  # mixed
    )
    with pytest.raises(ValueError, match="seed_position must be all-None"):
        _minimal_fixture(rooms)


def test_roomspec_rejects_invalid_seed_tuple_shape():
    import pytest
    with pytest.raises(ValueError, match="seed_position must be"):
        RoomSpec("x", "public", (1.0, 2.0, 3.0))  # type: ignore[arg-type]
