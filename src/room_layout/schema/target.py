"""Target rule values — `TargetRules`.

Plan reference: ``005_Step05_ProgramLayer_Plan.md`` §2 S05-D2 / S05-D3.

`TargetRules` is the **value bundle** the program-admission gates depend on
— the per-typology knobs (`density_factor`, `min_cardinality`,
`requires_single_floor`) that distinguish an apartment from a hotel from an
office.

Step 05 ↔ Step 06 boundary (S05-D2): this Step defines the **type** (a type
is defined where it is first needed — `stage01_program` is the first
consumer) and hand-constructs it in tests. The **values + loading** —
`data/target_rules/<t>.json`, the JSON loader, and the `TargetAdapter`
registry that produces populated `TargetRules` per `target_type` — are
**Step 06**.

Field set (S05-D3) is intentionally smaller than proto3's `TargetRules`:

- `density_factor` — usable-area fraction of the gross footprint; the area
  gate's capacity is `footprint_area_m2 * density_factor`.
- `min_cardinality` — minimum required count per `Role`. Empty dict = no
  cardinality constraint. Required-only (proto3:D023): only `required=True`
  spaces count toward it (enforced in `stage01_program`, not here).
- `requires_single_floor` — typology forbids multi-floor layouts; the
  multi-floor gate fails when this is set and the building has != 1 floor.

proto3's `default_min_area_m2` map is **omitted** — it existed for the
role-default fill that S05-D1 eliminates (`area_min_m2` is now required, so
there is nothing to fill).

The `min_cardinality` dict is mutable despite the frozen dataclass (S05-D3
option 가): kept as a plain `dict` for consistency with the other schema
containers (`ProgramRequest.floor_programs`, `ShapeInput.floors`); the
pipeline does not mutate inputs. Tightening every schema container to an
immutable type is a separate cross-cutting concern, not a Step 05 item.
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


@dataclass(frozen=True)
class TargetRules:
    """Per-typology admission knobs consumed by the Step 05 program gates.

    `__post_init__` keeps minimal structural guards (S05-D3, honest-fix):
    `density_factor > 0`; every `min_cardinality` key is a requestable `Role`
    (i.e. not `corridor`); every count is a non-negative int. Population from
    JSON is Step 06.
    """

    density_factor: float
    requires_single_floor: bool
    min_cardinality: dict[Role, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.density_factor <= 0:
            raise ValueError(
                f"TargetRules: density_factor must be > 0, got {self.density_factor}"
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
