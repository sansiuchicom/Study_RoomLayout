"""Stage geometry utilities — `to_shapely`, `polygon_parts`, `part_theta`.

Placeholder. Populated in work item 4.5.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.5.

Will define small helpers used across atomize / regionize / shape_gate.
Ported from Cell ``geometry.py`` and adapted to the new ``ShapePart``,
which already exposes ``exterior`` + ``holes`` directly (simplifying
the shapely-conversion path compared to Cell's API).

Internal — not re-exported from ``room_layout`` per S03-D6.
"""
