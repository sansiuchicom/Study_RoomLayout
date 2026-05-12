"""Cut planning data structures.

Phase 0 keeps this intentionally small. Later phases will replace the trivial
single-zone plan with deterministic cut planners that emit ``CutRecord`` values
for atomic subdivision.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CutRecord:
    """A planned cut line and its provenance."""

    line: object
    label: str
    depth: int = 0
    family_id: int | None = None


@dataclass
class CandidateZone:
    """A provisional zone used only for face assignment."""

    zone_id: int
    polygon: object
    cut_history: list[str] = field(default_factory=list)
    family_id: int | None = None
    family_theta: float = 0.0


@dataclass
class PlanningResult:
    """Planner output consumed by subdivision and assignment stages."""

    candidates: list[CandidateZone]
    cuts: list[CutRecord] = field(default_factory=list)


def plan_initial_zones(footprint, *, k: int | None = None) -> PlanningResult:
    """Return the Phase 0 whole-footprint plan.

    ``k`` is accepted so the public API shape is stable before the real planner
    lands in Phase 3.
    """
    _ = k
    return PlanningResult(candidates=[CandidateZone(zone_id=0, polygon=footprint)])
