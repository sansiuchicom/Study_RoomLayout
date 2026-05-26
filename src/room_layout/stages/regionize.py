"""Region dataclass + ``regionize(...)`` — Phase 4.

Placeholder. Populated in work item 4.9.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.9.

Will define:

- ``@dataclass(frozen=True) Region`` — atom cluster sized around
  ``target_area``. Holds: ``region_id: int``, ``shape: ShapePart``-
  shaped coords, contributing atoms.
- ``regionize(shape: ShapeInput, atoms: list[Atom],
  policy: DimensionPolicy, target_area: float) -> list[Region]`` —
  group atoms into regions.

Bundled work item (Plan §4.9): ``viz/stages/regionize.py`` renderer
and 33-case ``regionize.json`` + PNG golden fixtures land in the
**same commit** as this module (second manual review checkpoint).
"""
