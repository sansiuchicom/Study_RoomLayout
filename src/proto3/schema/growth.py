"""Growth schemas: GrowthResult, LayoutCandidate.

Stage 10 / Stage 13 outputs (Pipeline Overview §9). Access-preserving
atom growth (D011). LayoutCandidate is the final assembled output for a
valid candidate; invalid candidates use validation.FailureRecord.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .candidate import SeedCandidate, SpineCandidate
from .program import ProgramInstance


@dataclass
class GrowthResult:
    """Atom assignment + grown space patches + step trace (Stage 10)."""
    atom_assignment: dict[str, str] = field(default_factory=dict)  # {atom_id: space_name}
    grown_space_patches: dict[str, list[str]] = field(default_factory=dict)  # {space_name: [atom_ids]}
    growth_steps: list[dict] = field(default_factory=list)  # TBD: typed GrowthStep later
    access_evidence: dict | None = None  # access preservation (D011)
    boundary_evidence: dict | None = None  # required boundary preservation


@dataclass
class LayoutCandidate:
    """Final assembled output for one candidate (Stage 13)."""
    candidate_id: str = ""
    valid: bool = False
    program_instance: ProgramInstance | None = None
    spine_candidate: SpineCandidate | None = None
    seed_candidates: list[SeedCandidate] = field(default_factory=list)
    growth_result: GrowthResult | None = None
    final_geometry: dict | None = None  # TBD: per-space polygons
