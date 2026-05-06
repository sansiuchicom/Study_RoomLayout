"""Input schemas: BuildingInput, FloorInput, PersistentAnchor.

Stage 00 inputs (Pipeline Overview §9). Apartment-first but multi-floor
compatible (D003, S02-D10): BuildingInput.floors is always a list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# S02-D14: canonical target type alias. Both BuildingInput.target_type (data
# identity) and RunConfig.target_type (run-time intent) use this; Stage 00
# enforces equality via proto3.config.assert_target_consistent.
TargetType = Literal["apartment", "house", "hotel", "warehouse", "office"]


@dataclass
class PersistentAnchor:
    """Building-global anchor projected into one or more floors (Stage 03)."""
    kind: str = ""  # stair | elevator | wet_shaft | structural_core | void
    floors: list[int] = field(default_factory=list)
    # TBD: geometry representation (vertices vs Polygon) — Step 05 Geometry Kernel
    geometry: list[tuple[float, float]] = field(default_factory=list)
    # TBD: adjacency requirements, root candidate flag


@dataclass
class FloorInput:
    """Per-floor footprint, root, anchors, and floor program (§14)."""
    footprint: list[tuple[float, float]] = field(default_factory=list)  # polygon vertices in mm
    floor_root: tuple[float, float] | None = None  # entry/landing (§6.1)
    floor_program: dict | None = None  # subset of program_request — TBD typed in Step 06
    anchor_projections: list[PersistentAnchor] = field(default_factory=list)


@dataclass
class BuildingInput:
    """Multi-floor container. Apartment uses len(floors) == 1 (D003, S02-D10)."""
    target_type: TargetType = "apartment"  # canonical alias above (S02-D14)
    floors: list[FloorInput] = field(default_factory=list)
    program_request: dict = field(default_factory=dict)  # raw — typed in Step 06
    persistent_anchors: list[PersistentAnchor] = field(default_factory=list)
