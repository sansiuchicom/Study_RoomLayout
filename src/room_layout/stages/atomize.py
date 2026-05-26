"""Atom dataclass + ``atomize(shape, policy)`` — Phase 3.

Placeholder. Populated in work item 4.7.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.7.

Will define:

- ``@dataclass(frozen=True) Atom`` — minimal quantum-aligned cell.
  Holds: ``part_id: int`` (parent ShapePart index in
  ``FloorShape.parts``), ``shape: ShapePart``-shaped coords,
  ``theta`` (inherited from parent part).
- ``atomize(shape: ShapeInput, policy: DimensionPolicy) -> list[Atom]``
  — decompose floor footprint into atoms.

Bundled work item (Plan §4.7): the matching ``viz/stages/atomize.py``
renderer and 33-case ``atomize.json`` + PNG golden fixtures land in the
**same commit** as this module (first manual review checkpoint).
"""
