"""Program schemas: ProgramRequest, ProgramInstance, SpaceUnitSpec, ClusterSpec, AccessPolicy.

Stage 01 outputs (Pipeline Overview §6.2, §9). ProgramInstance owns
cardinality (D004); ClusterSpec is grouping only.

Step 06 additions (S06-D8, D10):
- `Role` Literal — strict 6-role enum (S06-D10)
- `ProgramRequest` dataclass — typed input layer replacing the raw `dict`
  shape used through Step 04 (S06-D8). Slim by design: `spaces` only.
  ClusterSpec / AccessPolicy instantiation lives in Step 09-10 (Plan Def-9).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# 6 canonical roles (Pipeline §6.2). Expand only via explicit schema diff (S06-D10).
Role = Literal["public", "private", "service", "wet", "hub", "corridor"]


@dataclass
class SpaceUnitSpec:
    """One required or optional generated space + its constraints (§6.2)."""
    name: str = ""  # e.g., "bedroom_2", "bathroom_shared"
    role: Role | None = None  # None = unset placeholder; Stage 01 fails if None at instantiation (S06-D10)
    required: bool = True
    min_area_m2: float | None = None
    max_area_m2: float | None = None
    preferred_area_m2: float | None = None
    min_dimension_mm: int | None = None
    # TBD: aspect_ratio range, exterior_contact preference, wet/service proximity


@dataclass
class ClusterSpec:
    """Functional/access grouping. Does NOT create cardinality (D004)."""
    name: str = ""
    member_space_names: list[str] = field(default_factory=list)
    # TBD: cluster access policy (terminal preference, hub adjacency)


@dataclass
class AccessPolicy:
    """Primary/dependent access rules for a space (§6.2)."""
    space_name: str = ""  # SpaceUnitSpec.name reference
    primary_access_required: bool = True
    dependent_on_space: str | None = None  # for dependent rooms
    door_capable_boundary_mm: int | None = None  # min door boundary
    # TBD: access host preference, exterior access rule


@dataclass
class ProgramRequest:
    """Typed program input — replaces the raw `dict` shape used through Step 04 (S06-D8).

    Slim by design: only `spaces` is typed here. ClusterSpec / AccessPolicy
    instantiation lives in Step 09-10 (Plan Def-9).

    `__post_init__` enforces that `spaces` is `list[SpaceUnitSpec]` — this is
    the strict-deserialize boundary for the spaces region (Plan §0 산출물 7,
    외부 review #2; full `list[T]` deserialize hardening = Plan Def-7, Step 08).
    """
    spaces: list[SpaceUnitSpec] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.spaces, list):
            raise ValueError(
                f"ProgramRequest.spaces must be list[SpaceUnitSpec], "
                f"got {type(self.spaces).__name__}"
            )
        for i, s in enumerate(self.spaces):
            if not isinstance(s, SpaceUnitSpec):
                raise ValueError(
                    f"ProgramRequest.spaces[{i}] must be SpaceUnitSpec, "
                    f"got {type(s).__name__}"
                )


@dataclass
class ProgramInstance:
    """Concrete required spaces for a candidate. Source of cardinality (D004).

    Regression rule (D004): a required apartment bathroom count of zero is a
    ProgramInstantiationFailure, not a growth failure.
    """
    space_units: list[SpaceUnitSpec] = field(default_factory=list)
    clusters: list[ClusterSpec] = field(default_factory=list)
    access_policies: list[AccessPolicy] = field(default_factory=list)
    # TBD: source ProgramSpec id, total area budget
