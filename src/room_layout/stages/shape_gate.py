"""Shape gate checks — Phase 5.

Placeholder. Populated in work item 4.11.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.11.

Will define gate-check functions that raise ``DimGateFailure`` (defined
in ``room_layout.schema.failure`` from Step 02) when a ``Region``
violates minimum-dimension or shape constraints. ``AccessSchemaFailure``
remains a Step 04 concern (corridor / access topology).

Bundled work item (Plan §4.11): ``viz/stages/gates.py`` renderer and
33-case ``gates.json`` + PNG golden fixtures land in the **same
commit** as this module (third manual review checkpoint).
"""
