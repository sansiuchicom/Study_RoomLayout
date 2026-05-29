"""Phase 7 growth fixture / result types — Step 04 §4.6.

Plan reference: ``004_Step04_AlgorithmCore_Plan.md`` §4.6 + S04-D3 / S04-D7.

The shared types of the growth half (Cell faithful port):

  - ``RoomSpec``      — one room's input declaration in a growth fixture.
  - ``LayoutFixture`` — one case's growth input (K rooms + role tables).
  - ``GrownRoom``     — one room's grown output (region ids + area).
  - ``GrowthResult``  — full per-fixture output (rooms + unassigned + diag).

The actual growth lives in ``growth_partition.py`` (``region_partition_growth``).

**`GrowthRole` (4-class) vs `schema.Role` (7-class)** — Cell's growth knows
only ``public / private / service / wet`` and treats the *first* ``public``
room as the hub. The new schema's public ``Role`` is 7-class
(``+ hub / corridor / vertical_circulation``). ``program_adapter`` (4.14)
collapses 7→4 — ``hub`` → a ``public`` room placed first, ``corridor`` never an
input, ``vertical_circulation`` excluded (anchor-locked, S04-D4) — and sets
``RoomSpec.name = SpaceUnitSpec.id`` so Step 07 recovers the authoritative
7-class role from the id. ``GrownRoom.role`` here is the collapsed 4-class
label, **not** the output source of truth (S04-D3). Named ``GrowthRole`` to
avoid clashing with the public ``room_layout.schema.Role``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

GrowthRole = Literal["public", "private", "service", "wet"]

ROLE_VALUES: frozenset[str] = frozenset(("public", "private", "service", "wet"))

# Cell's per-role defaults (ported from layout_fixtures.py, S04-D3). The new
# schema carries no aspect concept, so growth's hard aspect gate (W12) and the
# min-area diagnostics fall back to these. Both the 33-case golden fixtures
# (4.7) and program_adapter (4.14) build LayoutFixtures from them; a
# target_rules override is a Step 06 concern.
DEFAULT_ROLE_MIN_AREAS: dict[str, float] = {
    "public": 8.0,
    "private": 4.0,
    "wet": 2.0,
    "service": 3.0,
}

DEFAULT_ROLE_ASPECT_RANGES: dict[str, tuple[float, float]] = {
    "public": (1.0, 4.0),
    "private": (1.0, 4.0),
    "wet": (1.0, 4.0),
    "service": (1.0, 4.0),
}


@dataclass(frozen=True)
class RoomSpec:
    """One room's input declaration in a fixture.

    ``seed_position``: ``(x, y)`` for manual placement, or ``None`` to let the
    algorithm auto-place. A fixture's rooms must be all-None or all-tuples —
    mixed mode is rejected by ``LayoutFixture``. The new-schema production path
    is always auto (no ``seed_position`` in ``SpaceUnitSpec``); manual seeds
    appear only in the ported 33-case goldens (S04-D7).

    ``target_aspect_range``: ``None`` → fall back to the fixture's per-role
    default; ``(a_min, a_max)`` → explicit range used as a hard absorption gate.
    """

    name: str
    role: GrowthRole
    seed_position: tuple[float, float] | None
    target_aspect_range: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("RoomSpec.name must be non-empty")
        if self.role not in ROLE_VALUES:
            raise ValueError(
                f"RoomSpec.role must be one of {sorted(ROLE_VALUES)}, got {self.role!r}"
            )
        if self.seed_position is not None and len(self.seed_position) != 2:
            raise ValueError(
                f"RoomSpec.seed_position must be (x, y) or None, got {self.seed_position!r}"
            )
        if self.target_aspect_range is not None:
            a_min, a_max = self.target_aspect_range
            if not (1.0 <= a_min <= a_max):
                raise ValueError(
                    f"RoomSpec.target_aspect_range must satisfy "
                    f"1.0 <= min <= max, got {self.target_aspect_range!r}"
                )


@dataclass(frozen=True)
class LayoutFixture:
    """One case's growth input. K = len(rooms).

    No central ``target_area`` / ``max_area`` — growth dynamics + role-based
    constraints determine the final distribution; the algorithm halts when
    every room is saturated (no in-gate candidate left). Growth is
    target-agnostic (S04-D3); area targets are a Step 07 gate concern.
    """

    case_index: int
    case_name: str
    footprint_area_m2: float
    rooms: tuple[RoomSpec, ...]
    role_min_areas: dict[str, float]
    role_aspect_ranges: dict[str, tuple[float, float]]
    max_l_rooms: int = 2
    detour_threshold: float = 2.0

    def __post_init__(self) -> None:
        if not self.rooms:
            raise ValueError(f"LayoutFixture case {self.case_index}: no rooms")
        if self.footprint_area_m2 <= 0:
            raise ValueError(f"LayoutFixture case {self.case_index}: footprint_area_m2 must be > 0")
        if self.max_l_rooms < 0:
            raise ValueError(
                f"LayoutFixture case {self.case_index}: "
                f"max_l_rooms must be >= 0, got {self.max_l_rooms}"
            )
        if self.detour_threshold < 1.0:
            raise ValueError(
                f"LayoutFixture case {self.case_index}: "
                f"detour_threshold must be >= 1.0, got {self.detour_threshold}"
            )

        # role coverage: every role used by a RoomSpec must have entries in
        # both tables.
        roles_used = {r.role for r in self.rooms}
        missing_min = roles_used - set(self.role_min_areas.keys())
        missing_aspect = roles_used - set(self.role_aspect_ranges.keys())
        if missing_min:
            raise ValueError(
                f"LayoutFixture case {self.case_index}: "
                f"role_min_areas missing entries for {sorted(missing_min)}"
            )
        if missing_aspect:
            raise ValueError(
                f"LayoutFixture case {self.case_index}: "
                f"role_aspect_ranges missing entries for {sorted(missing_aspect)}"
            )

        for role, val in self.role_min_areas.items():
            if role not in ROLE_VALUES:
                raise ValueError(
                    f"LayoutFixture case {self.case_index}: unknown role {role!r} in role_min_areas"
                )
            if val < 0:
                raise ValueError(
                    f"LayoutFixture case {self.case_index}: "
                    f"role_min_areas[{role!r}] = {val} must be >= 0"
                )

        for role, rng in self.role_aspect_ranges.items():
            if role not in ROLE_VALUES:
                raise ValueError(
                    f"LayoutFixture case {self.case_index}: "
                    f"unknown role {role!r} in role_aspect_ranges"
                )
            a_min, a_max = rng
            if not (1.0 <= a_min <= a_max):
                raise ValueError(
                    f"LayoutFixture case {self.case_index}: "
                    f"role_aspect_ranges[{role!r}] = {rng} must satisfy 1.0 <= min <= max"
                )

        # seed_position consistency: all-None (auto) or all-tuple (manual).
        # Mixed mode rejected to avoid ambiguity over which seeds are fixed.
        seed_states = {r.seed_position is None for r in self.rooms}
        if len(seed_states) > 1:
            raise ValueError(
                f"LayoutFixture case {self.case_index}: "
                f"seed_position must be all-None (auto placement) or "
                f"all-tuple (manual placement) — mixed mode is not allowed."
            )

    @property
    def K(self) -> int:
        return len(self.rooms)

    @property
    def auto_seed(self) -> bool:
        """True iff every room has ``seed_position=None`` (auto-placement)."""
        return all(r.seed_position is None for r in self.rooms)

    @property
    def hub_room_index(self) -> int | None:
        """Index of the first ``public``-role room, or ``None`` if absent.

        K=2 single-room cases have no ``public`` room → hub invariant disabled.
        """
        for idx, room in enumerate(self.rooms):
            if room.role == "public":
                return idx
        return None

    def resolved_aspect_range(self, room: RoomSpec) -> tuple[float, float] | None:
        """Per-room aspect range after applying role default fallback."""
        if room.target_aspect_range is not None:
            return room.target_aspect_range
        return self.role_aspect_ranges.get(room.role)

    def resolved_min_area(self, room: RoomSpec) -> float:
        """Per-room min area resolved from ``role_min_areas``."""
        return self.role_min_areas[room.role]


@dataclass(frozen=True)
class GrownRoom:
    """One room's growth result: which regions were assigned, and area.

    ``role`` is the collapsed 4-class growth label (S04-D3) — not the
    authoritative output role, which Step 07 recovers from ``name`` (the
    ``SpaceUnitSpec.id``).
    """

    name: str
    role: GrowthRole
    region_ids: tuple[int, ...]
    area_m2: float


@dataclass(frozen=True)
class GrowthResult:
    """Final state after growth: per-room assignments + diagnostics.

    ``unassigned_region_ids`` lists regions no room absorbed (rejected by an
    aspect/hub gate, or unreachable at termination). These are the candidates
    for the Phase 8 corridor / access carve.
    """

    fixture: LayoutFixture
    rooms: tuple[GrownRoom, ...]
    unassigned_region_ids: tuple[int, ...]
    diagnostics: dict = field(default_factory=dict)
