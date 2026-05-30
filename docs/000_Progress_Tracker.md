# 000 Progress Tracker

Status: Current working status only
Scope: active work item, completed work, next actions, blockers
Last updated: 2026-05-30

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
Step 04 (Algorithm core port) merged to `main` 2026-05-29
(`969c4f0`, --no-ff). Step 05 (Program layer port) **open** on branch
`step05-programlayer` (2026-05-30) — kickoff (4.1) in progress.

Step 04 recap: Cell Phase 6–8 ported to `src/room_layout/stages/`
(seed_placement / growth_* / room_growth / shape_gate + corridor stack)
+ `program_adapter` (S04-D3) + `anchors.subtract_anchors` (S04-D4
donut-hole half). **Verified byte-identical to Cell across all 33
cases.** Goldens: layout / seed / layout_auto / corridor / corridor_auto
region-id digests + PNG sidecars. 643 pytest + 5 xfail (conda
`IfcOpenHouse`, GEOS 3.14.1); ruff clean.

Step 05 scope (Plan §1 / §2 S05-D1..D7, settled in chat 2026-05-30):
port proto3 `stage01_program` + `stage02_gate` + 4 domain gates onto the
new schema. **Boundary (S05-D2): Step 05 = gate machinery + rule *type*
(`TargetRules`); Step 06 = rule *values + loading* (JSON/adapter).**
Gates are pure functions taking primitive domain values by injection.
Schema reshape (S05-D1): `area_min_m2` → required (gate input);
`area_target_m2` → optional, kept as the Step 11 diffusion-priority hook
(growth is target-agnostic so it has no consumer yet — S04-D3). No
`ProgramInstance` type (S05-D5 — nothing to concretize). 33 golden
inputs regenerate (`area_target` placeholder → null); region-id digests
asserted unchanged (the S04-D3 target-agnostic regression guard).

Deferred to Step 07 — the anchor / connectivity cluster (S04 carry):
anchor fixed-room re-insertion, corridor single-connected-component
(xfail PoC pinned), access guarantee. Plus the program-side join:
per-room post-growth area/dim check (1.5 m² rejection — distinct from
Step 05's aggregate admission gate), `run()`, `LabeledRoomLayout`.

D-series cumulative state: D001-D006 accepted; proto3:D001-D023 audited;
S02-D1..D13 + S03-D1..D16 + S04-D1..D8 logged in their Step Plans;
S05-D1..D7 in `005_Step05_ProgramLayer_Plan.md` §2.
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
| 2026-05-30 | Step 05 Program layer port — **kickoff** on `step05-programlayer`. Plan/Tracker landed; Step 04 docs archived → `legacy/step04/`. §1/§2 settled over chat (S05-D1..D7): area-field realignment + Step05/06 type-value boundary + no `ProgramInstance`. |

---

# 3. Next actions

Step 05 (Program layer port) open on `step05-programlayer`. Work items
(Plan §4): 4.1 kickoff (in progress) → 4.2 schema realign → 4.3
`TargetRules` → 4.4 `ProgramInstantiationFailure` → 4.5 gates → 4.6
stage01 → 4.7 stage02 → 4.8 golden regen → 4.9 close + merge.

Immediate: finish 4.1 (commit Plan/Tracker + archived Step 04 docs +
this tracker cleanup), then start 4.2 (`schema/program.py` area-field
realignment, S05-D1).

(Steps 03→04 and 05→06 are parallelizable per Pipeline §5.3; Step 07 is
the join + where the Step-04-deferred anchor/connectivity cluster lands,
alongside the program-side per-room post-growth check.)

---

# 4. Blockers

_None._
