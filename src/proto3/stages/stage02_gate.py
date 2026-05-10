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
    rules = adapter.target_rules()

    # Multi-floor placeholder first — cheap and short-circuits non-apartment
    # multi-floor cases before geometry computation (Step 14 territory).
    check_multi_floor_feasibility(building, rules)

    # Step 06 single-floor scope (D024). Apartment fixtures always have
    # floors=[1]; the multi-floor gate above will have failed before this
    # for typologies where requires_single_floor=True with len != 1.
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
