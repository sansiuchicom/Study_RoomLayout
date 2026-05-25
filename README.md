# Study_RoomLayout

Room layout generation component for the PlanBIM synthetic-BIM training-data pipeline.

Successor to two predecessor prototypes (both archived under `archive/`):

- `archive/proto3/` — `Study_RoomLayout_proto3` (framework / Step 01-06).
- `archive/celllayout/` — `Study_RoomLayout_Cell` (algorithm testfield / Phase 1-8).

Both predecessors are preserved with full git history via `git subtree merge`.
See `MIGRATION_LOG.md` for the migration trail.

## Status

Step 01 (Project skeleton) closed 2026-05-25. The new source tree
(`src/room_layout/`) contains the package scaffold + `viz/` placeholder
subpackage; `pyproject.toml` builds, smoke tests pass, ruff lints, and
GitHub Actions CI is green on `main`.

**Next**: Step 02 (Core schema port) on the `step02-coreschema` branch.

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
