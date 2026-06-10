# Study_RoomLayout

Room layout generation component for the PlanBIM synthetic-BIM training-data pipeline.

Successor to two predecessor prototypes (both archived under `archive/`):

- `archive/proto3/` — `Study_RoomLayout_proto3` (framework / Step 01-06).
- `archive/celllayout/` — `Study_RoomLayout_Cell` (algorithm testfield / Phase 1-8).

Both predecessors are preserved with full git history via `git subtree merge`.
See `MIGRATION_LOG.md` for the migration trail.

## Status

**Post-v1: Step 10 (multi-floor) complete** on `step10-multifloor` — the first
multi-floor target, **house**. `run()` now lays out multi-floor buildings:
building-level cardinality (`cardinality_scope`, so living/kitchen downstairs +
bedrooms above is valid), vertical-circulation continuity
(`VERTICAL_CIRCULATION_DISCONTINUOUS`), vc-only/empty floors handled
(never-crashes), per-floor SVG reused. The input model maps 1:1 from the
**ResearchBIM `Building`/`Storey`** consumer (the live adapter is Step 09). The
single-floor **apartment** path stays byte-identical. S10-D1..D13. **Merged
`--no-ff` to `main`** (`382966c`, 2026-06-10) after a pre-build + post-
implementation review response (the access-model discussion +
deferred findings live in `docs/000_multifloor_access.md`).

**v1 shipped** — Step 08 (SVG visualization) complete, the v1 **ship gate**
(Pipeline §5.1). On top of the Step 07 `run()` end-to-end core, v1 now has the
**canonical layered-SVG renderer** (`viz/svg.py` — `render()`, 12 ordered `<g>`
layers re-derived from our pipeline), a **`make_gif()`** pipeline-progression
animation (matplotlib frames via `pillow`), and a single `viz/palette.py`
visual vocabulary. SVG rides the existing `on_stage` hook — `run()` is
untouched (S08-D7) — and is opt-in via
`RunConfig(debug_artifacts=("json","svg"))`. Merged `--no-ff` to `main` after a
pre-merge review (one fix landed — `debug_artifacts` token validation #9; the
other findings are documented v1-accepted limitations / post-v1 deferrals).
S08-D1..D9. Post-v1: Step 09 (ResearchBIM adapter) + Step 10 (multi-floor),
both independent (Pipeline §5.2).

Step 07 (Entry point + labeling) complete and **merged to `main`** (`68e8df2`,
`--no-ff`, 2026-06-03) after an external + adversarial review response
(`0c03b69` — never-crashes hardening + anchor/schema validation). The public
entry point now works end-to-end:

```python
def run(shape: ShapeInput, program: ProgramRequest, *, seed: int) -> LabeledRoomLayout
```

`run()` (D001) joins the geometry half (Step 03/04: atomize → … → corridor) and
the program half (Step 05/06: admission gates + program building), then
**polygonizes** the region-based `CorridoredLayout` (S04-D2), runs the §3.8
**labeling** stage (7-class role/usage recovery + `area_m2`), re-inserts
`vertical_circulation` **anchor** rooms (S04-D4), applies the **per-room**
post-growth area/dim gate, **bridges** orphan corridors into one connected
spine, and assembles a `LabeledRoomLayout` (`valid=False` ⇒ non-empty
`failure_records`, proto3:D018; never crashes). A pure-function `on_stage`
trace hook + `debug_run` persistence (D006) and a final-layout matplotlib
renderer (S01-D10) ship too.

The geometry pipeline (Cell Phase 3–8) stays **byte-identical to the
predecessor `Study_RoomLayout_Cell` across all 33 cases** — the orphan-corridor
bridge is a *post-step* over the unchanged carve. 970 pytest + 4 xfail under the
canonical runtime (conda `IfcOpenHouse`: shapely 2.1.2 / GEOS 3.14.1); per-stage
+ end-to-end golden regression.

Two limitations are recorded as deferred (post-v1): target-agnostic growth can
grow a realistic program *invalid* (`docs/000_area_aware_growth.md`), and
wall-thickness clear-area inset (Progress Tracker §5.2).

**Next**: Step 08 (SVG visualization) — the v1 ship gate: a canonical 12-layer
SVG renderer + `make_gif()` consuming the `StageOutput` trace.

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
