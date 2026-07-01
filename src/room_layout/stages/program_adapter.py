"""Program adapter — new-schema ``ProgramRequest`` → Cell growth ``LayoutFixture``.

Plan reference: ``004_Step04_AlgorithmCore_Plan.md`` §4.14 + S04-D3.

The thin bridge that lets the faithful Cell growth algorithm consume the new
7-class ``ProgramRequest`` (the production input). Per S04-D3:

- **Growth min/aspect via role tables**: ``area_min_m2`` / ``min_dimension_m``
  are *dropped* here — they feed the Step 07 gates, not growth. The fixture
  carries the per-role aspect / min-area tables growth uses (Cell defaults).
  **``area_target_m2`` is now *preserved* into ``RoomSpec`` (Phase 4 Step 2a,
  PlanBIM 145/146)** as the area-aware-growth input; growth stays
  target-agnostic until Step 2b consumes it (carrying it is behaviour-neutral).
- **Role 7→4 collapse**: ``hub`` → Cell ``public`` placed *first* so Cell's
  "first public room = hub" (``hub_room_index``) lands on it; ``corridor`` is
  never an input role; ``vertical_circulation`` is **excluded** (anchor-locked,
  re-inserted post-growth — S04-D4 / 4.15).
- **Identity preservation**: ``RoomSpec.name = SpaceUnitSpec.id``, so the grown
  room carries the program id back and Step 07 recovers the authoritative
  7-class role / usage from it.
- **Auto placement**: the new schema has no seed position, so every
  ``RoomSpec.seed_position`` is ``None`` → ``LayoutFixture.auto_seed`` is True.
"""

from __future__ import annotations

from shapely.ops import unary_union

from room_layout.schema import FloorShape, ProgramRequest
from room_layout.stages._helpers import to_shapely
from room_layout.stages.room_growth import (
    DEFAULT_ROLE_ASPECT_RANGES,
    DEFAULT_ROLE_MIN_AREAS,
    LayoutFixture,
    RoomSpec,
)

# Roles that are not grown rooms: corridor is an output of carving; vertical_
# circulation is anchor-locked (its polygon is the VerticalAnchor footprint).
_EXCLUDED_INPUT_ROLES = frozenset({"corridor", "vertical_circulation"})


def program_to_fixture(
    floor: FloorShape,
    program: ProgramRequest,
    *,
    case_name: str | None = None,
    case_index: int | None = None,
    role_min_areas: dict[str, float] | None = None,
    role_aspect_ranges: dict[str, tuple[float, float]] | None = None,
) -> LayoutFixture:
    """Build the Cell growth ``LayoutFixture`` for ``floor`` from ``program``.

    Reads ``program.floor_programs[floor.level]``. ``role_min_areas`` /
    ``role_aspect_ranges`` default to Cell's tables (S04-D3 — a Step 06
    ``target_rules`` override plugs in here).
    """
    specs = program.floor_programs.get(floor.level)
    if not specs:
        raise ValueError(
            f"program_to_fixture: no floor_programs entry for floor level {floor.level}"
        )

    grown = [s for s in specs if s.role not in _EXCLUDED_INPUT_ROLES]
    if not grown:
        raise ValueError(
            f"program_to_fixture: floor {floor.level} has no growable rooms "
            f"(all corridor / vertical_circulation)"
        )

    # hub-first ordering: `hub` maps to Cell `public`, and Cell's hub is the
    # FIRST public room — so hub-role specs must precede the rest.
    hub_specs = [s for s in grown if s.role == "hub"]
    rest_specs = [s for s in grown if s.role != "hub"]
    ordered = hub_specs + rest_specs

    rooms = tuple(
        RoomSpec(
            name=spec.id,  # identity preservation (S04-D3)
            role="public" if spec.role == "hub" else spec.role,
            seed_position=None,  # production path is auto-placement
            target_aspect_range=None,
            # Phase 4 Step 2a (PlanBIM 145/146): 전형 크기 보존 (이전엔 drop —
            # S04-D3 growth target-agnostic). growth 소비는 Step 2b; 현재는
            # 운반만(동작 무변). min/aspect 게이트는 종전대로.
            area_target_m2=spec.area_target_m2,
        )
        for spec in ordered
    )

    footprint_area = unary_union([to_shapely(p) for p in floor.parts]).area

    return LayoutFixture(
        case_index=case_index if case_index is not None else floor.level,
        case_name=case_name or f"floor_{floor.level}",
        footprint_area_m2=footprint_area,
        rooms=rooms,
        role_min_areas=dict(role_min_areas or DEFAULT_ROLE_MIN_AREAS),
        role_aspect_ranges={
            k: tuple(v) for k, v in (role_aspect_ranges or DEFAULT_ROLE_ASPECT_RANGES).items()
        },
    )
