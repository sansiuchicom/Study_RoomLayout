"""Program schemas: ProgramRequest, ProgramInstance, SpaceUnitSpec, ClusterSpec, AccessPolicy.

Stage 01 outputs (Pipeline Overview §6.2, §9). ProgramInstance owns
cardinality (D004); ClusterSpec is grouping only.

Step 06 additions (S06-D8, D10):
- `Role` Literal — strict 6-role enum (S06-D10)
- `ProgramRequest` dataclass — typed input layer replacing the raw `dict`
  shape used through Step 04 (S06-D8). Slim by design: `spaces` only.
  ClusterSpec / AccessPolicy instantiation lives in Step 09-10 (Plan Def-9).
- `SpaceUnitSpec.__post_init__` value/type validation (Step 06 merge-prep,
  third external review #1). Catches the silent-fail surface left by
  `from_dict` letting primitives through unchecked.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

# 6 canonical roles (Pipeline §6.2). Expand only via explicit schema diff (S06-D10).
Role = Literal["public", "private", "service", "wet", "hub", "corridor"]


@dataclass
class SpaceUnitSpec:
    """One required or optional generated space + its constraints (§6.2).

    `__post_init__` enforces type + range invariants so that bogus values
    (negative area, string-typed bool, NaN, max < min, etc.) fail at
    construction instead of polluting Stage 01/02 evidence with confusing
    inputs. Default-constructed `SpaceUnitSpec()` is intentionally still
    valid (placeholder semantics for `test_smoke` and similar schema-default
    checks); semantic validation (e.g., non-empty `name`, valid `role`)
    happens in Stage 01.
    """
    name: str = ""  # e.g., "bedroom_2", "bathroom_shared"
    role: Role | None = None  # None = unset placeholder; Stage 01 fails if None at instantiation (S06-D10)
    required: bool = True
    min_area_m2: float | None = None
    max_area_m2: float | None = None
    preferred_area_m2: float | None = None
    min_dimension_mm: int | None = None
    # TBD: aspect_ratio range, exterior_contact preference, wet/service proximity

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise ValueError(
                f"SpaceUnitSpec.name must be str, "
                f"got {type(self.name).__name__}={self.name!r}"
            )
        # bool is a subclass of int; `type(x) is bool` keeps int-typed-bool out.
        if type(self.required) is not bool:
            raise ValueError(
                f"SpaceUnitSpec.required must be bool, "
                f"got {type(self.required).__name__}={self.required!r}"
            )
        # role: None or string (Role Literal — runtime not strictly enforced
        # here; Stage 01 catches None / unknown).
        if self.role is not None and not isinstance(self.role, str):
            raise ValueError(
                f"SpaceUnitSpec.role must be str (Role Literal) or None, "
                f"got {type(self.role).__name__}={self.role!r}"
            )
        # area fields: None or finite number ≥ 0. bool excluded explicitly
        # (subclass of int).
        for fname in ("min_area_m2", "max_area_m2", "preferred_area_m2"):
            v = getattr(self, fname)
            if v is None:
                continue
            if (isinstance(v, bool)
                    or not isinstance(v, (int, float))
                    or math.isnan(v) or math.isinf(v)
                    or v < 0):
                raise ValueError(
                    f"SpaceUnitSpec.{fname} must be None or finite number ≥ 0, "
                    f"got {v!r}"
                )
        if self.min_dimension_mm is not None:
            if (type(self.min_dimension_mm) is not int
                    or self.min_dimension_mm <= 0):
                raise ValueError(
                    f"SpaceUnitSpec.min_dimension_mm must be None or positive int, "
                    f"got {self.min_dimension_mm!r}"
                )
        # ordering: max ≥ min when both set
        if (self.min_area_m2 is not None
                and self.max_area_m2 is not None
                and self.max_area_m2 < self.min_area_m2):
            raise ValueError(
                f"SpaceUnitSpec.max_area_m2 ({self.max_area_m2}) must be ≥ "
                f"min_area_m2 ({self.min_area_m2})"
            )


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
