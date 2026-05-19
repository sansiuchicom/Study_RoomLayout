"""Phase 8: Corridor Carving — base corridor + detour shortcut + cleanup.

See ``PHASE8_Corridor.md`` for the full spec. This module is the public
entry point; sub-stages are inlined here while the algorithm is being
fleshed out (W1 skeleton, W2 = Stage 1, W3 = Stage 2, W4 = cleanup).
Split into ``corridor_astar.py`` / ``corridor_distance.py`` once the
per-stage code grows enough to warrant it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .dimensions import DimensionPolicy
from .room_growth import GrownRoom, GrowthResult, LayoutFixture
from .schema import ShapeInput


@dataclass(frozen=True)
class CorridoredLayout:
    """Output of Phase 8.

    ``rooms`` is the post-carve copy of ``GrowthResult.rooms`` — region_ids
    are reduced for any room whose region was carved into corridor.

    ``base_corridor_region_ids`` come from Stage 1 (hub-radial), ``shortcut``
    from Stage 2 (detour). ``leftover_region_ids`` are unassigned regions
    that even cleanup could not absorb (usually empty).
    """
    fixture: LayoutFixture
    rooms: tuple[GrownRoom, ...]
    base_corridor_region_ids: tuple[int, ...]
    shortcut_corridor_region_ids: tuple[int, ...]
    leftover_region_ids: tuple[int, ...]
    diagnostics: dict = field(default_factory=dict)

    @property
    def corridor_region_ids(self) -> tuple[int, ...]:
        """All corridor regions — base + shortcut."""
        return self.base_corridor_region_ids + self.shortcut_corridor_region_ids


def carve_corridors(
    shape: ShapeInput,
    growth_result: GrowthResult,
    *,
    policy: DimensionPolicy | None = None,
) -> CorridoredLayout:
    """Phase 8 entry — see ``PHASE8_Corridor.md``.

    W1 skeleton: identity passthrough. Rooms unchanged, no corridor regions
    carved, unassigned regions handed through to ``leftover_region_ids``.
    W2 introduces Stage 1 (base corridor), W3 Stage 2 (detour), W4 cleanup.
    """
    return CorridoredLayout(
        fixture=growth_result.fixture,
        rooms=growth_result.rooms,
        base_corridor_region_ids=(),
        shortcut_corridor_region_ids=(),
        leftover_region_ids=growth_result.unassigned_region_ids,
        diagnostics={"phase": "w1-skeleton-passthrough"},
    )


# ---- Stage 1: base corridor (hub-radial) -------------------------------
# Implemented in W2. See PHASE8_Corridor.md §3.


# ---- Stage 2: detour shortcut ------------------------------------------
# Implemented in W3. See PHASE8_Corridor.md §4.


# ---- Cleanup -----------------------------------------------------------
# Implemented in W4. See PHASE8_Corridor.md §5.
