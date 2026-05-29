"""room_layout.stages — internal pipeline stages (Cell Phase 3–8).

This subpackage hosts the geometry + algorithm stages. Each module produces a
typed output the next stage consumes; outputs are serialized to per-stage
golden JSON under ``tests/golden/`` for regression coverage.

**Imports are module-qualified** — there is no public re-export from this
``__init__`` (Step 03 convention). Use e.g.
``from room_layout.stages.corridor import carve_corridors``.

Module layout (flat per S04-D6):

    Phase 3–5 (Step 03 — geometry):
      _helpers.py     shapely bridges + orientation (to_shapely / from_shapely
                      / polygon_parts / line_length / rotate_radians / part_theta)
      dimensions.py   DimensionPolicy + quantum helpers
      territory.py    Territory + resolve_territories(floor)
      atomize.py      Atom + atomize(floor)
      regionize.py    Region + regionize(floor, atoms)
      atom_graph.py / region_graph.py   adjacency graphs

    Phase 6–8 (Step 04 — algorithm core):
      seed_placement.py   SeedPlacement + centrality / BFS helpers
      growth_seed.py      auto_place_seeds_by_cells (hub / coverage / fps)
      growth_cells.py     vertex cells + guillotine partition
      growth_partition.py region_partition_growth → GrowthResult (entry)
      growth_absorb.py    3-stage leftover absorption (shape_gate consumer)
      room_growth.py      GrownRoom / GrowthResult / LayoutFixture / RoomSpec
      shape_gate.py       reflex helpers (count_reflex_vertices)
      corridor*.py        Phase 8 carve → CorridoredLayout (entry: corridor)

    New to this repo:
      program_adapter.py  ProgramRequest → Cell LayoutFixture (S04-D3)
      anchors.py          subtract_anchors donut-hole (S04-D4; fixed-room
                          re-insertion deferred to Step 07)

Internal dataclasses (`Atom` / `Region` / `Territory` / `DimensionPolicy` /
`GrownRoom` / `CorridoredLayout` …) live alongside their producing stage
(S03-D6) and are **not** re-exported from ``room_layout`` / ``room_layout.schema``
— that is the D001 public contract; these are pipeline internals. Tests import
directly from the stage module.

References: ``docs/000_Pipeline_Overview.md`` §3; ``004_Step04_AlgorithmCore_Plan.md``
§3; ``legacy/step03/003_Step03_GeometryPipeline_Plan.md`` §3;
``archive/celllayout/algorithm/celllayout_tf/`` (porting source).
"""
