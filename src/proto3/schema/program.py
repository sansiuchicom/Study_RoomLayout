"""Program schemas: ProgramInstance, SpaceUnitSpec, ClusterSpec, AccessPolicy.

Stage 01 outputs (Pipeline Overview §6.2, §9). ProgramInstance owns
cardinality (D004); ClusterSpec is grouping only.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SpaceUnitSpec:
    """One required or optional generated space + its constraints (§6.2)."""
    name: str = ""  # e.g., "bedroom_2", "bathroom_shared"
    role: str = ""  # public | private | service | wet | hub | corridor
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
class ProgramInstance:
    """Concrete required spaces for a candidate. Source of cardinality (D004).

    Regression rule (D004): a required apartment bathroom count of zero is a
    ProgramInstantiationFailure, not a growth failure.
    """
    space_units: list[SpaceUnitSpec] = field(default_factory=list)
    clusters: list[ClusterSpec] = field(default_factory=list)
    access_policies: list[AccessPolicy] = field(default_factory=list)
    # TBD: source ProgramSpec id, total area budget
