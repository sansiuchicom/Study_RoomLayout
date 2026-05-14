"""Seeded room growth — Phase 7 algorithm sandbox.

External fixture (``LayoutFixture``) declares K rooms with seed positions
and per-role aspect / min-area tables. The algorithm consumes the
fixture and grows each room from its seed into a contiguous set of
regions, honoring the aspect range and weak hub-connectivity as hard
gates (D005 spirit), and the per-role min_area as a target.

The first ``RoomSpec`` with ``role == "public"`` is the hub. If no
``public`` room exists (K=2 cases), hub invariant is disabled.

Out of scope (deferred): atom-level corridor carving, hub selection,
seed positioning, door-capability validation, repair.

See ``README.md`` § Phase 7 for the full spec; see ``PHASE7_Fixtures.md``
for fixture data conventions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Role = Literal["public", "private", "service", "wet"]

ROLE_VALUES: frozenset[str] = frozenset(("public", "private", "service", "wet"))


@dataclass(frozen=True)
class RoomSpec:
    """One room's input declaration in a fixture.

    ``target_aspect_range``: ``None`` → fall back to fixture's per-role
    default; ``(a_min, a_max)`` → explicit range. Algorithm uses this as
    a hard gate when deciding which region to absorb next.
    """
    name: str
    role: Role
    seed_position: tuple[float, float]
    target_aspect_range: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("RoomSpec.name must be non-empty")
        if self.role not in ROLE_VALUES:
            raise ValueError(
                f"RoomSpec.role must be one of {sorted(ROLE_VALUES)}, "
                f"got {self.role!r}"
            )
        if len(self.seed_position) != 2:
            raise ValueError(
                f"RoomSpec.seed_position must be (x, y), "
                f"got {self.seed_position!r}"
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
    """One case's external input. K = len(rooms).

    No central ``target_area`` or ``max_area`` — growth dynamics +
    role-based constraints determine the final distribution. The
    algorithm halts when every room is saturated (no in-gate
    candidate left).
    """
    case_index: int
    case_name: str
    footprint_area_m2: float
    rooms: tuple[RoomSpec, ...]
    role_min_areas: dict[str, float]
    role_aspect_ranges: dict[str, tuple[float, float]]

    def __post_init__(self) -> None:
        if not self.rooms:
            raise ValueError(f"LayoutFixture case {self.case_index}: no rooms")
        if self.footprint_area_m2 <= 0:
            raise ValueError(
                f"LayoutFixture case {self.case_index}: "
                f"footprint_area_m2 must be > 0"
            )

        # role coverage: every role used by a RoomSpec must have entries
        # in both tables.
        roles_used = {r.role for r in self.rooms}
        missing_min = roles_used - set(self.role_min_areas.keys())
        missing_aspect = roles_used - set(self.role_aspect_ranges.keys())
        if missing_min:
            raise ValueError(
                f"LayoutFixture case {self.case_index}: "
                f"role_min_areas missing entries for "
                f"{sorted(missing_min)}"
            )
        if missing_aspect:
            raise ValueError(
                f"LayoutFixture case {self.case_index}: "
                f"role_aspect_ranges missing entries for "
                f"{sorted(missing_aspect)}"
            )

        for role, val in self.role_min_areas.items():
            if role not in ROLE_VALUES:
                raise ValueError(
                    f"LayoutFixture case {self.case_index}: "
                    f"unknown role {role!r} in role_min_areas"
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
                    f"role_aspect_ranges[{role!r}] = {rng} must satisfy "
                    f"1.0 <= min <= max"
                )

    @property
    def K(self) -> int:
        return len(self.rooms)

    @property
    def hub_room_index(self) -> int | None:
        """Index of the first ``public``-role room, or ``None`` if absent.

        K=2 원룸 cases have no ``public`` room → hub invariant disabled.
        """
        for idx, room in enumerate(self.rooms):
            if room.role == "public":
                return idx
        return None

    def resolved_aspect_range(
        self, room: RoomSpec,
    ) -> tuple[float, float] | None:
        """Per-room aspect range after applying role default fallback."""
        if room.target_aspect_range is not None:
            return room.target_aspect_range
        return self.role_aspect_ranges.get(room.role)

    def resolved_min_area(self, room: RoomSpec) -> float:
        """Per-room min area resolved from ``role_min_areas``."""
        return self.role_min_areas[room.role]


@dataclass(frozen=True)
class GrownRoom:
    """One room's growth result: which regions were assigned, and area."""
    name: str
    role: Role
    region_ids: tuple[int, ...]
    area_m2: float


@dataclass(frozen=True)
class GrowthResult:
    """Final state after growth: per-room assignments + diagnostics.

    ``unassigned_region_ids`` lists regions that no room absorbed (either
    because every room's aspect/hub gate rejected them, or because growth
    terminated with the rest unreachable). These are candidates for the
    later atom-level corridor / access phase.
    """
    fixture: LayoutFixture
    rooms: tuple[GrownRoom, ...]
    unassigned_region_ids: tuple[int, ...]
    diagnostics: dict = field(default_factory=dict)


def region_unit_greedy(  # noqa: D401 — algorithm entry point
    shape,
    fixture: LayoutFixture,
    *,
    policy=None,
) -> GrowthResult:
    """Region-unit greedy seeded growth — Phase 7 first algorithm.

    Implementation arrives in Round 2. Round 1 ships schema + fixtures
    only so tests can pin the API before the body lands.
    """
    raise NotImplementedError(
        "region_unit_greedy is scheduled for Phase 7 Round 2; "
        "Round 1 only ships schema + fixtures."
    )
