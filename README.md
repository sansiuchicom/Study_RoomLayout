# Study_RoomLayout

Room layout generation component for the PlanBIM synthetic-BIM training-data pipeline.

Successor to two predecessor prototypes (both archived under `archive/`):

- `archive/proto3/` — `Study_RoomLayout_proto3` (framework / Step 01-06).
- `archive/celllayout/` — `Study_RoomLayout_Cell` (algorithm testfield / Phase 1-8).

Both predecessors are preserved with full git history via `git subtree merge`.
See `MIGRATION_LOG.md` for the migration trail.

## Status

Step 05 (Program layer port) merged to `main` (2026-06-02, `f3f4906`).
The full algorithm now lives in `src/room_layout/stages/` — Cell **Phase
3–8**: territory / atomize / regionize / atom_graph / region_graph (Step 03)
+ seed_placement / growth_* / room_growth / shape_gate / corridor stack
(Step 04) — plus `program_adapter` and `anchors.subtract_anchors`. Step 05
added the program **admission** layer: `constraints/gates.py` (4 domain
gates), `schema/target.py` (`TargetRules`), and `stages/stage01_program.py`
+ `stages/stage02_gate.py`. Ported growth + corridor are **byte-identical to
the predecessor `Study_RoomLayout_Cell` across all 33 cases**. Per-stage
golden regression (layout / seed / corridor digests + PNG sidecars). 690
pytest + 5 xfail under the canonical runtime (conda `IfcOpenHouse`: shapely
2.1.2 / GEOS 3.14.1).

Step 04 ends at a region-based `CorridoredLayout` (S04-D2); polygonization +
`LabeledRoomLayout` + the deferred anchor / corridor-connectivity cluster are
**Step 07**. Step 05 is admission only (pre-growth feasibility); the public
`run()` entry point is **Step 07**.

**Next**: Step 06 (Target rules system) — JSON loader + `TargetAdapter` +
per-typology rule files that populate the `TargetRules` type.

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

Run tests / lint locally **under the canonical runtime** (conda env
`IfcOpenHouse`, GEOS 3.14.1):

```bash
conda activate IfcOpenHouse   # GEOS 3.14.1 — required for the goldens
python -m pytest
ruff check .
ruff format --check .
```

> ⚠️ The geometry goldens are **GEOS-version-pinned (3.14.1)**. On a different
> GEOS build (e.g. base conda 3.13.1) ~60+ `atomize`/`regionize`/`region_graph`
> golden tests show spurious diffs — **run under `IfcOpenHouse`**. (The
> layout/corridor goldens are region-id digests and stay GEOS-stable.)
>
> The `regionize` / `region_graph` goldens are pinned to GEOS 3.14.x (the
> `IfcOpenHouse` runtime). On a different GEOS build they may show spurious
> diffs — see the GEOS-pin note in `tests/_golden.py`.
