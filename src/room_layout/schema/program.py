"""Program input types — `Role`, `SpaceUnitSpec`, `ProgramRequest`.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.4 + S02-D9
(single-Role design) / S02-D6 (structural-only `__post_init__`).

The `Role` Literal is the **single source of truth** for the 7-class
taxonomy (D004). Both `SpaceUnitSpec.role` (input) and
`LabeledRoom.role` (output, defined in `output.py`) use this same
Literal. Static-time vs. runtime rejection of `corridor` as an input
role is handled by `SpaceUnitSpec.__post_init__` (S02-D9 rationale —
single-asymmetric-case runtime check beats a parallel `InputRole`
Literal).
"""

from dataclasses import dataclass
from typing import Literal

Role = Literal[
    "public",
    "private",
    "service",
    "wet",
    "hub",
    "corridor",
    "vertical_circulation",
]


@dataclass(frozen=True)
class SpaceUnitSpec:
    """A single requested room slot in the program.

    `role == "corridor"` is rejected at construction (S02-D9): corridors
    are an *output* of carving, not user-requestable. `role ==
    "vertical_circulation"` must reference a `VerticalAnchor.id` via
    `anchor_id` so carving can place the room on the anchor footprint.
    """

    id: str
    role: Role
    usage: str | None
    area_target_m2: float
    area_min_m2: float
    min_dimension_m: float
    required: bool
    anchor_id: str | None = None

    def __post_init__(self) -> None:
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

    target_type: str
    floor_programs: dict[int, list[SpaceUnitSpec]]

    def __post_init__(self) -> None:
        if not self.target_type.strip():
            raise ValueError("ProgramRequest.target_type must be non-empty")
        if not self.floor_programs:
            raise ValueError("ProgramRequest.floor_programs must be non-empty")
