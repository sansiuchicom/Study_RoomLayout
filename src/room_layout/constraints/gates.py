"""Domain feasibility gates as pure functions (Step 05, S05-D4 / proto3:D020).

Each gate is `(...) -> None` and raises a `DomainGateFailure` subclass on
infeasibility, returning `None` on pass. They are **pure**: no side effects,
output determined entirely by inputs.

Injection split (S05-D2): per-typology *domain values* (`density_factor`,
`requires_single_floor`) arrive as primitive keyword arguments — the gate
depends only on the scalar it uses, not on a whole `TargetRules` object. The
*program data* (`list[SpaceUnitSpec]`) is passed directly (S05-D4 option 가):
filtering required spaces and extracting area/dim fields is the gate's own
essential logic, not something the caller pre-computes.

Required-only (proto3:D023): `check_min_area` / `check_min_dim` consider only
`SpaceUnitSpec.required = True` spaces. Optional spaces are layout-best-effort
and never cause admission failure; dropping them is a later-stage repair
concern (fail-only, D020), not a gate concern.

Units (S05-D4): metres throughout (`area_min_m2` m², `min_dimension_m` m,
`footprint_*` m / m²) — proto3 was mm; the new schema is m.

These are the **aggregate admission** gates (run pre-growth: does the program
fit at all?). The per-room post-growth check (this grown room is below its
own `area_min_m2` → reject) is a distinct Step 07 binding, not here.
"""

from __future__ import annotations

from room_layout.schema.failure import (
    AreaGateFailure,
    DimGateFailure,
    DomainGateFailure,
    FailureRecord,
)
from room_layout.schema.program import SpaceUnitSpec


def check_min_area(
    specs: list[SpaceUnitSpec],
    *,
    footprint_area_m2: float,
    density_factor: float,
) -> None:
    """Area admission gate: Σ required `area_min_m2` ≤ usable capacity.

    Usable capacity is `footprint_area_m2 * density_factor` (gross footprint
    discounted by the typology's usable fraction). Anchor-aware / per-room
    refinement is deferred (Step 07).

    Raises:
        AreaGateFailure: if total required minimum area exceeds capacity.
    """
    required = [s for s in specs if s.required]
    total_min_area = sum(s.area_min_m2 for s in required)
    capacity = footprint_area_m2 * density_factor

    if total_min_area > capacity:
        raise AreaGateFailure(FailureRecord(
            code="DOMAIN_AREA_GATE_FAIL",
            stage="02",
            message=(
                f"required spaces sum to {total_min_area:.2f} m² but usable "
                f"capacity is {capacity:.2f} m² "
                f"(footprint {footprint_area_m2:.2f} × density {density_factor})"
            ),
            data={
                "total_required_area_m2": round(total_min_area, 4),
                "footprint_area_m2": round(footprint_area_m2, 4),
                "density_factor": density_factor,
                "usable_capacity_m2": round(capacity, 4),
                "required_space_count": len(required),
            },
        ))


def check_min_dim(
    specs: list[SpaceUnitSpec],
    *,
    footprint_bbox_short_side_m: float,
) -> None:
    """Dimensional admission gate: largest required `min_dimension_m` fits.

    Bbox-level only — the largest required short-side minimum must not exceed
    the footprint bounding box's short side. Spaces with `min_dimension_m is
    None` declare no short-side minimum and are skipped (the field is optional,
    unlike the now-required `area_min_m2`). LIR-aware refinement is deferred
    (Step 07).

    Raises:
        DimGateFailure: if any required space's `min_dimension_m` exceeds the
            bbox short side.
    """
    required = [s for s in specs if s.required]
    candidates = [s for s in required if s.min_dimension_m is not None]
    if not candidates:
        return  # no short-side minimums declared → vacuously OK

    worst = max(candidates, key=lambda s: s.min_dimension_m)
    if worst.min_dimension_m > footprint_bbox_short_side_m:
        raise DimGateFailure(FailureRecord(
            code="DOMAIN_DIM_GATE_FAIL",
            stage="02",
            message=(
                f"space {worst.id!r} requires min_dimension "
                f"{worst.min_dimension_m} m but footprint bbox short side is "
                f"{footprint_bbox_short_side_m} m"
            ),
            data={
                "space_id": worst.id,
                "min_dimension_m": worst.min_dimension_m,
                "footprint_bbox_short_side_m": footprint_bbox_short_side_m,
            },
        ))


def check_multi_floor_feasibility(
    *,
    n_floors: int,
    requires_single_floor: bool,
) -> None:
    """Multi-floor admission gate (single-floor v1 scope, S05-D6).

    Fails when the typology requires a single floor but the building reports
    more than one. Multi-floor area allocation across floors is deferred to
    the Step 10 multi-floor orchestrator. Raises the **base**
    `DomainGateFailure` (no dedicated subclass — multi-floor handling is a
    future Step's territory).

    Raises:
        DomainGateFailure: if `requires_single_floor` and `n_floors != 1`.
    """
    if requires_single_floor and n_floors != 1:
        raise DomainGateFailure(FailureRecord(
            code="DOMAIN_MULTI_FLOOR_NOT_SUPPORTED",
            stage="02",
            message=(
                f"typology requires a single floor but building has "
                f"{n_floors} floors (Step 10 territory)"
            ),
            data={
                "requires_single_floor": True,
                "actual_floor_count": n_floors,
            },
        ))


def check_access_schema(specs: list[SpaceUnitSpec]) -> None:
    """Access-policy schema gate. **Documented no-op stub in Step 05 (S05-D4).**

    The current schema has no `AccessPolicy` concept (`SpaceUnitSpec` carries
    no access rules), so there is nothing to validate — this is a stub, not a
    speculative guard (honest-fix). It will gain real invariants (dependent-
    space references exist, door-boundary widths positive, …) at Step 09-10
    when Hub/Spine/Slot generation introduces concrete access policies.

    Never raises in v1.
    """
    return None
