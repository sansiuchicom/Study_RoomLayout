# Study_RoomLayout

Room layout generation component for the PlanBIM synthetic-BIM training-data pipeline.

Successor to two predecessor prototypes (both archived under `archive/`):

- `archive/proto3/` — `Study_RoomLayout_proto3` (framework / Step 01-06).
- `archive/celllayout/` — `Study_RoomLayout_Cell` (algorithm testfield / Phase 1-8).

Both predecessors are preserved with full git history via `git subtree merge`.
See `MIGRATION_LOG.md` for the migration trail.

## Status

Step 03 (Geometry pipeline port) done, merged to `main` 2026-05-28. The
geometry stages live in `src/room_layout/stages/` — territory / atomize /
regionize / atom_graph / region_graph (+ dimensions, `_helpers`) — against
the D001 schema (S03-D13 floor-scoped). Per-stage golden regression covers
33 Cell showcase cases. Tests pass under the canonical runtime (conda env
`IfcOpenHouse`: shapely 2.1.2 / GEOS 3.14.1); CI pins `geos=3.14.1` because
the regionize goldens are GEOS-version-sensitive.

**Next**: Step 04 (Algorithm core port) — Cell Phase 6–8 (`growth_*` /
`corridor*`) plus `shape_gate` (the reflex helper deferred from Step 03 per
S03-D16), against the new schema.

Canonical docs live under `docs/`:

- `docs/000_Architecture_Decisions.md` — accepted decisions (D001–D006
  + the proto3 D001–D023 inheritance audit).
- `docs/000_Pipeline_Overview.md` — external contract, internal
  pipeline, terminology, and Step map (7 active + 2 deferred).
- `docs/000_Progress_Tracker.md` — current implementation status and
  next actions.

## Installation (dev)

```bash
python -m pip install -e .[dev]      # tests + lint
python -m pip install -e .[dev,viz]  # + matplotlib for stage viz
```

Run tests / lint locally:

```bash
python -m pytest
ruff check .
ruff format --check .
```

> The `regionize` / `region_graph` goldens are pinned to GEOS 3.14.x (the
> `IfcOpenHouse` runtime). On a different GEOS build they may show spurious
> diffs — see the GEOS-pin note in `tests/_golden.py`.
