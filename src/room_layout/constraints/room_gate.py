"""Per-room post-growth feasibility check (Step 07 §4.5).

The aggregate admission gates (``constraints/gates.py``) run *pre-growth*: does
the program fit the floor at all (Σ required ``area_min_m2`` ≤ usable
capacity)? They cannot catch a room that *grows* too small — growth is
target-agnostic (S04-D3), so a room can end up below its own ``area_min_m2`` /
``min_dimension_m`` (the "1.5 m² room"). This module is that distinct per-room
*post-growth* check (proto3:D020 fail-only):

- measured on the **actual grown polygon**: area is ``LabeledRoom.area_m2``
  (the polygon area, S07-D6); the min dimension is the short side of the
  polygon's *minimum rotated rectangle*, so a rotated room measures its true
  width, not an inflated axis-aligned bbox (same OBB convention as
  ``corridor._obb_aspect``);
- **collects** one ``FailureRecord`` per violation and returns them (it does
  NOT raise — ``run()`` accumulates them into
  ``LabeledRoomLayout.failure_records`` and flips ``valid=False``), unlike the
  raise-on-first aggregate gates;
- ``vertical_circulation`` rooms are **exempt**: their polygon is the fixed
  anchor footprint (§4.4), not a growth outcome, so growth-viability does not
  apply.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

from shapely.geometry import Polygon

from room_layout.schema.failure import FailureRecord
from room_layout.schema.output import LabeledRoom
from room_layout.schema.program import SpaceUnitSpec


def _obb_short_side(polygon: Polygon) -> float:
    """Short side of the polygon's minimum rotated rectangle (true width).

    Returns ``0.0`` for a degenerate room whose OBB collapses to a line/point —
    it then fails any positive ``min_dimension_m`` (a sliver is correctly
    rejected).
    """
    obb = polygon.minimum_rotated_rectangle
    if obb.geom_type != "Polygon":
        return 0.0
    coords = list(obb.exterior.coords)[:4]
    sides = [
        math.hypot(coords[i][0] - coords[(i + 1) % 4][0], coords[i][1] - coords[(i + 1) % 4][1])
        for i in range(4)
    ]
    return min(sides)


def check_grown_rooms(
    rooms: Iterable[LabeledRoom],
    specs_by_id: Mapping[str, SpaceUnitSpec],
) -> list[FailureRecord]:
    """Per-room post-growth area / min-dimension check (§4.5).

    For each non-``vertical_circulation`` room, fails when its grown area is
    below ``spec.area_min_m2`` (``ROOM_BELOW_MIN_AREA``) or its OBB short side
    is below ``spec.min_dimension_m`` when set (``ROOM_BELOW_MIN_DIM``). Both
    can fire for one room. Returns all failures (empty = all pass).
    """
    failures: list[FailureRecord] = []
    for room in rooms:
        if room.role == "vertical_circulation":
            continue
        spec = specs_by_id.get(room.id)
        if spec is None:
            continue  # §11 split 조각 (program spec 없음) — admission 검사 대상 아님
        if room.area_m2 < spec.area_min_m2:
            failures.append(
                FailureRecord(
                    code="ROOM_BELOW_MIN_AREA",
                    stage="per_room_gate",
                    message=(
                        f"room {room.id!r} grew to {room.area_m2:.3f} m² but its "
                        f"minimum is {spec.area_min_m2:.3f} m²"
                    ),
                    data={
                        "room": room.id,
                        "area_m2": round(room.area_m2, 4),
                        "area_min_m2": spec.area_min_m2,
                    },
                )
            )
        if spec.min_dimension_m is not None:
            short = _obb_short_side(room.polygon)
            if short < spec.min_dimension_m:
                failures.append(
                    FailureRecord(
                        code="ROOM_BELOW_MIN_DIM",
                        stage="per_room_gate",
                        message=(
                            f"room {room.id!r} short side {short:.3f} m is below its "
                            f"minimum dimension {spec.min_dimension_m} m"
                        ),
                        data={
                            "room": room.id,
                            "short_side_m": round(short, 4),
                            "min_dimension_m": spec.min_dimension_m,
                        },
                    )
                )
    return failures
