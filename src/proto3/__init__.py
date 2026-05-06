"""proto3 — spine-first floor layout generation framework.

Canonical references (repo root):
    - 000_Pipeline_Overview.md         framework, stages, step map
    - 000_Architecture_Decisions.md    accepted decisions
    - 000_Progress_Tracker.md          current implementation status

Future top-level exports (placeholder; populated as Steps land):

    # Step 02 — Core Schema
    # from .config import RunConfig
    # from .debug import DebugArtifact
    # from .schema import BuildingInput, FloorInput, PersistentAnchor
    # from .schema import ProgramInstance, SpaceUnitSpec, ClusterSpec
    # from .schema import AccessPolicy
    # from .schema import Region, RegionSet, Atom, AtomSet
    # from .schema import ContactGraph
    # from .schema import HubCandidate, TerminalCandidate
    # from .schema import SpineCandidate, SlotCandidate, SeedCandidate
    # from .schema import GrowthResult, LayoutCandidate
    # from .schema import ValidationResult, FailureRecord, NoGoodRecord

This package currently exposes nothing. Importing it should succeed
(used by tests/test_smoke.py to verify packaging).
"""
