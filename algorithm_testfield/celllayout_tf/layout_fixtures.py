"""Layout fixtures for the 33 testfield cases — Phase 7 input data.

Each case in ``cases.py`` has one matching ``LayoutFixture`` here,
declaring:

  - K (room count) — derived from footprint area (see PHASE7_Fixtures.md)
  - per-room role + seed_position
  - shared role tables (``DEFAULT_ROLE_MIN_AREAS``,
    ``DEFAULT_ROLE_ASPECT_RANGES``) — same for every case in this iteration

The hub is implicit: first ``RoomSpec`` with ``role == "public"``. K=2
cases (24, 27) have no public room → hub invariant disabled at runtime.

This file is the executable equivalent of ``PHASE7_Fixtures.md``. Keep
them in sync manually when adjusting seeds, K, role distributions, or
role tables.
"""

from __future__ import annotations

from .room_growth import LayoutFixture, RoomSpec


DEFAULT_ROLE_MIN_AREAS: dict[str, float] = {
    "public": 8.0,
    "private": 4.0,
    "wet": 2.0,
    "service": 3.0,
}


DEFAULT_ROLE_ASPECT_RANGES: dict[str, tuple[float, float]] = {
    "public":  (1.0, 4.0),   # W12: uniform 1:4 across roles (tested 1:5/1:3,
    "private": (1.0, 4.0),   # 1:4 is the sweet spot — most rooms fit, only
    "wet":     (1.0, 4.0),   # extreme long arms (case 11 thin) get clipped
    "service": (1.0, 4.0),   # to corridor candidates)
}


def _make_fixture(
    index: int,
    name: str,
    area: float,
    rooms: tuple[RoomSpec, ...],
) -> LayoutFixture:
    return LayoutFixture(
        case_index=index,
        case_name=name,
        footprint_area_m2=area,
        rooms=rooms,
        role_min_areas=DEFAULT_ROLE_MIN_AREAS,
        role_aspect_ranges=DEFAULT_ROLE_ASPECT_RANGES,
    )


def make_fixtures() -> list[LayoutFixture]:
    """Return all 33 fixtures in case-index order."""
    return [
        _make_fixture(1, "30평 판상형", 140.0, (
            RoomSpec("space_1", "public",  (3.5, 5.0)),
            RoomSpec("space_2", "private", (7.0, 7.5)),
            RoomSpec("space_3", "private", (7.0, 2.5)),
            RoomSpec("space_4", "private", (11.0, 7.5)),
            RoomSpec("space_5", "wet",     (11.0, 2.5)),
        )),
        _make_fixture(2, "30평 ㄱ자", 122.0, (
            RoomSpec("space_1", "public",  (4.0, 5.0)),
            RoomSpec("space_2", "private", (4.0, 8.0)),
            RoomSpec("space_3", "private", (4.0, 2.0)),
            RoomSpec("space_4", "private", (11.0, 5.0)),
            RoomSpec("space_5", "wet",     (12.0, 2.0)),
        )),
        _make_fixture(3, "40평 4-bay", 160.0, (
            RoomSpec("space_1", "public",  (3.0, 5.0)),
            RoomSpec("space_2", "private", (8.0, 7.5)),
            RoomSpec("space_3", "private", (13.0, 7.5)),
            RoomSpec("space_4", "private", (13.0, 2.5)),
            RoomSpec("space_5", "wet",     (8.0, 2.5)),
            RoomSpec("space_6", "wet",     (3.0, 2.0)),
        )),
        _make_fixture(4, "50평 ㄷ자", 131.0, (
            RoomSpec("space_1", "public",  (2.0, 5.0)),
            RoomSpec("space_2", "private", (5.5, 1.9)),
            RoomSpec("space_3", "private", (10.0, 1.9)),
            RoomSpec("space_4", "private", (10.0, 8.1)),
            RoomSpec("space_5", "wet",     (5.5, 8.1)),
        )),
        _make_fixture(5, "타워형", 122.0, (
            RoomSpec("space_1", "public",  (4.0, 4.0)),
            RoomSpec("space_2", "private", (8.0, 5.5)),
            RoomSpec("space_3", "private", (11.5, 9.0)),
            RoomSpec("space_4", "private", (12.0, 4.5)),
            RoomSpec("space_5", "wet",     (4.0, 1.0)),
        )),
        _make_fixture(6, "Square 10x10", 100.0, (
            RoomSpec("space_1", "public",  (3.0, 7.0)),
            RoomSpec("space_2", "private", (7.0, 7.0)),
            RoomSpec("space_3", "private", (7.0, 3.0)),
            RoomSpec("space_4", "wet",     (3.0, 3.0)),
        )),
        _make_fixture(7, "Long rect 20x6", 120.0, (
            RoomSpec("space_1", "public",  (3.0, 3.0)),
            RoomSpec("space_2", "private", (8.0, 3.0)),
            RoomSpec("space_3", "private", (13.0, 3.0)),
            RoomSpec("space_4", "wet",     (18.0, 3.0)),
        )),
        _make_fixture(8, "Tall rect 6x20", 120.0, (
            RoomSpec("space_1", "public",  (3.0, 3.0)),
            RoomSpec("space_2", "private", (3.0, 8.0)),
            RoomSpec("space_3", "private", (3.0, 13.0)),
            RoomSpec("space_4", "wet",     (3.0, 18.0)),
        )),
        _make_fixture(9, "ㄱ자 standard", 95.0, (
            RoomSpec("space_1", "public",  (3.0, 2.5)),
            RoomSpec("space_2", "private", (8.0, 2.5)),
            RoomSpec("space_3", "private", (2.5, 8.0)),
            RoomSpec("space_4", "wet",     (2.5, 11.0)),
        )),
        _make_fixture(10, "ㄱ자 thick", 124.0, (
            RoomSpec("space_1", "public",  (3.0, 2.5)),
            RoomSpec("space_2", "private", (8.0, 2.5)),
            RoomSpec("space_3", "private", (12.0, 2.5)),
            RoomSpec("space_4", "private", (3.0, 9.0)),
            RoomSpec("space_5", "wet",     (3.0, 12.5)),
        )),
        _make_fixture(11, "ㄱ자 thin", 75.0, (
            RoomSpec("space_1", "public",  (5.0, 1.5)),
            RoomSpec("space_2", "private", (1.5, 8.0)),
            RoomSpec("space_3", "wet",     (11.0, 1.5)),
        )),
        _make_fixture(12, "7자 standard", 98.0, (
            RoomSpec("space_1", "public",  (5.0, 9.5)),
            RoomSpec("space_2", "private", (11.0, 9.5)),
            RoomSpec("space_3", "private", (12.0, 4.0)),
            RoomSpec("space_4", "wet",     (12.0, 1.5)),
        )),
        _make_fixture(13, "十자 symmetric", 88.0, (
            RoomSpec("space_1", "public",  (7.0, 6.0)),
            RoomSpec("space_2", "private", (2.0, 6.0)),
            RoomSpec("space_3", "wet",     (12.0, 6.0)),
        )),
        _make_fixture(14, "十자 asymmetric", 69.0, (
            RoomSpec("space_1", "public",  (7.5, 5.5)),
            RoomSpec("space_2", "private", (2.0, 5.5)),
            RoomSpec("space_3", "wet",     (12.0, 5.5)),
        )),
        _make_fixture(15, "T자", 98.0, (
            RoomSpec("space_1", "public",  (7.0, 2.5)),
            RoomSpec("space_2", "private", (2.0, 2.5)),
            RoomSpec("space_3", "private", (7.0, 8.5)),
            RoomSpec("space_4", "wet",     (12.0, 2.5)),
        )),
        _make_fixture(16, "ㅁ자 small hole", 126.0, (
            RoomSpec("space_1", "public",  (2.0, 5.0)),
            RoomSpec("space_2", "private", (6.5, 1.5)),
            RoomSpec("space_3", "private", (6.5, 8.5)),
            RoomSpec("space_4", "private", (12.0, 7.5)),
            RoomSpec("space_5", "wet",     (12.0, 2.5)),
        )),
        _make_fixture(17, "ㅁ자 big hole", 108.0, (
            RoomSpec("space_1", "public",  (1.5, 5.0)),
            RoomSpec("space_2", "private", (7.0, 1.5)),
            RoomSpec("space_3", "private", (12.5, 2.0)),
            RoomSpec("space_4", "wet",     (7.0, 8.5)),
            RoomSpec("space_5", "private", (12.5, 8.0)),
        )),
        _make_fixture(18, "Rect rotated 30°", 96.0, (
            RoomSpec("space_1", "public",  (4.5, 3.0)),
            RoomSpec("space_2", "private", (7.5, 3.0)),
            RoomSpec("space_3", "private", (4.5, 5.0)),
            RoomSpec("space_4", "wet",     (7.5, 5.0)),
        )),
        _make_fixture(19, "Rect rotated 60°", 96.0, (
            RoomSpec("space_1", "public",  (4.5, 3.0)),
            RoomSpec("space_2", "private", (7.5, 3.0)),
            RoomSpec("space_3", "private", (4.5, 5.0)),
            RoomSpec("space_4", "wet",     (7.5, 5.0)),
        )),
        _make_fixture(20, "ㄱ자 rotated 30°", 95.0, (
            RoomSpec("space_1", "public",  (4.5, 4.0)),
            RoomSpec("space_2", "private", (4.0, 6.0)),
            RoomSpec("space_3", "private", (3.5, 6.5)),
            RoomSpec("space_4", "wet",     (6.0, 2.5)),
        )),
        _make_fixture(21, "7자 rotated 45°", 88.0, (
            RoomSpec("space_1", "public",  (7.5, 8.0)),
            RoomSpec("space_2", "private", (4.0, 8.0)),
            RoomSpec("space_3", "wet",     (10.5, 5.5)),
        )),
        _make_fixture(22, "Main + wing 25°", 116.0, (
            RoomSpec("space_1", "public",  (4.0, 4.0)),
            RoomSpec("space_2", "private", (8.0, 4.0)),
            RoomSpec("space_3", "private", (11.5, 8.5)),
            RoomSpec("space_4", "wet",     (4.0, 1.5)),
        )),
        # Case name matches cases.py (ASCII +/-); PHASE7_Fixtures.md uses ± for readability.
        _make_fixture(23, "Mirror wings +/-30°", 126.0, (
            RoomSpec("space_1", "public",  (4.0, 4.0)),
            RoomSpec("space_2", "private", (8.0, 4.0)),
            RoomSpec("space_3", "private", (-1.0, 8.0)),
            RoomSpec("space_4", "private", (12.0, 9.0)),
            RoomSpec("space_5", "wet",     (4.0, 1.5)),
        )),
        _make_fixture(24, "7자 angled (-25 + 0°)", 48.0, (
            RoomSpec("space_1", "private", (8.0, 4.0)),
            RoomSpec("space_2", "wet",     (4.0, 9.0)),
        )),
        _make_fixture(25, "Circle r=6", 113.0, (
            RoomSpec("space_1", "public",  (-2.5,  2.5)),
            RoomSpec("space_2", "private", ( 2.5,  2.5)),
            RoomSpec("space_3", "private", (-2.5, -2.5)),
            RoomSpec("space_4", "wet",     ( 2.5, -2.5)),
        )),
        _make_fixture(26, "Ellipse 10x6", 100.0, (
            RoomSpec("space_1", "public",  (-3.5,  1.5)),
            RoomSpec("space_2", "private", ( 3.5,  1.5)),
            RoomSpec("space_3", "private", (-3.5, -1.5)),
            RoomSpec("space_4", "wet",     ( 3.5, -1.5)),
        )),
        _make_fixture(27, "Half circle", 57.0, (
            RoomSpec("space_1", "private", (-2.5, 2.5)),
            RoomSpec("space_2", "wet",     ( 2.5, 2.5)),
        )),
        _make_fixture(28, "Curved ㄱ", 105.0, (
            RoomSpec("space_1", "public",  (2.0, 8.0)),
            RoomSpec("space_2", "private", (2.0, 12.0)),
            RoomSpec("space_3", "private", (8.5, 2.0)),
            RoomSpec("space_4", "wet",     (12.0, 2.0)),
        )),
        _make_fixture(29, "E자", 132.0, (
            RoomSpec("space_1", "public",  (2.5, 8.0)),
            RoomSpec("space_2", "private", (9.0, 1.5)),
            RoomSpec("space_3", "private", (9.0, 6.5)),
            RoomSpec("space_4", "private", (9.0, 11.0)),
            RoomSpec("space_5", "wet",     (2.5, 3.0)),
        )),
        _make_fixture(30, "ㄹ자 (zigzag)", 112.0, (
            RoomSpec("space_1", "public",  (5.0, 10.0)),
            RoomSpec("space_2", "private", (5.0, 2.0)),
            RoomSpec("space_3", "private", (12.5, 6.0)),
            RoomSpec("space_4", "wet",     (9.0, 2.0)),
        )),
        _make_fixture(31, "비대칭 ㄱ", 62.0, (
            RoomSpec("space_1", "public",  (6.0, 1.5)),
            RoomSpec("space_2", "private", (1.1, 7.0)),
            RoomSpec("space_3", "wet",     (12.0, 1.5)),
        )),
        _make_fixture(32, "60평 큰 ㄱ자", 242.0, (
            RoomSpec("space_1", "public",  (4.0, 6.0)),
            RoomSpec("space_2", "private", (10.0, 9.0)),
            RoomSpec("space_3", "private", (13.0, 9.0)),
            RoomSpec("space_4", "private", (13.0, 3.0)),
            RoomSpec("space_5", "wet",     (4.0, 2.0)),
            RoomSpec("space_6", "wet",     (19.0, 2.5)),
            RoomSpec("space_7", "service", (18.5, 8.0)),
        )),
        _make_fixture(33, "ㅁ자 + wing", 116.0, (
            RoomSpec("space_1", "public",  (1.5, 5.0)),
            RoomSpec("space_2", "private", (5.0, 1.5)),
            RoomSpec("space_3", "private", (5.0, 8.5)),
            RoomSpec("space_4", "wet",     (13.0, 7.0)),
        )),
    ]


def selected_fixtures(
    indices: list[int] | None = None,
) -> list[LayoutFixture]:
    """Return all fixtures or only the listed case indices (1-based)."""
    all_fix = make_fixtures()
    if not indices:
        return all_fix
    return [
        all_fix[idx - 1]
        for idx in indices
        if 1 <= idx <= len(all_fix)
    ]
