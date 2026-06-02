# 000 Progress Tracker

Status: Current working status only
Scope: active work item, completed work, next actions, blockers
Last updated: 2026-06-02

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
Step 05 (Program layer port) **complete** on branch
`step05-programlayer` (2026-06-02, 18 commits) — pending no-ff merge to
`main`. Step 04 merged to `main` 2026-05-29 (`969c4f0`, --no-ff).

Step 05 delivered: the program **admission layer** (pre-growth: does a
program fit a floor at all?). Ported proto3 `stage01_program` +
`stage02_gate` + 4 domain gates onto the new schema.
- `constraints/gates.py` (NEW) — 4 pure gates, m units (S05-D4): area /
  dim / multi-floor active + access no-op stub. Domain scalars injected
  as primitives; `list[SpaceUnitSpec]` passed direct (option 가).
- `schema/target.py` (NEW) — `TargetRules` value bundle (S05-D3): 3
  fields (`density_factor` / `min_cardinality` / `requires_single_floor`).
- `stages/stage01_program.py` (NEW) — required-only cardinality gate only
  (S05-D8); returns specs unchanged (S05-D5, no `ProgramInstance`).
- `stages/stage02_gate.py` (NEW) — floor-scoped area + dim (S05-D6
  revised → 다: multi-floor is building-level, hoisted to Step 07).
- `schema/program.py` — area-field realignment (S05-D1): `area_min_m2`
  required (gate input); `area_target_m2` optional (diffusion-priority
  hook — growth is target-agnostic, S04-D3, so no consumer yet).
- `schema/failure.py` — `ProgramInstantiationFailure` (sibling, S05-D5).
- 33 golden `input.json` regenerated (S05-D7): `area_target` honest-fake
  → null; **region-id digests unchanged** — the empirical S04-D3
  target-agnostic regression guard.

Boundary (S05-D2): Step 05 = gate machinery + rule *type*; Step 06 =
rule *values + loading* (JSON/adapter). 690 pytest + 5 xfail (conda
`IfcOpenHouse`, GEOS 3.14.1); ruff clean. Pre-close adversarial review:
0 gate-logic bugs, 5 items fixed (`c5c06a4`).

Deferred to Step 07 — anchor/connectivity cluster (S04 carry: anchor
fixed-room re-insertion, corridor single-component xfail, access
guarantee) + program-side join: `check_multi_floor_feasibility` call
site, per-room post-growth area/dim check (1.5 m² rejection — distinct
from Step 05's aggregate admission), `run()`, `LabeledRoomLayout`.

D-series cumulative: D001-D006 accepted; proto3:D001-D023 audited;
S02-D1..D13 + S03-D1..D16 + S04-D1..D8 + S05-D1..D8 in their Step Plans.

Next: merge Step 05 → `main`, then open Step 06 (Target rules system).
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
| 2026-05-29 | Step 04 Algorithm core port — completed + **merged to `main`** (`969c4f0`, --no-ff; 22 work-item commits; 4.15 anchor re-insertion deferred to Step 07). Cell Phase 6–8 (seed/growth/corridor) + shape_gate ported, **byte-identical to Cell live on all 33 cases**; + `program_adapter` (S04-D3) + `subtract_anchors` (S04-D4 donut-hole). layout/seed/auto/corridor goldens + PNG sidecars; 643 pytest + 5 xfail under GEOS 3.14.1; ruff clean. S04-D1..D8. Verified via 33-case Cell cross-check + 2 adversarial-verification workflows (growth_absorb, growth_partition: 0 confirmed). |
| 2026-06-02 | Step 05 Program layer port — completed on `step05-programlayer` (18 commits; 8 work items). `constraints/gates.py` (4 pure gates, m units) + `schema/target.py` (`TargetRules`) + `ProgramInstantiationFailure` + `stage01_program` (cardinality only, S05-D8) + `stage02_gate` (floor-scoped area+dim, S05-D6 revised). `area_min_m2` → required / `area_target_m2` → optional (S05-D1); 33 golden inputs regenerated, **region-id digests unchanged** (S04-D3 target-agnostic guard, S05-D7). S05-D1..D8. Pre-close adversarial review: 0 gate-logic bugs, 5 fixes (`c5c06a4`). 690 pytest + 5 xfail under GEOS 3.14.1; ruff clean. Pending no-ff merge to `main`. |

---

# 3. Next actions

Step 05 complete on `step05-programlayer` (18 commits). Remaining:

1. **Merge Step 05 to `main`** — `git merge --no-ff step05-programlayer`
   (proto3:D015 no-squash). Then archive Step 05 docs at the Step 06 §4.1
   commit (`git mv 005_Step05_*.md legacy/step05/`, proto3:D016 H011).

2. **Open Step 06 (Target rules system)** per Pipeline §5.1 — the JSON
   loader + `TargetAdapter` + per-typology `data/target_rules/<t>.json`
   that *populate* the `TargetRules` type Step 05 defined (S05-D2 — values
   + loading). `proto3:D021` / `D022` carry; role↔usage mapping table
   lands here per D001.

(Step 07 is the join: stage01/stage02 run as the program-side entry, the
gate functions get a second binding as the per-room post-growth check,
`check_multi_floor_feasibility` gets its call site, and the
Step-04-deferred anchor/connectivity cluster lands.)

---

# 4. Blockers

_None._
