"""Public zoning entry point for the atomic subdivision testfield."""

from __future__ import annotations

from dataclasses import dataclass

from .assignment import Zone, assign_faces_to_candidates
from .planner import PlanningResult, plan_initial_zones
from .subdivision import SubdivisionResult, build_atomic_faces
from .validation import PartitionReport, validate_partition


@dataclass
class ZoningResult:
    zones: list[Zone]
    planning: PlanningResult
    subdivision: SubdivisionResult
    validation: PartitionReport

    def zone_dicts(self) -> list[dict]:
        return [zone.as_dict() for zone in self.zones]


def zone_footprint(
    footprint,
    *,
    k: int | None = None,
    precision: float = 0.001,
    tolerance: float = 1e-6,
) -> ZoningResult:
    """Run the Phase 0 atomic-zoning scaffold."""
    planning = plan_initial_zones(footprint, k=k)
    subdivision = build_atomic_faces(
        footprint,
        [cut.line for cut in planning.cuts],
        precision=precision,
    )
    zones = assign_faces_to_candidates(subdivision.faces, planning.candidates)
    validation = validate_partition(
        footprint,
        zones,
        precision=precision,
        tolerance=tolerance,
    )
    return ZoningResult(
        zones=zones,
        planning=planning,
        subdivision=subdivision,
        validation=validation,
    )
