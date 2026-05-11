"""proto3.schema — dataclass-based schema for proto3 candidate state.

See repo-root 002_Step02_CoreSchema_Plan.md §3 for module layout.
"""
from .input import BuildingInput, FloorInput, PersistentAnchor
from .program import ProgramRequest, ProgramInstance, SpaceUnitSpec, ClusterSpec, AccessPolicy, Role
from .region_atom import Region, RegionSet, Atom, AtomSet, ContactGraph
from .geometry import GeometricPiece, Decomposition
from .candidate import (
    HubCandidate,
    TerminalCandidate,
    SpineCandidate,
    SlotCandidate,
    SeedCandidate,
)
from .growth import GrowthResult, LayoutCandidate
from .validation import ValidationResult, FailureRecord, NoGoodRecord

__all__ = [
    # input (3)
    "BuildingInput", "FloorInput", "PersistentAnchor",
    # program (5 dataclasses + Role Literal) — Step 06 added ProgramRequest + Role (S06-D8, D10)
    "ProgramRequest", "ProgramInstance", "SpaceUnitSpec", "ClusterSpec", "AccessPolicy",
    "Role",
    # region/atom (5)
    "Region", "RegionSet", "Atom", "AtomSet", "ContactGraph",
    # geometry (2) — Step 05 D019
    "GeometricPiece", "Decomposition",
    # candidate (5)
    "HubCandidate", "TerminalCandidate", "SpineCandidate", "SlotCandidate", "SeedCandidate",
    # growth (2)
    "GrowthResult", "LayoutCandidate",
    # validation (3)
    "ValidationResult", "FailureRecord", "NoGoodRecord",
]
