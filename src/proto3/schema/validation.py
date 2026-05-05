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
