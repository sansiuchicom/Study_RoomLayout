"""Candidate schemas: HubCandidate, TerminalCandidate, SpineCandidate, SlotCandidate, SeedCandidate.

Stage 07-09 outputs (Pipeline Overview §6.4, §9). Spine-first candidate
search (D007). Each candidate carries provenance (Pipeline Overview §12.1).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HubCandidate:
    """Primary access host / central distribution space candidate."""
    candidate_id: str = ""
    region_id: str = ""  # which region this hub centers in
    score: float | None = None
    # TBD: explicit hub location, role (living vs hall vs explicit corridor)


@dataclass
class TerminalCandidate:
    """Cluster target location (§6.4). Not a final room polygon."""
    candidate_id: str = ""
    cluster_name: str = ""  # ClusterSpec.name reference
    region_id: str = ""  # terminal location
    capacity_estimate: float | None = None
    score: float | None = None


@dataclass
class SpineCandidate:
    """Floor-rooted access skeleton (D007). Trunk → branch → stub."""
    candidate_id: str = ""
    floor_root: tuple[float, float] = (0.0, 0.0)
    hub_id: str = ""  # HubCandidate.candidate_id
    trunk_atom_ids: list[str] = field(default_factory=list)
    branches: list[dict] = field(default_factory=list)  # TBD: typed Branch later
    branch_cost_total: float | None = None
    # TBD: stub_atom_ids, attachment_hints, reserved access atoms


@dataclass
class SlotCandidate:
    """Branch-adjacent attachment opportunity (§6.4)."""
    candidate_id: str = ""
    branch_id: str = ""  # which branch in SpineCandidate
    boundary_atom_ids: list[str] = field(default_factory=list)
    door_boundary_evidence_mm: float | None = None


@dataclass
class SeedCandidate:
    """Initial hypothesis for where a SpaceUnit starts growing (§6.4).

    Provenance fields (§12.1) are first-class — terminal, branch, slot,
    parent region, and initial boundary evidence are required for failure
    diagnosis (D010).
    """
    candidate_id: str = ""
    space_name: str = ""  # SpaceUnitSpec.name
    slot_id: str | None = None  # primary slot
    seed_atom_ids: list[str] = field(default_factory=list)  # patch
    parent_region_id: str | None = None
    initial_boundary_evidence: dict | None = None
