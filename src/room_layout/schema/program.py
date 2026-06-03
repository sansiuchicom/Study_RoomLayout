"""Program input types — `Role`, `TargetType`, `SpaceUnitSpec`, `ProgramRequest`.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.4 + S02-D9
(single-Role design) / S02-D6 (structural-only `__post_init__`) +
Pipeline §2.2 (TargetType Literal) + ``005_Step05_ProgramLayer_Plan.md``
S05-D1 (area-field realignment: required `area_min_m2`, optional
`area_target_m2`).

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

    Area fields (realigned in Step 05, S05-D1 — this Step is their first
    real consumer):

    - `area_min_m2` is **required** — it is the primary input to the Step 05
      admission gate (`check_min_area`) and the Step 07 per-room check.
    - `area_target_m2` is **optional** (`None` by default). It is the
      *diffusion-priority hook* for a possible future area-aware growth pass
      (which would weight expansion by it); v1 growth is target-agnostic
      (S04-D3), so nothing consumes it yet. No committed Step owns that pass —
      it may never land; the optional field then costs nothing.
    - `min_dimension_m` is `None`-able per Pipeline §2.2 — rooms without a
      strict short-side minimum (e.g., flexible utility) elide it.

    `__post_init__` keeps **minimal** value guards only (S05-D1, honest-fix —
    no NaN/inf/type hardening): non-empty `id`; `area_min_m2 >= 0`;
    `area_target_m2 >= area_min_m2` when both set; `min_dimension_m > 0` when
    set. Plus the role/corridor/anchor structural checks (S02-D9).
    """

    id: str
    role: Role
    usage: str | None
    area_min_m2: float
    required: bool
    area_target_m2: float | None = None
    min_dimension_m: float | None = None
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
        if self.anchor_id is not None and self.role != "vertical_circulation":
            # converse invariant (S07 review): anchor binding is vc-only (D004). A
            # non-vc spec with an anchor_id would carry it onto LabeledRoom (breaking
            # "anchor_id ⟺ vertical_circulation") and punch an unfilled hole.
            raise ValueError(
                f"SpaceUnitSpec {self.id!r}: anchor_id is only valid for "
                f"role='vertical_circulation', not role={self.role!r}"
            )
        # Minimal value guards (S05-D1).
        if not self.id:
            raise ValueError("SpaceUnitSpec: id must be a non-empty identifier")
        if self.area_min_m2 < 0:
            raise ValueError(
                f"SpaceUnitSpec {self.id!r}: area_min_m2 must be >= 0, got {self.area_min_m2}"
            )
        if self.area_target_m2 is not None and self.area_target_m2 < self.area_min_m2:
            raise ValueError(
                f"SpaceUnitSpec {self.id!r}: area_target_m2 ({self.area_target_m2}) "
                f"must be >= area_min_m2 ({self.area_min_m2})"
            )
        if self.min_dimension_m is not None and self.min_dimension_m <= 0:
            raise ValueError(
                f"SpaceUnitSpec {self.id!r}: min_dimension_m must be > 0 when set, "
                f"got {self.min_dimension_m}"
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
