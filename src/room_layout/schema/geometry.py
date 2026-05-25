"""Geometry input types — `ShapePart`, `VerticalAnchor`, `FloorShape`, `ShapeInput`.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.3 + S02-D6 / S02-D7 /
S02-D10 / S02-D12.

All dataclasses here are `frozen=True` (input contract — immutability per
S02-D3). `__post_init__` does *structural* validation only (single-object
invariants); cross-references (e.g. `SpaceUnitSpec.anchor_id` → existing
`VerticalAnchor.id`) live in `validators.py` (work item 4.7).
"""

from dataclasses import dataclass, field
from typing import Literal

from shapely.geometry import Polygon
from shapely.geometry.polygon import LinearRing

Point = tuple[float, float]
Ring = tuple[Point, ...]

VerticalAnchorKind = Literal[
    "stair_core",
    "elevator_shaft",
    "ps_shaft",
    "eps_shaft",
    "duct_shaft",
]
VerticalAnchorHostRole = Literal["vertical_circulation"] | None

# Single source of truth for the kind ↔ host_role matrix (S02-D10).
# Walk-in shafts (stair / elevator) host a `vertical_circulation` room;
# non-walk-in shafts (ps / eps / duct) are forbidden-region only.
_KIND_TO_HOST_ROLE: dict[str, VerticalAnchorHostRole] = {
    "stair_core": "vertical_circulation",
    "elevator_shaft": "vertical_circulation",
    "ps_shaft": None,
    "eps_shaft": None,
    "duct_shaft": None,
}


def _validate_ring(ring: Ring, *, label: str, expect_ccw: bool) -> None:
    """Structural validation of a single ring.

    Order is intentional (each step assumes prior steps passed):

    1. ``len(ring) >= 3`` — degenerate rings (point / segment) cannot
       form a polygon.
    2. ``signed area != 0`` — collinear rings are degenerate even with
       3+ points; reject before checking orientation since `is_ccw`
       is undefined on zero-area rings.
    3. orientation matches ``expect_ccw`` (exterior CCW + holes CW per
       S02-D12 / shapely right-hand rule).
    4. ``is_simple`` — no self-intersection.
    """
    if len(ring) < 3:
        raise ValueError(f"{label}: ring must have ≥ 3 points, got {len(ring)}")
    lr = LinearRing(ring)
    if lr.area == 0:
        raise ValueError(f"{label}: ring has zero signed area (degenerate / collinear)")
    if lr.is_ccw != expect_ccw:
        want = "CCW" if expect_ccw else "CW"
        got = "CCW" if lr.is_ccw else "CW"
        raise ValueError(f"{label}: ring orientation must be {want}, got {got}")
    if not lr.is_simple:
        raise ValueError(f"{label}: ring is self-intersecting")


@dataclass(frozen=True)
class ShapePart:
    """One design-time polygon primitive (rect / wing / mirror extension).

    Per Pipeline §2 "parts preserved, not unioned": a `FloorShape` is a
    list of `ShapePart`s, each carrying its own orientation through its
    edges. No `theta` field — orientation is inferred per part downstream.
    """

    exterior: Ring
    holes: tuple[Ring, ...] = ()

    def __post_init__(self) -> None:
        _validate_ring(self.exterior, label="ShapePart.exterior", expect_ccw=True)
        for i, hole in enumerate(self.holes):
            _validate_ring(hole, label=f"ShapePart.holes[{i}]", expect_ccw=False)


@dataclass(frozen=True)
class VerticalAnchor:
    """Stair / elevator / shaft fixed footprint spanning a floor range.

    `host_role == "vertical_circulation"` ⇒ a walk-in room (stair / elevator)
    is carved at this footprint on every floor in `floor_range`.
    `host_role is None` ⇒ forbidden region only (ps / eps / duct shaft).
    """

    id: str
    kind: VerticalAnchorKind
    footprint_polygon: Polygon
    floor_range: tuple[int, int]
    host_role: VerticalAnchorHostRole

    def __post_init__(self) -> None:
        expected = _KIND_TO_HOST_ROLE[self.kind]
        if self.host_role != expected:
            raise ValueError(
                f"VerticalAnchor {self.id!r}: kind={self.kind!r} requires "
                f"host_role={expected!r}, got {self.host_role!r}"
            )
        start, end = self.floor_range
        if start > end:
            raise ValueError(
                f"VerticalAnchor {self.id!r}: floor_range start ({start}) > end ({end})"
            )


@dataclass(frozen=True)
class FloorShape:
    """One floor's footprint — a list of `ShapePart`s + slab height."""

    level: int
    parts: list[ShapePart]
    floor_to_floor_height: float

    def __post_init__(self) -> None:
        if not self.parts:
            raise ValueError(f"FloorShape level={self.level}: parts must be non-empty")
        if self.floor_to_floor_height <= 0:
            raise ValueError(
                f"FloorShape level={self.level}: floor_to_floor_height must be > 0, "
                f"got {self.floor_to_floor_height}"
            )


@dataclass(frozen=True)
class ShapeInput:
    """The full geometric input to `run()` — name + floors + anchors."""

    name: str
    floors: list[FloorShape]
    vertical_anchors: list[VerticalAnchor] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("ShapeInput.name must be non-empty")
        if not self.floors:
            raise ValueError(f"ShapeInput {self.name!r}: floors must be non-empty")
