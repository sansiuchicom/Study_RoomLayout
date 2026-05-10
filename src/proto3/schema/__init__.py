"""proto3.schema — dataclass-based schema for proto3 candidate state.

See repo-root 002_Step02_CoreSchema_Plan.md §3 for module layout.
"""
from .input import BuildingInput, FloorInput, PersistentAnchor
from .program import ProgramInstance, SpaceUnitSpec, ClusterSpec, AccessPolicy
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
    # program (4)
    "ProgramInstance", "SpaceUnitSpec", "ClusterSpec", "AccessPolicy",
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
