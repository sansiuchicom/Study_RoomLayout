"""Validation schemas: ValidationResult, FailureRecord, NoGoodRecord.

Stage 11/13 outputs (Pipeline Overview §6.5, §9, §11). Pre-repair and
post-repair validation (D009). Failure-to-pruning backtracking (D010).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of checking a candidate against hard/soft constraints (§6.5).

    Used for both pre-repair (Stage 11) and post-repair (Stage 13) validation
    via the `stage` field (D009).
    """
    stage: str = ""  # "pre_repair" | "post_repair"
    valid: bool = False
    hard_failures: list[str] = field(default_factory=list)
    repairable_defects: list[str] = field(default_factory=list)
    soft_violations: list[str] = field(default_factory=list)
    # TBD: typed Defect dataclass


@dataclass
class FailureRecord:
    """Evidence-backed diagnosis of why a candidate failed (§6.5, §11).

    See Pipeline Overview §11 for the canonical YAML example
    (failure_type, evidence, diagnosis, learned_constraint, retry_policy).
    """
    failure_type: str = ""  # e.g., "primary_door_boundary_missing"
    affected_space: str | None = None
    detected_stage: str | None = None
    evidence: dict = field(default_factory=dict)
    diagnosis: dict = field(default_factory=dict)  # likely_layer, confidence, reason
    learned_constraint: dict | None = None
    retry_policy: dict | None = None  # start_level, escalation


@dataclass
class NoGoodRecord:
    """Search-space pruning record from repeated/clear failures (§11)."""
    reason: str = ""
    pattern: dict = field(default_factory=dict)
    action: dict = field(default_factory=dict)  # reject_*, penalize_*, ...
    # TBD: confidence, expiry, scope (per-run vs persistent)


class ProgramInstantiationFailure(Exception):
    """Stage 01 cardinality / role-validity gate failure (D004 / DH-004 regression, S04-D11).

    Raised when a role required by `TargetAdapter.target_rules().min_cardinality`
    is under-supplied by `BuildingInput.program_request`, when an unknown role
    is encountered (S06-D10), or when duplicate `name` values appear (S06-D7).
    Step 06+ may catch this and convert it into a ValidationResult.
    """

    def __init__(self, failure: FailureRecord, message: str | None = None) -> None:
        self.failure = failure
        super().__init__(message or failure.failure_type or "program instantiation failed")


# Stage 02 Domain Feasibility Gate failures (S06-D6, D020). Parent + 3 children;
# each holds a FailureRecord (S04-D11 pattern). Stage 02 invokes 3 active gates
# (area/dim/multi-floor); AccessSchemaFailure is dormant scaffold through Step 06
# and activates at Step 09-10 when AccessPolicy gets concrete instances (Plan Def-9).


class DomainGateFailure(Exception):
    """Stage 02 Domain Feasibility Gate failure parent (S06-D6, D020).

    Subclassed by `AreaGateFailure`, `DimGateFailure`, `AccessSchemaFailure`.
    Catch the parent for any-gate handling, the child for gate-specific logic.
    """

    def __init__(self, failure: FailureRecord, message: str | None = None) -> None:
        self.failure = failure
        super().__init__(message or failure.failure_type or "domain gate failed")


class AreaGateFailure(DomainGateFailure):
    """Total required min_area exceeds gross footprint × density_factor.

    D023 — required-only summation. D024 — gross footprint (anchor-aware
    refinement deferred to Step 12 / Stage 11).
    """


class DimGateFailure(DomainGateFailure):
    """A required space's min_dimension_mm exceeds the footprint bounding box short side.

    Bbox-level check only (S06-D12). LIR-aware refinement deferred to Step 12.
    """


class AccessSchemaFailure(DomainGateFailure):
    """Access policy schema invariant violated (dormant in Step 06).

    Raised by `proto3.constraints.gates.check_access_schema`. Stage 02 does not
    invoke this gate during Step 06 — `ProgramRequest` is slim (S06-D8) so no
    AccessPolicy reaches Stage 02. Activation = Step 09-10 (Plan Def-9).
    """
