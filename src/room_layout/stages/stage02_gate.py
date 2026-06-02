"""Stage 02 — floor-scoped domain feasibility gate (S05-D6, proto3:D020).

Runs the **floor-level** admission gates against a single `FloorShape`: the
program's required spaces must fit the floor by area (`check_min_area`) and by
short-side dimension (`check_min_dim`). Fail-only (D020) — returns the specs
unchanged on accept, raises a `DomainGateFailure` subclass on the first gate
that fails.

Altitude boundary (S05-D6): `check_multi_floor_feasibility` is a *building*-
level question (is the whole building single-floor?) and is **not** invoked
here — the Step 07 `run()` caller, which owns `n_floors`, runs it. This keeps
stage02's input to one `FloorShape` (no `ShapeInput` / `n_floors` leakage) and
matches gate altitude to caller altitude.

Geometry: `footprint_area_m2` is the shapely union area of the floor's parts
(holes subtracted — `ShapePart` carries them); the bbox short side is the
shorter span of that union's axis-aligned bounds. Units are metres throughout
(the schema is m — no mm conversion, unlike proto3).
"""

from __future__ import annotations

from shapely.ops import unary_union

from room_layout.constraints.gates import check_min_area, check_min_dim
from room_layout.schema.geometry import FloorShape
from room_layout.schema.program import SpaceUnitSpec
from room_layout.schema.target import TargetRules
from room_layout.stages._helpers import to_shapely


def run(
    floor: FloorShape,
    specs: list[SpaceUnitSpec],
    *,
    rules: TargetRules,
) -> list[SpaceUnitSpec]:
    """Run the floor-scoped area + dim gates.

    Args:
        floor: the `FloorShape` the program is being placed on.
        specs: that floor's `SpaceUnitSpec` list.
        rules: the active `TargetRules` (provides `density_factor`).

    Returns:
        `specs` unchanged on accept.

    Raises:
        AreaGateFailure: Σ required `area_min_m2` > footprint × density.
        DimGateFailure: a required `min_dimension_m` exceeds the bbox short side.
    """
    footprint = unary_union([to_shapely(p) for p in floor.parts])
    footprint_area_m2 = footprint.area
    minx, miny, maxx, maxy = footprint.bounds
    bbox_short_side_m = min(maxx - minx, maxy - miny)

    check_min_area(
        specs,
        footprint_area_m2=footprint_area_m2,
        density_factor=rules.density_factor,
    )
    check_min_dim(specs, footprint_bbox_short_side_m=bbox_short_side_m)

    return specs
