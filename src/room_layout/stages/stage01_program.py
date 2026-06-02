"""Stage 01 — program instantiation gate (S05-D5 / S05-D8, proto3:D023).

Validates that a `ProgramRequest` carries enough **required** rooms to meet
the typology's cardinality floor, then returns it **unchanged** (S05-D5 — no
`ProgramInstance` concretization: `area_min_m2` is already required after the
S05-D1 realignment, so there is nothing to fill).

Responsibility boundary (S05-D8): this stage owns **only** the rules-based
cardinality check. The other validations proto3's Stage 01 bundled are
already covered elsewhere in this repo and are deliberately **not** repeated
here (single source of truth):

- structural per-space invariants (empty/invalid id, role in Literal,
  corridor/vc rules) — `SpaceUnitSpec.__post_init__` (Step 02).
- cross-reference invariants (duplicate id across floors, floor-in-shape,
  anchor binding) — `validators.validate_input(shape, program)` (Step 02),
  which the Step 07 `run()` calls before atomize.

proto3's Stage 01 re-checked structure/duplicates for "callable in
isolation"; we drop that — `run()` always runs `validate_input` first, so the
redundant guard is a YAGNI insurance our split (Step 02 cross-ref layer)
already retires.

Required-only cardinality (proto3:D023): optional spaces (`required=False`)
do not satisfy `min_cardinality`. Dropping/repairing optional spaces is a
later-stage concern (fail-only, D020).

Single-floor scope (S05-D6): v1 lays out one floor; multi-floor cardinality
aggregation is the Step 10 orchestrator's concern. This stage checks the
specs of the one floor it is handed.
"""

from __future__ import annotations

from collections import Counter

from room_layout.schema.failure import FailureRecord, ProgramInstantiationFailure
from room_layout.schema.program import SpaceUnitSpec
from room_layout.schema.target import TargetRules


def run(
    specs: list[SpaceUnitSpec],
    *,
    rules: TargetRules,
) -> list[SpaceUnitSpec]:
    """Run the cardinality gate over one floor's specs.

    Args:
        specs: the `SpaceUnitSpec` list for a single floor (e.g.
            `program.floor_programs[level]`).
        rules: the active `TargetRules` (provides `min_cardinality`).

    Returns:
        `specs` unchanged on success (S05-D5).

    Raises:
        ProgramInstantiationFailure: if any role's required-space count is
            below `rules.min_cardinality[role]` (code
            `PROGRAM_CARDINALITY_INSUFFICIENT`).
    """
    # Required-only count per role (D023). corridor/vertical_circulation are
    # counted as-is if present (no special handling — judgment 2).
    actual = Counter(s.role for s in specs if s.required)

    for role, min_required in rules.min_cardinality.items():
        if actual[role] < min_required:
            raise ProgramInstantiationFailure(
                FailureRecord(
                    code="PROGRAM_CARDINALITY_INSUFFICIENT",
                    stage="01",
                    message=(
                        f"role {role!r} has {actual[role]} required space(s) "
                        f"but the typology needs at least {min_required}"
                    ),
                    data={
                        "role": role,
                        "required_min": min_required,
                        "actual": actual[role],
                    },
                )
            )

    return specs
