"""Program input types — `Role`, `TargetType`, `SpaceUnitSpec`, `ProgramRequest`.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.4 + S02-D9
(single-Role design) / S02-D6 (structural-only `__post_init__`) +
Pipeline §2.2 (TargetType Literal, Optional area_min / min_dimension).

The `Role` Literal is the **single source of truth** for the 7-class
taxonomy (D004). Both `SpaceUnitSpec.role` (input) and
`LabeledRoom.role` (output, defined in `output.py`) use this same
Literal. Static-time vs. runtime rejection of `corridor` as an input
role is handled by `SpaceUnitSpec.__post_init__` (S02-D9 rationale —
single-asymmetric-case runtime check beats a parallel `InputRole`
Literal).

`TargetType` Literal lists the typologies for which `target_rules/<t>.json`
(Step 05) is defined. `ProgramRequest.target_type` validates against it
at construction. Adding a new typology = one Literal entry + one
target_rules JSON.
"""

from dataclasses import dataclass
from typing import Literal, get_args

Role = Literal[
    "public",
    "private",
    "service",
    "wet",
    "hub",
    "corridor",
    "vertical_circulation",
]

TargetType = Literal[
    "apartment",
    "house",
    "hotel",
    "office",
    "warehouse",
]

_VALID_ROLES = frozenset(get_args(Role))
_VALID_TARGET_TYPES = frozenset(get_args(TargetType))


@dataclass(frozen=True)
class SpaceUnitSpec:
    """A single requested room slot in the program.

    `role == "corridor"` is rejected at construction (S02-D9): corridors
    are an *output* of carving, not user-requestable. `role ==
    "vertical_circulation"` must reference a `VerticalAnchor.id` via
    `anchor_id` so carving can place the room on the anchor footprint.

    `area_min_m2` and `min_dimension_m` are `None`-able per Pipeline §2.2
    — rooms without strict minimums (e.g., flexible utility) can elide
    them. `area_target_m2` is always required.
    """

    id: str
    role: Role
    usage: str | None
    area_target_m2: float
    area_min_m2: float | None
    min_dimension_m: float | None
    required: bool
    anchor_id: str | None = None

    def __post_init__(self) -> None:
        if self.role not in _VALID_ROLES:
            raise ValueError(
                f"SpaceUnitSpec {self.id!r}: role={self.role!r} not in "
                f"Role Literal: {sorted(_VALID_ROLES)}"
            )
        if self.role == "corridor":
            raise ValueError(
                f"SpaceUnitSpec {self.id!r}: role='corridor' is not a valid input "
                "role (corridor is produced by carving — per S02-D9)"
            )
        if self.role == "vertical_circulation" and self.anchor_id is None:
            raise ValueError(
                f"SpaceUnitSpec {self.id!r}: role='vertical_circulation' requires "
                "anchor_id (must reference a VerticalAnchor.id)"
            )


@dataclass(frozen=True)
class ProgramRequest:
    """The full program input to `run()` — a target type + per-floor specs."""

    target_type: TargetType
    floor_programs: dict[int, list[SpaceUnitSpec]]

    def __post_init__(self) -> None:
        if self.target_type not in _VALID_TARGET_TYPES:
            raise ValueError(
                f"ProgramRequest: target_type={self.target_type!r} not in "
                f"TargetType Literal: {sorted(_VALID_TARGET_TYPES)}"
            )
        if not self.floor_programs:
            raise ValueError("ProgramRequest.floor_programs must be non-empty")
