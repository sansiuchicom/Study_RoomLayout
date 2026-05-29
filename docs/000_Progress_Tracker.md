# 000 Progress Tracker

Status: Current working status only
Scope: active work item, completed work, next actions, blockers
Last updated: 2026-05-29

---

## 0. Purpose

This file tracks current implementation progress.

It should stay short. It should not duplicate the full framework, full stage
list, or full decision record.

Canonical references:

```text
Framework / pipeline / terminology:
  000_Pipeline_Overview.md

Accepted decisions / rationale:
  000_Architecture_Decisions.md
```

---

# 1. Current status

```text
Step 03 (Geometry pipeline port) done (2026-05-28). Cell Phase 3–4
geometry stages ported to `src/room_layout/stages/` against the new
schema (S03-D13 floor-scoped): territory / atomize / regionize /
atom_graph / region_graph + dimensions + _helpers. Dev-bridge
matplotlib viz (atomize / regionize / region-graph overlay + input
renderer in the demo CLI) under `src/room_layout/viz/`. Per-stage
golden infra in `tests/golden/` — 33 Cell showcase cases × 3 stages
(atomize digest / regionize full-geom / region_graph edges), Polygon-
aware comparator with `--update-goldens`. 371 pytest passing **under the
canonical runtime** (conda env `IfcOpenHouse`: shapely 2.1.2 / GEOS
3.14.1; ~38 s, golden-heavy); ruff clean. NB: the regionize / region_graph
goldens are GEOS-version-sensitive — a different GEOS build (e.g. base
conda GEOS 3.13.1) shows ~20 false failures, so CI pins `geos=3.14.1`.

Key Step-03 course-corrections (Plan §2 S03-D13..D16): stages take
`FloorShape` not `ShapeInput` (D13); atomize golden is a digest, not
per-atom geometry (D14); region_graph golden is edges-only (D15);
`shape_gate` is a Phase 6/7 reflex helper — deferred to Step 04, not
a Phase-5 gate stage (D16). Two dependency-order fixes during port:
territory before atomize; atom_graph (region_graph dep) was
mis-bucketed as Phase 8.

D-series cumulative state: D001-D006 accepted; proto3:D001-D023
audited; S02-D1..D13 + S03-D1..D16 logged in their Step Plans.

Next: open Step 04 (Algorithm core port) per Step 03 Plan §7. Step 04
ports Cell Phase 6–8 (seed_placement / growth_* / room_growth /
corridor_*) + `shape_gate` (with its consumer growth_absorb), reusing
the Step 03 stage outputs (Region / AtomGraph / RegionGraph / atoms)
as growth input. Third D005-triggered branch →
`step04-algorithmcore` branch.
```

---

# 2. Completed

| Date | Item |
|---|---|
| 2026-05-24 | `git init` + README + MIGRATION_LOG |
| 2026-05-24 | Subtree merge `archive/proto3/` (history preserved) |
| 2026-05-24 | Subtree merge `archive/celllayout/` (history preserved) |
| 2026-05-24 | GitHub remote `origin` connected, `main` pushed |
| 2026-05-24 | `docs/000_*` scaffold |
| 2026-05-24 | proto3 D001–D023 inherited-decision audit |
| 2026-05-24 | D001–D004 contract lock + Pipeline §2 typed sketches |
| 2026-05-24 | Pipeline §3 internal flow + §4 terminology |
| 2026-05-24 | Pipeline §5 Step map (7 active + 2 deferred) |
| 2026-05-25 | D005 lock — solo-mode workflow (default `main`, branch on triggers) |
| 2026-05-25 | D006 lock — output directory convention (3-category + per-stage layout) |
| 2026-05-25 | Step 01 Project skeleton — completed (8 work-item commits + 1 side-fix; CI green) |
| 2026-05-25 | Step 02 Core schema port — completed (9 work-item commits incl. chore close; 92 pytest passing; ruff clean; latent 4.3 LinearRing.area bug surfaced + fixed in 4.6) |
| 2026-05-28 | Step 03 Geometry pipeline port — completed (territory / atomize / regionize / atom_graph / region_graph + dev-bridge viz + 33×3 goldens; 371 pytest passing under GEOS 3.14.1 (IfcOpenHouse); ruff clean; S03-D13..D16 course-corrections; shape_gate deferred to Step 04) |
| 2026-05-28..29 | Post-Step-03 review hardening (on `main`, 4 commits) — CI repinned to conda-forge + `geos=3.14.1` (regionize goldens are GEOS-version-sensitive); atom/region graph `neighbors`/`edge_between` made O(1) + atom edges keyed by `atom_id` not list index; `xfail` PoCs for three latent geometry bugs (B5 regionize Pass-B atom loss; B6 region shape↔atom_ids desync; C10 territory 3-way-overlap hole); pytest `pythonpath` += `src` (bare run w/o install); `to_dict`/`from_dict` skip `init=False` derived fields (the new graph indexes had broken `RegionGraph` serialization); README/tracker doc sync. 373 passing + 3 xfailed |

---

# 3. Next actions

Step 03 landed on `main` (commit `b2cf8d9`, 2026-05-28); a post-merge
review-hardening pass on `main` followed (see log above). Remaining:

1. **Open Step 04 (Algorithm core port)** on a `step04-algorithmcore`
   branch (D005 triggers fire — regression risk + integration work):
   - Branch kickoff §4.1 commit (per `proto3:D016` H011 deferred-archive
     pattern):
     - `git mv 003_Step03_GeometryPipeline_Plan.md 003_Step03_GeometryPipeline_Tracker.md legacy/step03/`
     - Write `004_Step04_AlgorithmCore_Plan.md` + Tracker at repo root.
   - Plan §4 work items derive from Step 03 Plan §7 + Pipeline §3: port
     Cell Phase 6–8 (`seed_placement` / `growth_seed` / `growth_cells` /
     `growth_partition` / `growth_absorb` / `room_growth` / `corridor` +
     `corridor_*`) **plus `shape_gate`** (the reflex helper
     `growth_absorb` consumes — deferred from Step 03 per S03-D16).
   - Reuse Step 03 stage outputs (Region / AtomGraph / RegionGraph /
     atoms) as growth input; extend the per-stage golden + viz infra
     (seed / layout / corridor) on the same 33 cases. Final stage
     (corridor) emits the `LabeledRoomLayout` — the input to Step 06 `run()`.

---

# 4. Blockers

_None._
