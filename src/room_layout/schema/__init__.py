"""room_layout.schema — typed dataclasses for the D001 external contract.

This subpackage hosts the input / output / failure dataclasses that
`run()` (Step 06) consumes and produces. Step 02 lands the types
themselves; Step 03 onward fills the algorithm against this schema.

Module layout (work items 4.3–4.7)::

    geometry.py     ShapeInput / FloorShape / ShapePart / VerticalAnchor
                    + Ring / Point type aliases
    program.py      ProgramRequest / SpaceUnitSpec / Role
    output.py       LabeledRoomLayout / LabeledFloorLayout / LabeledRoom / Door
    failure.py      FailureRecord + DomainGateFailure exception hierarchy
    serialize.py    to_dict / from_dict generic helpers + strict Literal
                    validation (proto3:D017 carry)
    validators.py   validate_input(shape, program) cross-reference check

References:

- ``docs/000_Pipeline_Overview.md`` §2 — typed contract sketches that
  drive the dataclass shapes implemented here.
- ``docs/000_Architecture_Decisions.md`` D001 / D003 / D004 / D006 +
  proto3:D012 / D017 / D018 / D020 / D023.
- ``002_Step02_CoreSchema_Plan.md`` §2 — S02-D1..D13 design decisions.

Re-exports are populated in subsequent work items (4.3 onward).
"""

from room_layout.schema.failure import (
    AccessSchemaFailure,
    AreaGateFailure,
    DimGateFailure,
    DomainGateFailure,
    FailureRecord,
)
from room_layout.schema.geometry import (
    FloorShape,
    Point,
    Ring,
    ShapeInput,
    ShapePart,
    VerticalAnchor,
    VerticalAnchorHostRole,
    VerticalAnchorKind,
)
from room_layout.schema.output import (
    Door,
    DoorKind,
    LabeledFloorLayout,
    LabeledRoom,
    LabeledRoomLayout,
)
from room_layout.schema.program import (
    ProgramRequest,
    Role,
    SpaceUnitSpec,
)
from room_layout.schema.serialize import (
    coords_to_polygon,
    from_dict,
    from_json,
    polygon_to_coords,
    to_dict,
    to_json,
)

__all__ = [
    "AccessSchemaFailure",
    "AreaGateFailure",
    "DimGateFailure",
    "DomainGateFailure",
    "Door",
    "DoorKind",
    "FailureRecord",
    "FloorShape",
    "LabeledFloorLayout",
    "LabeledRoom",
    "LabeledRoomLayout",
    "Point",
    "ProgramRequest",
    "Ring",
    "Role",
    "ShapeInput",
    "ShapePart",
    "SpaceUnitSpec",
    "VerticalAnchor",
    "VerticalAnchorHostRole",
    "VerticalAnchorKind",
    "coords_to_polygon",
    "from_dict",
    "from_json",
    "polygon_to_coords",
    "to_dict",
    "to_json",
]
