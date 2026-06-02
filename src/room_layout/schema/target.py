"""Target rule values — `TargetRules`.

Plan reference: ``006_Step06_TargetRules_Plan.md`` §2 S06-D1 (+ legacy
``005_Step05_ProgramLayer_Plan.md`` §2 S05-D2 / S05-D3).

`TargetRules` is the **value bundle** the program-admission gates + the
`expand_program` builder depend on — the per-typology knobs that distinguish
an apartment from a hotel from an office.

Step 05 ↔ Step 06 boundary (S05-D2): Step 05 defined the **type** (first
consumer `stage01_program`); Step 06 adds the **values + loading**
(`data/target_rules/<t>.json` + `target.rules_loader` + `TargetAdapter`).

Fields:

- `density_factor` — usable-area fraction of the gross footprint; the area
  gate's capacity is `footprint_area_m2 * density_factor`.
- `min_cardinality` — minimum required count per `Role`. Empty dict = no
  cardinality constraint. Required-only (proto3:D023): only `required=True`
  spaces count toward it (enforced in `stage01_program`, not here).
- `requires_single_floor` — typology forbids multi-floor layouts; the
  multi-floor gate fails when this is set and the building has != 1 floor.
- `default_min_area_m2` — per-`Role` standard floor area (S06-D1). A **full**
  Role-keyed map. This is the SEED `expand_program` reads to fill a fresh
  `SpaceUnitSpec.area_min_m2`; it is **not** a stage01 None-fallback (S05-D1
  stands — stage01 never fills, and a directly-built spec must supply its own
  required `area_min_m2`). Full map (every `Role`, incl. `corridor`) so
  `expand_program[role]` cannot KeyError at runtime — the loader/constructor
  fails loud instead.

The `dict` fields are mutable despite the frozen dataclass (S05-D3 option 가):
kept as plain `dict`s for consistency with the other schema containers
(`ProgramRequest.floor_programs`, `ShapeInput.floors`); the pipeline does not
mutate inputs. Tightening every container to an immutable type is a separate
cross-cutting concern.
"""

from dataclasses import dataclass, field
from typing import get_args

from room_layout.schema.program import Role

# Roles valid as a `min_cardinality` key. Derived from the public `Role`
# Literal, minus `corridor`: corridor is never a user-requestable input role
# (S02-D9 — it is produced by carving), so a `SpaceUnitSpec` can never carry
# it. A `min_cardinality["corridor"] >= 1` rule would therefore be
# unsatisfiable by construction; reject it as a rule-authoring mistake rather
# than letting it silently make a whole typology infeasible (review 4.8).
# `vertical_circulation` stays valid — it IS requestable (anchor-bound).
_CARDINALITY_ROLES = frozenset(get_args(Role)) - {"corridor"}

# Roles that `default_min_area_m2` must cover: ALL of them (S06-D1). corridor
# is included (carving emits corridor rooms; a 0.0 default is fine) so any
# `expand_program[role]` lookup is total — no runtime KeyError.
_ALL_ROLES = frozenset(get_args(Role))


@dataclass(frozen=True)
class TargetRules:
    """Per-typology admission knobs consumed by the Step 05 gates + expand.

    `__post_init__` keeps minimal structural guards (honest-fix):
    `0 < density_factor <= 1` (a usable-area *fraction*, so > 1 is meaningless
    by definition — a domain invariant, not speculative hardening); every
    `min_cardinality` key is a requestable `Role` (not `corridor`) with a
    non-negative int count; `default_min_area_m2` is a full Role map of
    non-negative floats (S06-D1). NaN/inf rejection is the loader's job at the
    JSON boundary (S06-D4), not here (a hand-built dataclass is trusted).
    """

    density_factor: float
    requires_single_floor: bool
    default_min_area_m2: dict[Role, float]  # required full Role map (S06-D1)
    min_cardinality: dict[Role, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (0 < self.density_factor <= 1):
            raise ValueError(
                f"TargetRules: density_factor must be in (0, 1] "
                f"(it is a usable-area fraction), got {self.density_factor}"
            )
        for role, count in self.min_cardinality.items():
            if role not in _CARDINALITY_ROLES:
                raise ValueError(
                    f"TargetRules: min_cardinality role={role!r} is not a valid "
                    f"cardinality key (must be a requestable Role, not 'corridor'): "
                    f"{sorted(_CARDINALITY_ROLES)}"
                )
            if not isinstance(count, int) or count < 0:
                raise ValueError(
                    f"TargetRules: min_cardinality[{role!r}] must be a "
                    f"non-negative int, got {count!r}"
                )
        da_keys = set(self.default_min_area_m2)
        if da_keys != _ALL_ROLES:
            missing = sorted(_ALL_ROLES - da_keys)
            extra = sorted(da_keys - _ALL_ROLES)
            raise ValueError(
                f"TargetRules: default_min_area_m2 must be a full Role map "
                f"(S06-D1); missing={missing}, unknown={extra}"
            )
        for role, area in self.default_min_area_m2.items():
            if isinstance(area, bool) or not isinstance(area, (int, float)) or area < 0:
                raise ValueError(
                    f"TargetRules: default_min_area_m2[{role!r}] must be a "
                    f"non-negative number, got {area!r}"
                )
