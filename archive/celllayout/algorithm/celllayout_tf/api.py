"""Stable public facade for portable RoomLayoutCell integration.

The lower-level atom, region graph, seed, and corridor-stage modules remain
importable by exact module path for diagnostics and tests, but they are not part
of the package root API. External integrations should import from this facade or
from ``celllayout_tf`` directly.
"""

from __future__ import annotations

from .corridor import CorridoredLayout, carve_corridors
from .dimensions import DimensionPolicy
from .growth_partition import region_partition_growth
from .room_growth import (
    GrownRoom,
    GrowthResult,
    LayoutFixture,
    Role,
    RoomSpec,
)
from .schema import ShapeInput, ShapePart, part_theta

__all__ = [
    "ShapeInput",
    "ShapePart",
    "part_theta",
    "DimensionPolicy",
    "Role",
    "RoomSpec",
    "LayoutFixture",
    "GrownRoom",
    "GrowthResult",
    "CorridoredLayout",
    "region_partition_growth",
    "carve_corridors",
]
