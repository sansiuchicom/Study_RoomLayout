"""Domain feasibility gates as pure functions (Step 06, S06-D13, D020).

Each gate is `(inputs) -> None` and raises a subclass of
`proto3.schema.validation.DomainGateFailure` on infeasibility.

Stage 02 invokes 3 of these (area, dim, multi-floor) per D020. The 4th
(`check_access_schema`) is **dormant scaffold** through Step 06 — function
signature exists for unit testing only; Stage 02 does not call it because
`ProgramRequest` is slim (S06-D8) and carries no `access_policies`.
Activation = Step 09-10 when Hub/Spine/Slot generation introduces concrete
`AccessPolicy` instances (Plan Def-9).

Required-only summation (D023): `check_min_area` and `check_min_dim` consider
only `SpaceUnitSpec.required = True` spaces. Optional spaces are layout-
best-effort and do not influence Stage 02 admission.

Future binding to Stage 11/13 (D013 / Plan Def-5) — Step 12 territory.
"""
from __future__ import annotations

from proto3.schema.input import BuildingInput
from proto3.schema.program import ProgramInstance
from proto3.schema.validation import (
    AccessSchemaFailure,
    AreaGateFailure,
    DimGateFailure,
    DomainGateFailure,
    FailureRecord,
)
from proto3.target import TargetRules


def check_min_area(
    program: ProgramInstance,
    rules: TargetRules,
    footprint_area_m2: float,
) -> None:
    """Stage 02 area gate. Total required min_area ≤ gross footprint × density_factor.

    Args:
        program: ProgramInstance after Stage 01 (default fill applied per S06-D7).
        rules:   TargetRules from the active TargetAdapter.
        footprint_area_m2: Gross footprint area in m². Caller computes (e.g.,
            via `shapely.Polygon(floor.footprint).area / 1e6` for mm vertices).

    Raises:
        AreaGateFailure: if `Σ required min_area > footprint × density_factor`.
            Per D023 (required-only) and D024 (gross footprint, anchor-aware
            refinement deferred to Step 12).
    """
    required = [u for u in program.space_units if u.required]
    total_min_area = sum(
        (u.min_area_m2 or 0.0) for u in required
    )
    capacity = footprint_area_m2 * rules.density_factor

    if total_min_area > capacity:
        raise AreaGateFailure(FailureRecord(
            failure_type="domain_area_gate_fail",
            detected_stage="02",
            evidence={
                "total_required_area_m2": round(total_min_area, 4),
                "footprint_area_m2": round(footprint_area_m2, 4),
                "density_factor": rules.density_factor,
                "usable_capacity_m2": round(capacity, 4),
                "required_space_count": len(required),
            },
            diagnosis={
                "likely_layer": "program_request",
                "reason": (
                    f"required spaces sum to {total_min_area:.2f} m² but usable "
                    f"capacity is {capacity:.2f} m² (footprint {footprint_area_m2:.2f} × "
                    f"density {rules.density_factor})"
                ),
            },
        ))


def check_min_dim(
    program: ProgramInstance,
    footprint_bbox_short_side_mm: int,
) -> None:
    """Stage 02 dim gate. Largest required min_dimension ≤ footprint bbox short side.

    Bbox-level only — LIR-aware refinement deferred to Step 12 (Plan Def-4).
    Per D023, only required=True spaces contribute.

    Args:
        program: ProgramInstance after Stage 01.
        footprint_bbox_short_side_mm: Shorter side of footprint axis-aligned
            bounding box in mm. Caller computes from floor.footprint vertices.

    Raises:
        DimGateFailure: if any required space's `min_dimension_mm` exceeds
            the bbox short side.
    """
    required = [u for u in program.space_units if u.required]
    if not required:
        return  # vacuously OK — caught upstream by Stage 01 cardinality

    candidates = [
        (u.name, u.min_dimension_mm)
        for u in required
        if u.min_dimension_mm is not None
    ]
    if not candidates:
        return  # no min_dimension constraints declared

    worst_name, worst_dim = max(candidates, key=lambda nd: nd[1])

    if worst_dim > footprint_bbox_short_side_mm:
        raise DimGateFailure(FailureRecord(
            failure_type="domain_dim_gate_fail",
            affected_space=worst_name,
            detected_stage="02",
            evidence={
                "space_name": worst_name,
                "min_dimension_mm": worst_dim,
                "footprint_bbox_short_side_mm": footprint_bbox_short_side_mm,
            },
            diagnosis={
                "likely_layer": "program_request",
                "reason": (
                    f"space {worst_name!r} requires min_dimension {worst_dim}mm "
                    f"but footprint bbox short side is {footprint_bbox_short_side_mm}mm"
                ),
            },
        ))


def check_access_schema(program: ProgramInstance) -> None:
    """Access policy schema invariants. **Dormant scaffold in Step 06.**

    Stage 02 does not call this during Step 06 — `ProgramRequest` is slim
    (S06-D8, spaces only) so `program.access_policies` is empty by
    construction. Function exists for unit testing the schema invariants
    that Step 09-10 will exercise once AccessPolicy gets concrete data
    (Plan Def-9).

    Invariants checked:
      - `dependent_on_space` references an existing `SpaceUnitSpec.name`.
      - `door_capable_boundary_mm` (if set) is positive.

    Raises:
        AccessSchemaFailure: on first invariant violation.
    """
    space_names = {u.name for u in program.space_units}

    for policy in program.access_policies:
        if (policy.dependent_on_space is not None
                and policy.dependent_on_space not in space_names):
            raise AccessSchemaFailure(FailureRecord(
                failure_type="access_dependent_space_unknown",
                affected_space=policy.space_name,
                detected_stage="02",
                evidence={
                    "policy_space_name": policy.space_name,
                    "dependent_on_space": policy.dependent_on_space,
                    "known_space_names": sorted(space_names),
                },
                diagnosis={
                    "likely_layer": "program_request",
                    "reason": (
                        f"policy for {policy.space_name!r} depends on "
                        f"{policy.dependent_on_space!r} but no such space exists"
                    ),
                },
            ))

        if (policy.door_capable_boundary_mm is not None
                and policy.door_capable_boundary_mm <= 0):
            raise AccessSchemaFailure(FailureRecord(
                failure_type="access_door_boundary_invalid",
                affected_space=policy.space_name,
                detected_stage="02",
                evidence={
                    "policy_space_name": policy.space_name,
                    "door_capable_boundary_mm": policy.door_capable_boundary_mm,
                },
                diagnosis={
                    "likely_layer": "program_request",
                    "reason": "door_capable_boundary_mm must be positive when set",
                },
            ))


def check_multi_floor_feasibility(
    building: BuildingInput,
    rules: TargetRules,
) -> None:
    """Multi-floor feasibility placeholder. Step 14 territory (Plan Def-8).

    Step 06 currently enforces a single-floor assumption per D024:
    if the typology requires single floor (`rules.requires_single_floor`)
    and the building reports more than one floor, fail.

    Multi-floor area / dim allocation across floors is deferred to Step 14
    when persistent anchors and floor-rooted layout are wired up.

    Raises:
        DomainGateFailure (parent class — no specific subclass yet, since
            multi-floor handling is a future Step's territory).
    """
    n_floors = len(building.floors)

    if rules.requires_single_floor and n_floors != 1:
        raise DomainGateFailure(FailureRecord(
            failure_type="domain_multi_floor_not_supported",
            detected_stage="02",
            evidence={
                "target_type": rules.target_type,
                "requires_single_floor": True,
                "actual_floor_count": n_floors,
            },
            diagnosis={
                "likely_layer": "building_input",
                "reason": (
                    f"target_type {rules.target_type!r} requires single floor "
                    f"but building has {n_floors} floors (Step 14 territory)"
                ),
            },
        ))
