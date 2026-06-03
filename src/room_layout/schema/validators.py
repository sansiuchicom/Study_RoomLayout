"""Cross-reference validators — `validate_input(shape, program)`.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.7 + S02-D10
(structural-vs-cross-ref split) + proto3:D018 (failure_records carry).

Distinct from ``__post_init__`` (structural / single-object) validation:
this module checks invariants that *span* the input pair
(`ShapeInput` × `ProgramRequest`).

**Severity convention** (resolved in chat 2026-05-25): codes prefixed
``WARN_`` are warnings (pipeline may continue); all other codes are
errors. Consumers (Step 06 `run`) filter by `WARN_PREFIX` to decide
whether to short-circuit. If warning categories ever exceed ~5, migrate
to a `severity` field on `FailureRecord`.

Stable failure codes emitted by this module:

- ``DUPLICATE_ANCHOR_ID`` — two `VerticalAnchor`s share the same `id`.
  (error)
- ``DUPLICATE_FLOOR_LEVEL`` — two `FloorShape`s share the same `level`.
  (error)
- ``DUPLICATE_SPEC_ID`` — two `SpaceUnitSpec`s share the same `id`
  across all floor programs. (error)
- ``ANCHOR_ID_NOT_FOUND`` — `SpaceUnitSpec.anchor_id` references a
  `VerticalAnchor.id` that does not exist. (error)
- ``ANCHOR_HOST_ROLE_MISMATCH`` — the resolved anchor has
  `host_role != "vertical_circulation"`, so the spec cannot bind
  to it as a walk-in room. (error)
- ``ANCHOR_FLOOR_RANGE_MISMATCH`` — the spec's containing floor level
  is outside the resolved anchor's `floor_range`. (error)
- ``ANCHOR_OUTSIDE_FOOTPRINT`` — a `VerticalAnchor` footprint protrudes
  outside the floor it spans (would emit an out-of-building room). (error)
- ``PROGRAM_FLOOR_NOT_IN_SHAPE`` — `ProgramRequest.floor_programs`
  references a level not in `ShapeInput.floors`. (error)
- ``WARN_ANCHOR_UNUSED`` — a `VerticalAnchor` with
  `host_role == "vertical_circulation"` is not referenced by any
  `SpaceUnitSpec`. (warning)

Called by Step 06's `run()` before atomize, so the algorithm can
short-circuit with a `valid=False` `LabeledRoomLayout` carrying
`failure_records` (proto3:D018 carry).
"""

from collections import Counter

from shapely.geometry import Polygon
from shapely.ops import unary_union

from room_layout.schema.failure import FailureRecord
from room_layout.schema.geometry import ShapeInput
from room_layout.schema.program import ProgramRequest

WARN_PREFIX = "WARN_"
_STAGE = "validate_input"


def validate_input(shape: ShapeInput, program: ProgramRequest) -> list[FailureRecord]:
    """Cross-reference checks between a ShapeInput and a ProgramRequest.

    Returns an accumulated list of FailureRecords; empty means consistent.
    Codes prefixed `WARN_` are warnings (see module docstring).
    """
    records: list[FailureRecord] = []

    _check_duplicate_anchor_ids(shape, records)
    _check_duplicate_floor_levels(shape, records)
    _check_duplicate_spec_ids(program, records)
    _check_anchor_footprint_containment(shape, records)

    anchors_by_id = {a.id: a for a in shape.vertical_anchors}
    shape_levels = {fs.level for fs in shape.floors}
    used_anchor_ids: set[str] = set()

    for level, specs in program.floor_programs.items():
        if level not in shape_levels:
            records.append(
                FailureRecord(
                    code="PROGRAM_FLOOR_NOT_IN_SHAPE",
                    stage=_STAGE,
                    message=(
                        f"floor_programs references level {level} not present in shape.floors"
                    ),
                    data={
                        "level": level,
                        "available_levels": sorted(shape_levels),
                    },
                )
            )

        for spec in specs:
            if spec.anchor_id is None:
                continue
            anchor = anchors_by_id.get(spec.anchor_id)
            if anchor is None:
                records.append(
                    FailureRecord(
                        code="ANCHOR_ID_NOT_FOUND",
                        stage=_STAGE,
                        message=(
                            f"SpaceUnitSpec {spec.id!r} references anchor_id "
                            f"{spec.anchor_id!r} not in shape.vertical_anchors"
                        ),
                        data={
                            "spec_id": spec.id,
                            "anchor_id": spec.anchor_id,
                            "available_anchor_ids": sorted(anchors_by_id.keys()),
                        },
                    )
                )
                continue

            if anchor.host_role != "vertical_circulation":
                records.append(
                    FailureRecord(
                        code="ANCHOR_HOST_ROLE_MISMATCH",
                        stage=_STAGE,
                        message=(
                            f"SpaceUnitSpec {spec.id!r} binds to anchor "
                            f"{anchor.id!r} whose host_role="
                            f"{anchor.host_role!r} ≠ 'vertical_circulation'"
                        ),
                        data={
                            "spec_id": spec.id,
                            "anchor_id": anchor.id,
                            "anchor_kind": anchor.kind,
                            "anchor_host_role": anchor.host_role,
                        },
                    )
                )
                continue

            # host_role OK — check floor_range containment.
            start, end = anchor.floor_range
            if not (start <= level <= end):
                records.append(
                    FailureRecord(
                        code="ANCHOR_FLOOR_RANGE_MISMATCH",
                        stage=_STAGE,
                        message=(
                            f"SpaceUnitSpec {spec.id!r} on floor {level} binds to "
                            f"anchor {anchor.id!r} whose floor_range="
                            f"{anchor.floor_range} does not include {level}"
                        ),
                        data={
                            "spec_id": spec.id,
                            "anchor_id": anchor.id,
                            "spec_floor": level,
                            "anchor_floor_range": list(anchor.floor_range),
                        },
                    )
                )
                # Still count as used — the user clearly intended to bind here;
                # avoid double-reporting via WARN_ANCHOR_UNUSED.

            used_anchor_ids.add(anchor.id)

    for anchor in shape.vertical_anchors:
        if anchor.host_role == "vertical_circulation" and anchor.id not in used_anchor_ids:
            records.append(
                FailureRecord(
                    code="WARN_ANCHOR_UNUSED",
                    stage=_STAGE,
                    message=(
                        f"VerticalAnchor {anchor.id!r} (kind={anchor.kind!r}) "
                        f"has host_role='vertical_circulation' but no "
                        f"SpaceUnitSpec references it"
                    ),
                    data={"anchor_id": anchor.id, "anchor_kind": anchor.kind},
                )
            )

    return records


def _check_duplicate_anchor_ids(shape: ShapeInput, records: list[FailureRecord]) -> None:
    counts = Counter(a.id for a in shape.vertical_anchors)
    for anchor_id, count in counts.items():
        if count > 1:
            records.append(
                FailureRecord(
                    code="DUPLICATE_ANCHOR_ID",
                    stage=_STAGE,
                    message=(f"VerticalAnchor.id {anchor_id!r} appears {count} times"),
                    data={"anchor_id": anchor_id, "count": count},
                )
            )


def _check_duplicate_floor_levels(shape: ShapeInput, records: list[FailureRecord]) -> None:
    counts = Counter(fs.level for fs in shape.floors)
    for level, count in counts.items():
        if count > 1:
            records.append(
                FailureRecord(
                    code="DUPLICATE_FLOOR_LEVEL",
                    stage=_STAGE,
                    message=f"FloorShape.level {level} appears {count} times",
                    data={"level": level, "count": count},
                )
            )


def _check_anchor_footprint_containment(shape: ShapeInput, records: list[FailureRecord]) -> None:
    """Each anchor's footprint must lie within the floor(s) it spans — otherwise a
    `vertical_circulation` room would be emitted outside the building (S07 review).
    Boundary-touching is fine; only area *protruding* outside the floor fails."""
    floors_by_level = {fs.level: fs for fs in shape.floors}
    for anchor in shape.vertical_anchors:
        start, end = anchor.floor_range
        for level in range(start, end + 1):
            floor = floors_by_level.get(level)
            if floor is None:
                continue  # missing floor is a separate concern (range vs shape)
            floor_poly = unary_union(
                [Polygon(p.exterior, [list(h) for h in p.holes]) for p in floor.parts]
            )
            outside = anchor.footprint_polygon.difference(floor_poly).area
            if outside > 1e-9:
                records.append(
                    FailureRecord(
                        code="ANCHOR_OUTSIDE_FOOTPRINT",
                        stage=_STAGE,
                        message=(
                            f"VerticalAnchor {anchor.id!r} footprint protrudes "
                            f"{outside:.3f} m² outside floor {level}"
                        ),
                        data={
                            "anchor_id": anchor.id,
                            "level": level,
                            "outside_area_m2": round(outside, 4),
                        },
                    )
                )


def _check_duplicate_spec_ids(program: ProgramRequest, records: list[FailureRecord]) -> None:
    """SpaceUnitSpec.id is a global identifier across floors (Pipeline §2.3
    — `LabeledRoom.id` matches `SpaceUnitSpec.id` when known)."""
    all_ids = [s.id for specs in program.floor_programs.values() for s in specs]
    counts = Counter(all_ids)
    for spec_id, count in counts.items():
        if count > 1:
            records.append(
                FailureRecord(
                    code="DUPLICATE_SPEC_ID",
                    stage=_STAGE,
                    message=(
                        f"SpaceUnitSpec.id {spec_id!r} appears {count} times across floor_programs"
                    ),
                    data={"spec_id": spec_id, "count": count},
                )
            )
