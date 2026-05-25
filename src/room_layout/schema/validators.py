"""Cross-reference validators — `validate_input(shape, program)`.

Placeholder. Populated in work item 4.7.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.7.

Distinct from ``__post_init__`` (structural / single-object) validation
per S02-D6 / S02-D10: this module checks invariants that *span* the
input pair (``ShapeInput`` × ``ProgramRequest``).

Will define:

- ``validate_input(shape: ShapeInput, program: ProgramRequest) ->
  list[FailureRecord]`` — empty list = OK. Each failure mode emits a
  ``FailureRecord`` with a stable ``code``.

Initial failure codes (expanded in later Steps as new cross-refs
appear):

- ``ANCHOR_ID_NOT_FOUND`` — a ``SpaceUnitSpec.anchor_id`` references
  a ``VerticalAnchor.id`` that does not exist.
- ``ANCHOR_HOST_ROLE_MISMATCH`` — the resolved anchor has a
  ``host_role`` incompatible with the requesting ``SpaceUnitSpec.role``
  (only ``vertical_circulation`` rooms bind to anchors per D004 /
  S02-D9).
- ``PROGRAM_FLOOR_NOT_IN_SHAPE`` — ``ProgramRequest.floor_programs``
  contains a level not in ``ShapeInput.floors``.

Called by Step 06's ``run()`` before atomize, so the algorithm can
short-circuit with a ``valid=False`` ``LabeledRoomLayout`` carrying
``failure_records`` (proto3:D018 carry).
"""
