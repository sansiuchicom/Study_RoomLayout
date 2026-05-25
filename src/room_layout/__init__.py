"""room_layout — room layout generation component.

This package is the Stage 4 (Room Layout) building block of the PlanBIM
synthetic-BIM training-data pipeline. It takes a footprint (with
preserved part decomposition) plus a room program and returns a labeled
room layout — see ``docs/000_Pipeline_Overview.md`` §2 for the external
contract.

Canonical references (repo root)::

    docs/000_Pipeline_Overview.md       external contract, internal
                                        pipeline, terminology, step map
    docs/000_Architecture_Decisions.md  accepted decisions (D001–D006 +
                                        proto3 D001–D023 inheritance audit)
    docs/000_Progress_Tracker.md        current implementation status

Step 02 landed the full typed schema (`room_layout.schema`). The public
surface below mirrors `room_layout.schema.__all__` so callers may write
either::

    from room_layout import ShapeInput
    # or equivalently
    from room_layout.schema import ShapeInput

The algorithm entry point `run(...)` lands in Step 06.
"""

from room_layout.schema import (
    WARN_PREFIX,
    AccessSchemaFailure,
    AreaGateFailure,
    DimGateFailure,
    DomainGateFailure,
    Door,
    DoorKind,
    FailureRecord,
    FloorShape,
    LabeledFloorLayout,
    LabeledRoom,
    LabeledRoomLayout,
    Point,
    ProgramRequest,
    Ring,
    Role,
    ShapeInput,
    ShapePart,
    SpaceUnitSpec,
    TargetType,
    VerticalAnchor,
    VerticalAnchorHostRole,
    VerticalAnchorKind,
    coords_to_polygon,
    from_dict,
    from_json,
    polygon_to_coords,
    to_dict,
    to_json,
    validate_input,
)

__version__ = "0.1.0"

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
    "TargetType",
    "VerticalAnchor",
    "VerticalAnchorHostRole",
    "VerticalAnchorKind",
    "WARN_PREFIX",
    "__version__",
    "coords_to_polygon",
    "from_dict",
    "from_json",
    "polygon_to_coords",
    "to_dict",
    "to_json",
    "validate_input",
]
