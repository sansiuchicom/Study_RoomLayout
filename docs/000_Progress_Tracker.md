# 000 Progress Tracker

Status: Current working status only
Scope: active work item, completed work, next actions, blockers
Last updated: 2026-05-24

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
Step 01 (Project skeleton) done (2026-05-25). Repo has a working
pyproject build (`pip install -e .`), the `room_layout` package +
`viz` placeholder subpackage, pytest smoke tests (3 passing on
Python 3.10), ruff lint + format clean, and a GitHub Actions
CI workflow green on `main` (first run `26391806249`, 16 s). Output
directory scaffold landed per D006; `legacy/` ready for next-Step
archival per proto3:D016 H011.

D-series cumulative state: D001-D006 accepted; proto3:D001-D023
audited (Carry 13 / Modify 4 / Drop 3 / Defer 3 after D005 amended
proto3:D015). New cross-cutting decisions D005 (workflow) and D006
(output directories) added during Step 01.

Next: open Step 02 (Core schema port) per proto3:D015 / D016.
Step 02 hits two D005 triggers (regression risk + integration work
touching the whole downstream chain), so it proceeds on a
`step02-coreschema` branch. Branch kickoff §4.1 commit will
git-mv 001_Step01_Skeleton_*.md to legacy/step01/.
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

---

# 3. Next actions

1. **Open Step 02 (Core schema port)** on a `step02-coreschema`
   branch (D005 triggers fire — regression risk + integration work):
   - Branch kickoff §4.1 commit bundles two operations per
     `proto3:D016` H011 deferred-archive pattern:
     - `git mv 001_Step01_Skeleton_Plan.md 001_Step01_Skeleton_Tracker.md legacy/step01/`
     - Write `002_Step02_CoreSchema_Plan.md` + Tracker at repo root.
   - Plan §4 work items will be derived from D001 typed sketches
     (`ShapeInput` / `FloorShape` / `ShapePart` / `VerticalAnchor` /
     `ProgramRequest` / `SpaceUnitSpec` / `LabeledRoomLayout` etc.)
     plus `Role` Literal, `FailureRecord`, and strict
     `proto3:D017` Literal validation on deserialization.
2. Cell algorithm modules in `archive/celllayout/` use their own
   internal schema today; Step 02 also defines the refactor scope
   that Step 03 (geometry pipeline port) will execute (S01-Q1 = "Refactor
   in-place" — Cell modules adopt the new schema, no internal-vs-
   public schema split).
3. Land Step 02 via `git merge --no-ff` to `main`.

---

# 4. Blockers

_None._
