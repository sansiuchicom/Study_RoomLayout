# Study_RoomLayout

Room layout generation component for the PlanBIM synthetic-BIM training-data pipeline.

Successor to two predecessor prototypes (both archived under `archive/`):

- `archive/proto3/` — `Study_RoomLayout_proto3` (framework / Step 01-06).
- `archive/celllayout/` — `Study_RoomLayout_Cell` (algorithm testfield / Phase 1-8).

Both predecessors are preserved with full git history via `git subtree merge`.
See `MIGRATION_LOG.md` for the migration trail.

## Status

Step 02 (Core schema port) closed 2026-05-25. The full D001 external
contract lives in `src/room_layout/schema/` across 6 modules — geometry
/ program / output / failure / serialize / validators — and is re-exported
from top-level `room_layout`. Pytest passing, ruff clean, GitHub Actions
CI green.

**Next**: Step 03 (Geometry pipeline port) on the `step03-geometrypipeline`
branch — moves Cell Phase 3–8 modules from `archive/celllayout/algorithm/`
into `src/room_layout/stages/` against the new schema (S02-D8 semantic
migration).

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
