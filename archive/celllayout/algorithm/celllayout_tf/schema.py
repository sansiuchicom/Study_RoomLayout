"""Input schema for testfield cases.

A case is a list of design-time primitive polygons (``ShapePart``). Each part
stores raw vertex coordinates only — no orientation, no role, no derived
geometry. The case footprint is the union of its parts; the union is computed
by downstream code when needed and is never the canonical representation.

Why preserve parts instead of unioning at construction: synthetic data already
knows which primitives compose a footprint (e.g. main rect + rotated wing).
Keeping that decomposition lets downstream code read each part's orientation
from its own edges with no detection/inference step.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, hypot, pi

Point = tuple[float, float]
Ring = tuple[Point, ...]


@dataclass(frozen=True)
class ShapePart:
    exterior: Ring
    holes: tuple[Ring, ...] = ()

    def __post_init__(self):
        if len(self.exterior) < 3:
            raise ValueError(
                f"ShapePart exterior needs >=3 points, got {len(self.exterior)}"
            )
        for idx, hole in enumerate(self.holes):
            if len(hole) < 3:
                raise ValueError(
                    f"ShapePart hole[{idx}] needs >=3 points, got {len(hole)}"
                )


@dataclass(frozen=True)
class ShapeInput:
    name: str
    parts: tuple[ShapePart, ...]

    def __post_init__(self):
        if not self.parts:
            raise ValueError(f"ShapeInput {self.name!r} has no parts")


def part_theta(part: ShapePart) -> float:
    """Return the part's orientation in radians on ``[0, pi/2)``.

    Reads atan2 of the first non-degenerate exterior edge. For axis-aligned
    rectangles or any straight-edged shape this is exact. For curved parts
    (high-vertex disks/ellipses) the first edge points along the tangent at
    the first vertex — caller treats the result as approximate.
    """
    verts = part.exterior
    n = len(verts)
    for i in range(n):
        x0, y0 = verts[i]
        x1, y1 = verts[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        if hypot(dx, dy) > 1e-9:
            return float(atan2(dy, dx) % (pi / 2))
    return 0.0
