# 000 Progress Tracker

Status: Current working status only
Scope: active work item, completed work, next actions, blockers
Last updated: 2026-05-25

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
Step 02 (Core schema port) done (2026-05-25). The full D001 external
contract is implemented as typed dataclasses in
`src/room_layout/schema/` across 6 modules — geometry / program /
output / failure / serialize / validators — re-exported from
top-level `room_layout` per Plan §5. 92 pytest tests passing in
0.16 s; ruff lint + format clean; chore close commit prepared on
`step02-coreschema` branch (pending push + no-ff merge to `main`
+ CI green on both).

D-series cumulative state: D001-D006 accepted; proto3:D001-D023
audited (Carry 13 / Modify 4 / Drop 3 / Defer 3); 13 Step-local
S02-D1..D13 decisions logged in Step 02 Plan §2 (notably S02-D8
semantic-migration, S02-D9 single Role + corridor runtime reject,
S02-D11 no debug_artifacts, S02-D13 no viz this Step).

Next: open Step 03 (Geometry pipeline port) per Plan §7 / S02-D8.
Step 03 moves Cell Phase 3–8 modules from
`archive/celllayout/algorithm/celllayout_tf/` into
`src/room_layout/stages/`, refactors each module's schema
references to `from room_layout.schema import ...`, and adds the
first per-stage matplotlib renderers under `src/room_layout/viz/`
(the development bridge — Step 07 swaps in canonical SVG). Step 03
is the second D005-triggered branch (regression risk + integration
work) → `step03-geometrypipeline` branch.
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

---

# 3. Next actions

1. **Land Step 02** to `main`:
   - `git push origin step02-coreschema` → confirm CI green on the branch.
   - `git switch main && git merge --no-ff step02-coreschema && git push`.
   - Confirm CI green on `main`.
   - `git branch -d step02-coreschema` (only after CI green on `main`).
   - Flip the two pending boxes in `002_Step02_CoreSchema_Tracker.md`
     §2 (`CI green on step02-coreschema` / `CI green on main`) and §1
     4.9; this can ride as a follow-up tracker-only commit on `main`.

2. **Open Step 03 (Geometry pipeline port)** on a
   `step03-geometrypipeline` branch (D005 triggers fire again —
   regression risk + integration work touching the whole pipeline):
   - Branch kickoff §4.1 commit (per `proto3:D016` H011 deferred-archive
     pattern):
     - `git mv 002_Step02_CoreSchema_Plan.md 002_Step02_CoreSchema_Tracker.md legacy/step02/`
     - Write `003_Step03_GeometryPipeline_Plan.md` + Tracker at repo root.
   - Plan §4 work items derive from Plan §7 of Step 02 + Pipeline §3
     internal flow: move Cell Phase 3–8 modules from
     `archive/celllayout/algorithm/celllayout_tf/` into
     `src/room_layout/stages/`, refactor schema imports to
     `from room_layout.schema import ...` (S02-D8 semantic migration),
     and add per-stage matplotlib renderers under
     `src/room_layout/viz/` as the development bridge (Step 07 swaps in
     canonical SVG).
   - Establish `tests/golden/<fixture>/` infrastructure using
     `validate_input` + semantic-equality comparison (per Pipeline §5.1).

---

# 4. Blockers

_None._
