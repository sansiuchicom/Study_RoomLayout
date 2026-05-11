"""Stage 02 — Domain Feasibility Gate (S06-D6, D012, D013, D020, D023, D024).

Step 06 §4.6: wires the active 3 gates from `proto3.constraints.gates`
(area + dim + multi-floor) into a Stage 02 run function. Single-floor
assumption per D024 — uses `floors[0]` only; multi-floor area allocation
is Step 14 territory (Plan Def-8).

Stage 02 is **fail-only** (D020) — accepts the input ProgramInstance
unchanged on success, raises a `DomainGateFailure` subclass on any gate
failure. Repair (drop optional spaces, retry) belongs to Stage 12.

`check_access_schema` (the 4th gate function) is **dormant** in Step 06
(S06-D12) — not invoked here. `ProgramRequest` is slim (S06-D8) so
`access_policies` is empty by construction; activation lands at
Step 09-10 when Hub/Spine/Slot generation introduces concrete
`AccessPolicy` instances (Plan Def-9).
"""
from __future__ import annotations

from shapely.geometry import Polygon

from proto3.constraints.gates import (
    check_min_area,
    check_min_dim,
    check_multi_floor_feasibility,
)
from proto3.schema.input import BuildingInput
from proto3.schema.program import ProgramInstance
from proto3.schema.validation import DomainGateFailure, FailureRecord
from proto3.target import TargetAdapter


def run(
    building: BuildingInput,
    *,
    instance: ProgramInstance,
    adapter: TargetAdapter,
) -> ProgramInstance:
    """Run Stage 02 gates against a Stage 01-produced ProgramInstance.

    Args:
        building:  BuildingInput from Stage 00.
        instance:  ProgramInstance from Stage 01 (concrete after default fill).
        adapter:   TargetAdapter providing TargetRules.

    Returns:
        The input `instance` unchanged on accept.

    Raises:
        AreaGateFailure: total required area > gross footprint × density_factor.
        DimGateFailure:  any required min_dimension > footprint bbox short side.
        DomainGateFailure: parent class — multi-floor not supported when
            `requires_single_floor=True` and floors != 1.
    """
    # Defense in depth (merge-prep, third external review #2). Adapter
    # already validates target_type at load_fixture time, but Stage 02 can
    # be called directly without going through Stage 00.
    if building.target_type != adapter.target_type:
        raise ValueError(
            f"Stage 02: building.target_type={building.target_type!r} "
            f"does not match adapter.target_type={adapter.target_type!r}"
        )

    rules = adapter.target_rules()

    # Stage 02 single-floor scope, unconditional (merge-prep, third external
    # review #3). Even when rules.requires_single_floor=False (house/hotel),
    # Step 06's Stage 02 cannot aggregate area/dim across floors — fail loud
    # rather than silently evaluate floors[0] only. Multi-floor allocation is
    # Step 14 territory (Plan Def-8). Unblock at that point by replacing this
    # guard with per-floor aggregation logic.
    if len(building.floors) != 1:
        raise DomainGateFailure(FailureRecord(
            failure_type="stage02_multi_floor_unsupported",
            detected_stage="02",
            evidence={"actual_floor_count": len(building.floors)},
            diagnosis={
                "likely_layer": "scope",
                "reason": "Stage 02 single-floor scope; multi-floor = Step 14 (Plan Def-8)",
            },
        ))

    # Multi-floor placeholder gate (apartment-only ergonomics — fails fast
    # if apartment fixture somehow has multiple floors. Above guard already
    # rejects len != 1; this remains as a parameterized check for future
    # binding to Stage 11/13 per Plan Def-5).
    check_multi_floor_feasibility(building, rules)

    # Step 06 single-floor scope (D024). Apartment fixtures always have
    # floors=[1]; the multi-floor guard above ensures we never see anything else.
    floor = building.floors[0]
    polygon = Polygon(floor.footprint)

    # FloorInput.footprint vertices are in mm; shapely.area returns mm².
    # Convert to m² for the area gate (whose threshold is in m²).
    footprint_area_m2 = polygon.area / 1_000_000.0

    minx, miny, maxx, maxy = polygon.bounds
    bbox_short_side_mm = int(min(maxx - minx, maxy - miny))

    check_min_area(instance, rules, footprint_area_m2)
    check_min_dim(instance, bbox_short_side_mm)

    # check_access_schema is dormant in Step 06 (S06-D12) — not invoked.

    return instance
