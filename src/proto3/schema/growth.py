"""Growth schemas: GrowthResult, LayoutCandidate.

Stage 10 / Stage 13 outputs (Pipeline Overview §9). Access-preserving
atom growth (D011). LayoutCandidate is the unified Stage 13 output: valid
and invalid candidates share the same dataclass, discriminated by
`valid: bool` (D018). Invalid candidates populate `failure_records` and
`debug_artifact_refs`; valid candidates may carry empty defaults there.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .candidate import SeedCandidate, SpineCandidate
from .program import ProgramInstance
from .validation import FailureRecord, ValidationResult


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
    """Unified Stage 13 output for one candidate, valid or invalid (D018).

    `valid=True/False` discriminates the two cases. Invalid candidates must
    populate `failure_records` (Pipeline Overview §9 Stage 13 contract).
    Valid candidates may carry empty defaults on the failure-side fields.
    Search Orchestrator (Pipeline Overview §10) accesses `result.valid` /
    `result.failure_records` directly without isinstance checks.
    """
    candidate_id: str = ""
    valid: bool = False
    program_instance: ProgramInstance | None = None
    spine_candidate: SpineCandidate | None = None
    seed_candidates: list[SeedCandidate] = field(default_factory=list)
    growth_result: GrowthResult | None = None
    final_geometry: dict | None = None  # TBD: per-space polygons
    # D018 unified-output fields:
    validation_result: ValidationResult | None = None  # post-repair (Stage 13) result
    failure_records: list[FailureRecord] = field(default_factory=list)  # invalid: must populate
    debug_artifact_refs: dict[str, str] = field(default_factory=dict)  # {kind: path}
    provenance: dict = field(default_factory=dict)  # which spine/seed/atom path led here — TBD typed
    output_artifacts: dict = field(default_factory=dict)  # final JSON/SVG paths — TBD typed
