"""Program input types — `ProgramRequest`, `SpaceUnitSpec`, `Role`.

Placeholder. Populated in work item 4.4.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.4.

Will define:

- ``Role = Literal["public", "private", "service", "wet", "hub",
  "corridor", "vertical_circulation"]`` — single 7-class taxonomy per
  D004, shared by ``SpaceUnitSpec.role`` and ``LabeledRoom.role``
  (S02-D9 single source of truth);
- ``@dataclass(frozen=True) SpaceUnitSpec`` — ``role: Role`` with
  ``__post_init__`` enforcing (a) ``role != "corridor"`` (S02-D9 —
  ``corridor`` is output-only) and (b) ``role == "vertical_circulation"``
  ⇒ ``anchor_id is not None`` (S02-D6 / S02-D10 structural);
- ``@dataclass(frozen=True) ProgramRequest`` — ``target_type`` +
  ``floor_programs: dict[int, list[SpaceUnitSpec]]``.
"""
