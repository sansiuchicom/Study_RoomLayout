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

Future top-level exports (placeholder; populated as Steps land)::

    # Step 02 — Core Schema
    # from .schema import (
    #     ShapeInput, FloorShape, ShapePart, VerticalAnchor,
    #     ProgramRequest, SpaceUnitSpec,
    #     LabeledRoomLayout, LabeledFloorLayout, LabeledRoom,
    #     Role, FailureRecord,
    # )

    # Step 06 — Entry point
    # from .run import run

Step 01 is scaffold-only: this package currently exposes nothing.
Importing it should succeed (``tests/test_smoke.py`` verifies this).
"""

__version__ = "0.1.0"
