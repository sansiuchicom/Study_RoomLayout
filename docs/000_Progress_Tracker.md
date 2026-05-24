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
Phase-1 doc lock done (2026-05-24). New D-series D001–D004 accepted
(external contract, seed-first growth, triple-layer geometry, 7-class
role). proto3 D001–D023 audited (Carry 14 / Modify 3 / Drop 3 /
Defer 3). Pipeline Overview now carries the typed contract sketches
(§2) and per-stage operational narrative (§3) plus terminology (§4).

Next: derive the Step 01–N list given that archive/celllayout/ Phase
1–8 already covers atomize → corridor carving. Then scaffold src/ per
the public API boundary noted in archive/celllayout/PORTABLE_CORE.md
and open the first Step plan per proto3:D015 / D016 workflow.
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

---

# 3. Next actions

1. Derive the Step 01–N list: given `archive/celllayout/` Phase 1–8
   covers atomize → corridor carving, decide which Steps the new repo
   needs (port Cell, port proto3 program / gates / target_rules layer,
   wire `ShapeInput` / `ProgramRequest` / `LabeledRoomLayout` schema,
   ResearchBIM adapter scope, etc.).
2. Scaffold `src/<package>/` aligned with the public-API boundary
   noted in `archive/celllayout/PORTABLE_CORE.md`.
3. Open Step 01 plan per `proto3:D015` / `D016` (per-Step branch,
   Plan + Tracker companion docs).

---

# 4. Blockers

_None._
