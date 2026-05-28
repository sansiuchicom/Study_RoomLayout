"""room_layout.stages — internal pipeline stages (Phase 3–5).

This subpackage hosts the geometry-side stages of the algorithm. Each
module produces a typed output that the next stage consumes; outputs
are also serialized to per-stage golden JSON under ``tests/golden/``
for regression coverage.

Module layout (Plan §3):

    _helpers.py     Cell geometry utilities (to_shapely / from_shapely /
                    polygon_parts / line_length / rotate_radians /
                    part_theta) ported and adapted to new schema
    dimensions.py   DimensionPolicy + quantum helpers (is_quantum_aligned,
                    split_interval); foundational utility for the rest
    territory.py    Territory dataclass + resolve_territories(floor)
    atomize.py      Atom dataclass + atomize(floor, policy)
    regionize.py    Region dataclass + regionize(floor, atoms, ...)
    atom_graph.py   AtomGraph + build_atom_graph(floor) (region_graph dep)
    region_graph.py RegionGraph + build_region_graph(floor)

(shape_gate is a Phase 6/7 growth helper — deferred to Step 04 per
S03-D16, not part of this subpackage in Step 03.)

Internal dataclasses (`Atom` / `Region` / `Territory` / `DimensionPolicy`)
live alongside their producing stage per S03-D6 and are **not**
re-exported from ``room_layout`` or ``room_layout.schema`` —
``room_layout.schema`` is the D001 public contract; these are pipeline
implementation details. Tests import directly from the stage module.

References:

- ``docs/000_Pipeline_Overview.md`` §3 — per-stage operational view
  this Step implements.
- ``003_Step03_GeometryPipeline_Plan.md`` §3 — directory structure;
  §4 — work items; §2 — 12 frozen decisions (S03-D1..D12).
- ``archive/celllayout/algorithm/celllayout_tf/`` — porting source.

Re-exports populated in subsequent work items (4.5 onward).
"""
