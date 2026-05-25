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

- ``ANCHOR_ID_NOT_FOUND`` — `SpaceUnitSpec.anchor_id` references a
  `VerticalAnchor.id` that does not exist. (error)
- ``ANCHOR_HOST_ROLE_MISMATCH`` — the resolved anchor has
  `host_role != "vertical_circulation"`, so the spec cannot bind
  to it as a walk-in room. (error)
- ``PROGRAM_FLOOR_NOT_IN_SHAPE`` — `ProgramRequest.floor_programs`
  references a level not in `ShapeInput.floors`. (error)
- ``WARN_ANCHOR_UNUSED`` — a `VerticalAnchor` with
  `host_role == "vertical_circulation"` is not referenced by any
  `SpaceUnitSpec`. (warning)

Called by Step 06's `run()` before atomize, so the algorithm can
short-circuit with a `valid=False` `LabeledRoomLayout` carrying
`failure_records` (proto3:D018 carry).
"""

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
