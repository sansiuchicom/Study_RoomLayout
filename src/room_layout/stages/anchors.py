"""Vertical-anchor wiring — Phase 6 preprocessing (Step 04 §4.4).

Plan reference: ``004_Step04_AlgorithmCore_Plan.md`` §4.4 + S04-D4.

New to this repo — Cell's Phase 1–8 has no anchor concept. v1 handles
anchors with a **footprint donut-hole** (S04-D4): the anchor footprints are
subtracted from the floor *before* the geometry pipeline, so atomize /
regionize / growth / carve stay anchor-blind. ``ShapePart.holes`` is already
first-class and ``atomize`` excludes holes (``test_atomize_hole_is_excluded``).

This module is the **subtraction half** (4.4). The fixed-room re-insertion
for ``host_role == "vertical_circulation"`` anchors lands in 4.15 with the
growth result to append to.

`difference(part, anchor)` is a clean interior hole only when the anchor sits
strictly inside a part; a boundary-touching anchor yields a notch and a
spanning anchor splits the part (handled generically via ``polygon_parts``).
"""

from __future__ import annotations

from shapely.ops import unary_union

from room_layout.schema import FloorShape, VerticalAnchor
from room_layout.schema.failure import DomainGateFailure, FailureRecord
from room_layout.stages._helpers import from_shapely, polygon_parts, to_shapely

# Split fragments below this area (m²) are dropped as degenerate.
_MIN_PART_AREA = 1e-9


def anchors_on_floor(anchors: list[VerticalAnchor], level: int) -> list[VerticalAnchor]:
    """Anchors whose inclusive ``floor_range`` covers ``level``.

    Anchors span a vertical range with identical XY on every floor in it
    (Pipeline §2.1); a single floor sees only those passing through it.
    """
    return [a for a in anchors if a.floor_range[0] <= level <= a.floor_range[1]]


def subtract_anchors(floor: FloorShape, anchors: list[VerticalAnchor]) -> FloorShape:
    """Return ``floor`` with applicable anchor footprints punched out (S04-D4).

    Every anchor on this floor — both ``vertical_circulation`` (stair /
    elevator) and ``host_role=None`` shafts — becomes a forbidden hole so the
    geometry pipeline never grows into it. The ``vertical_circulation`` rooms
    are re-inserted as fixed polygons after growth (4.15); the ``None`` shafts
    stay holes with no room emitted.

    Parts that split under subtraction yield multiple ``ShapePart``s; parts
    fully consumed by an anchor are dropped.
    """
    applicable = anchors_on_floor(anchors, floor.level)
    if not applicable:
        return floor

    cut = unary_union([a.footprint_polygon for a in applicable])
    new_parts = []
    for part in floor.parts:
        remainder = to_shapely(part).difference(cut)
        for poly in polygon_parts(remainder):
            if poly.area < _MIN_PART_AREA:
                continue
            new_parts.append(from_shapely(poly))

    if not new_parts:
        raise DomainGateFailure(
            FailureRecord(
                code="FLOOR_CONSUMED_BY_ANCHORS",
                stage="run",
                message=(
                    f"floor {floor.level}: vertical anchors consume the entire footprint "
                    "(no floor area left to lay out)"
                ),
                data={"level": floor.level},
            )
        )

    return FloorShape(
        level=floor.level,
        parts=new_parts,
        floor_to_floor_height=floor.floor_to_floor_height,
    )
