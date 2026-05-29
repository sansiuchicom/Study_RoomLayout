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
Step 04 (Algorithm core port) done on branch `step04-algorithmcore`
(2026-05-29), pending no-ff merge to `main`. Cell Phase 6–8 ported to
`src/room_layout/stages/`: seed_placement / growth_seed / growth_cells /
growth_partition / growth_absorb / room_growth / shape_gate + the corridor
stack (corridor + corridor_params/index/path/stage1/stage2). Plus two
new-to-this-repo bridges: `program_adapter` (S04-D3, ProgramRequest→Cell
fixture) and `anchors.subtract_anchors` (S04-D4 donut-hole half).
**Verified byte-identical to Cell live across all 33 cases** (growth +
corridor cross-checked) — the strongest correctness anchor. Goldens in
`tests/golden/`: layout / seed / layout_auto / corridor / corridor_auto
region-id digests + PNG sidecars; growth driven both by ported manual
seeds (S04-D7 a1) and the auto production path. 636 pytest passing + 4
xfailed under the canonical runtime (conda `IfcOpenHouse`, GEOS 3.14.1);
ruff clean.

Key Step-04 decisions (Plan §2 S04-D1..D8): algorithm follows Cell,
interface follows the new schema (D1); Step 04 ends at region-set rooms
(`CorridoredLayout`), labeling/run() = Step 07 (D2); target-agnostic
growth + 7→4 role collapse + id-identity preservation (D3); anchors =
footprint donut-hole (D4); region-id digest goldens (D5); flat `stages/`
(D6); manual-seed goldens + separate auto coverage (D7); growth takes
Step 03 outputs as params, no recompute (D8).

Finding (S04-D7 / 4.12): the auto seed path is hub-dominant (less balanced
than hand-tuned manual) — faithful Cell behavior, area-balance deferred.

Deferred to Step 07 — the anchor / connectivity cluster: anchor fixed-room
re-insertion (4.15, polygon room = labeling concern; anchors are the lone
non-Cell-port piece), corridor single-connected-component (PHASE8 §11,
xfail PoC pinned), access guarantee (S04-D4). All converge where the
region result becomes the polygon `LabeledRoomLayout`.

D-series cumulative state: D001-D006 accepted; proto3:D001-D023 audited;
S02-D1..D13 + S03-D1..D16 + S04-D1..D8 logged in their Step Plans.

Next: open Step 05 (Program layer port) per Pipeline §5.1.
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
| 2026-05-29 | Step 04 Algorithm core port — completed on `step04-algorithmcore` (22 work-item commits; 4.15 anchor re-insertion deferred to Step 07). Cell Phase 6–8 (seed/growth/corridor) + shape_gate ported, **byte-identical to Cell live on all 33 cases**; + `program_adapter` (S04-D3) + `subtract_anchors` (S04-D4 donut-hole). layout/seed/auto/corridor goldens + PNG sidecars; 636 pytest + 4 xfail under GEOS 3.14.1; ruff clean. S04-D1..D8. Verified via 33-case Cell cross-check + 2 adversarial-verification workflows (growth_absorb, growth_partition: 0 confirmed). Pending no-ff merge to `main`. |

---

# 3. Next actions

Step 04 is complete on `step04-algorithmcore` (22 commits). Remaining:

1. **Merge Step 04 to `main`** — `git merge --no-ff step04-algorithmcore`
   (proto3:D015 no-squash). Then archive Step 04 docs at the Step 05 §4.1
   commit (`git mv 004_Step04_*.md legacy/step04/`, proto3:D016 H011).

2. **Open Step 05 (Program layer port)** per Pipeline §5.1 — proto3
   `stages/stage01_program.py` + `stage02_gate.py`; the 4 domain gates
   (`check_min_area` / `check_min_dim` / `check_access_schema` /
   `check_multi_floor_feasibility`) in `constraints/gates.py`;
   `proto3:D020` / `D023` carry. (Steps 03→04 and 05→06 are parallelizable
   per Pipeline §5.3; Step 07 is the join + where the Step-04-deferred
   anchor/connectivity cluster lands.)

---

# 4. Blockers

_None._
