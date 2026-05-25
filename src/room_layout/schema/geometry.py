"""Geometry input types — `ShapeInput`, `FloorShape`, `ShapePart`, `VerticalAnchor`.

Placeholder. Populated in work item 4.3.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.3.

Will define:

- type aliases: ``Point = tuple[float, float]``, ``Ring = tuple[Point, ...]``;
- ``@dataclass(frozen=True) ShapePart`` — ``exterior: Ring`` (CCW) +
  ``holes: tuple[Ring, ...] = ()`` (CW per S02-D12, shapely right-hand rule);
- ``@dataclass(frozen=True) VerticalAnchor`` — ``kind`` ↔ ``host_role``
  matrix enforced in ``__post_init__`` (S02-D10 structural);
- ``@dataclass(frozen=True) FloorShape`` — ``level`` + ``parts`` +
  ``floor_to_floor_height``;
- ``@dataclass(frozen=True) ShapeInput`` — required ``name: str`` (S02-D7)
  + ``floors`` + ``vertical_anchors``.
"""
