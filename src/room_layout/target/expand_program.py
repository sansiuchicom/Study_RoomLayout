"""`expand_program` — `{role: count}` → `ProgramRequest` (Step 06 §4.6).

A caller convenience: turn a coarse "how many rooms of each role" request into
a full `ProgramRequest` the pipeline can consume, sourcing the per-room
minimum area from the typology's `TargetRules` instead of making the caller
spell out every `SpaceUnitSpec`.

Field policy for each generated `SpaceUnitSpec` (decisions S06-D1/D2/D3):

- `id`     = ``f"{role}_{i}"`` (1-based within each role) — stable, readable.
- `role`   = the requested role.
- `area_min_m2`   = ``rules.default_min_area_m2[role]`` (S06-D1 — the typology
  owns the minimum barrier; the full-Role-map guarantee means no KeyError).
- `area_target_m2` = ``None`` (S06-D2 — user preferred-size meaning is left
  open; no consumer yet).
- `usage`  = ``None`` (S06-D3 — never auto-guessed from role; set by the
  user/caller at labeling/BIM).
- `required` = ``True`` (every explicitly-requested room is required;
  optional spaces are a future concern).

Injection (4.6 option 가): `rules` is passed in (a pure function, no I/O); the
caller loads it via `TargetAdapter`. `target_type` is stamped straight onto
the `ProgramRequest` (S06-D6 — not validated against `rules`, since nothing
downstream branches on it).

Invalid roles (`corridor`, or `vertical_circulation` without an anchor) are
**not** pre-screened here — `SpaceUnitSpec.__post_init__` already rejects them
(S02-D9), so a second check would duplicate that single source of truth
(S05-D8 spirit). They surface as the constructor's `ValueError`.

**Single-floor only.** This builds a one-`level` `ProgramRequest` (and binds no
`vertical_circulation` anchors). Multi-floor program *allocation* — deciding
which spaces go on which floor + the per-floor stair/vc specs — is the caller's
job (S10-D4: `run()` validates the allocation, it does not invent one). There is
deliberately no `expand_building(...)` helper yet (no consumer). For a
multi-floor house, author `ProgramRequest.floor_programs` directly per floor.
"""

from __future__ import annotations

from room_layout.schema.program import ProgramRequest, Role, SpaceUnitSpec, TargetType
from room_layout.schema.target import TargetRules


def expand_program(
    counts: dict[Role, int],
    target_type: TargetType,
    *,
    rules: TargetRules,
    level: int = 1,
) -> ProgramRequest:
    """Expand a per-role room count into a single-floor `ProgramRequest`.

    Args:
        counts: requested room count per `Role` (e.g. ``{"public": 1,
            "private": 3, "wet": 1}``). A count of 0 (or absent) produces no
            rooms of that role.
        target_type: the typology, stamped onto the result (S06-D6).
        rules: the active `TargetRules` (provides `default_min_area_m2`).
        level: the floor level the program is placed on (v1 single-floor).

    Returns:
        a `ProgramRequest` with `floor_programs[level]` holding the expanded
        `SpaceUnitSpec` list (role-grouped, 1-based ids).

    Raises:
        ValueError: a count is not a non-negative int (bool/float rejected), or
            a requested role is not a valid input role (the latter via
            `SpaceUnitSpec.__post_init__`).
    """
    specs: list[SpaceUnitSpec] = []
    for role, count in counts.items():
        # `count` must be a real non-negative int. `bool` is a subclass of int
        # (`True`/`False` would silently mean 1/0) and floats raise a confusing
        # `range()` TypeError downstream — reject both with a clear message, the
        # same friendliness as the negative-count guard (count-contract symmetry).
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError(
                f"expand_program: count for role {role!r} must be a non-negative int, "
                f"got {type(count).__name__} {count!r}"
            )
        if count < 0:
            raise ValueError(f"expand_program: count for role {role!r} is negative ({count})")
        for i in range(1, count + 1):
            specs.append(
                SpaceUnitSpec(
                    id=f"{role}_{i}",
                    role=role,
                    usage=None,
                    area_min_m2=rules.default_min_area_m2[role],
                    required=True,
                )
            )

    return ProgramRequest(target_type=target_type, floor_programs={level: specs})
