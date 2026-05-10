# 000 Progress Tracker

Status: Current working status only  
Scope: active Step, active files, completed work, next actions, blockers  
Last updated: 2026-05-09

---

## 0. Purpose

This file tracks current implementation progress.

It should stay short. It should not duplicate the full framework, full Stage list, or full decision record.

Canonical references:

```text
Framework / Stage model / Step map:
  000_Pipeline_Overview.md

Accepted decisions / rationale:
  000_Architecture_Decisions.md
```

---

# 1. Current status

Current phase:

```text
Step 06 in progress (kickoff §4.1, 2026-05-09). Branch `step06-program-constraint-engine`.
```

Current Step:

```text
Step 06. Program & Domain Constraint Engine
```

Current Step status:

```text
Started 2026-05-09. Plan v3 (after two external reviews by other Claude
instances): 19 decisions / 10 work items (4.3a 신설) / 28 DoD / 13
deferred / 11 risks. Landed:
  §4.1 (`3f09cbe`) — Step 05 archive + step06 module scaffold + step05
       schema export cleanup. 82 passed.
  §4.2 (`f241d58`) — ProgramRequest dataclass + Role Literal + spaces
       strict deserialize + serialize.py typing.Union fix. 92 passed.
  §4.3 (`0da364b`) — TargetRules + apartment.json data package +
       adapter target check + pyproject package-data. 117 passed.
  §4.3a (`372090b`) — generic TargetAdapter reform (S06-D22) + 3-layer
       extensibility model README + D022 placeholder + .gitignore
       build/dist. 120 passed.
Remaining:
  §4.4 DomainGateFailure + gates module
  §4.5 Stage 01 본격화 (모든 SpaceUnitSpec 필드 + dup/unknown/type guards)
  §4.6 Stage 02 gate + Pipeline §9.10 update + R2 regression
  §4.7 fail-loud sweep (RunConfig validation + threshold wiring +
       palette/render strict)
  §4.8 step06 program gate overview notebook
  §4.9 close (Plan/Tracker, Progress Tracker, D020/D021/D022 finalize)
```

---

# 2. Active files

Global docs:

```text
000_Pipeline_Overview.md
000_Architecture_Decisions.md
000_Progress_Tracker.md
000_User_Profile.md        # maintained separately by the user
```

Active Step files:

```text
006_Step06_ProgramConstraintEngine_Plan.md     (In progress)
006_Step06_ProgramConstraintEngine_Tracker.md  (In progress)
```

Step 05 docs archived to `legacy/step05/` (during Step 06 §4.1, 2026-05-09).
Step 04 docs archived to `legacy/step04/` (during Step 05 §4.1, 2026-05-08).
Step 03 docs archived to `legacy/step03/` (during Step 04 §4.1, 2026-05-07).
Step 02 docs archived to `legacy/step02/` (during Step 03 §4.1).
Step 01 docs archived to `legacy/step01/` (during Step 02 §4.1).

Next Step files to create:

```text
TBD at Step 07 kickoff (e.g., 007_Step07_RegionAtomDecomposition_Plan.md, _Tracker.md)
```

---

# 3. Completed planning decisions

Summary only. See `000_Architecture_Decisions.md` for canonical details.

Completed:

```text
- Step / Stage / Search Orchestrator / Cross-cutting Infrastructure / Target terminology separated.
- Step 00 removed.
- Implementation Steps use 001–014.
- Candidate Search is not a Stage; it is the Search Orchestrator.
- Runtime pipeline uses Stage 00–13.
- Stage 10–13 are Atom Growth → Pre-repair Validation → Repair → Post-repair Validation / Output.
- Apartment-first but floor-rooted architecture accepted.
- ProgramInstance owns cardinality.
- Domain constraints are gates, not role scores.
- Region/atom dual layer accepted.
- Greedy growth is first-pass replaceable algorithm, not architecture invariant.
- Dataclass-first schema accepted.
- SVG-first visualization accepted.
- Empty anchor fields required early, even before multi-floor implementation.
- Debug output should be ignored by default.
- Legacy doc relative links are not maintained post-archive (H012, Step 04 §4.1).
```

---

# 4. Next actions

Immediate next action:

```text
Step 06 §4.4 — DomainGateFailure hierarchy + proto3.constraints.gates
module (4 pure functions). Note: pre-§4.4 cleanup commits land first
to absorb two external reviews (chore: serialize docstring / Tracker
drift / ApartmentAdapter remnants / _MismatchAdapter target_type;
design: required-only policy, Stage 02 fail-only, cardinality dedup,
access gate dormant scaffold, rules_loader completeness, area gate
boundary, multi-floor assumption). After cleanup, proceed 4.4→4.9.
```

Step 05 delivered (merged `7064132`, 2026-05-08):

```text
- proto3.geometry.{lir, grid, recursive, decompose} (v3.2 algorithm import)
- proto3.schema.geometry.{GeometricPiece, Decomposition} (M2 layer separation)
- proto3.schema.region_atom.Atom extended with parent_piece_id, family_id
- proto3.geometry.decompose.run() mm-friendly wrapper (X3 pattern, R-S05-7 mitigation)
- D1 sloped fixture (apartment_diagonal.json)
- D-decisions: D019 (per-family proportional atom sizing, D006 amendment)
- 80 pytest passed (39 + 41 신규)
- notebooks/step05_decomposition_overview.ipynb
```

---

# 5. Known open issues

These are not blockers for Step 04.

```text
- Exact geometry library choice is not yet fixed (Step 05).
- Exact decomposition algorithm is not yet fixed (Step 07).
- Exact growth scoring formula is not yet fixed (Step 11).
- Exact multi-floor anchor behavior is deferred to Step 14.
- Curved / non-Manhattan footprint normalization strategy is jointly deferred to Step 05.
```

---

# 6. Step status table

Canonical Step definitions live in `000_Pipeline_Overview.md`. This table only tracks progress.

| Step | Status | Notes |
|---:|---|---|
| 01 | Done | Project Skeleton / Global Docs (2026-05-03) |
| 02 | Done | Core Schema / Run Config / Debug Output Contract (2026-05-04) |
| 03 | Done | Visualization Renderer / Visual Vocabulary (2026-05-06) |
| 04 | Done | Apartment Fixtures / Target Adapter (2026-05-07; merged `822786a`) |
| 05 | Done | Geometry Kernel — v3.2 algorithm import + D019 (per-family proportional atom; D006 amendment) (2026-05-08; merged `7064132`) |
| 06 | In progress | Program & Domain Constraint Engine (kickoff 2026-05-09; branch `step06-program-constraint-engine`) |
| 07 | Not started | Region / Atom Decomposition |
| 08 | Not started | Graph Construction / Static Features / Role Scoring |
| 09 | Not started | Hub / Terminal / Spine Candidate Generation |
| 10 | Not started | Slot / Seed / Patch Generation |
| 11 | Not started | Atom Growth |
| 12 | Not started | Validation / Repair / FailureRecord |
| 13 | Not started | Search Orchestrator / No-good Records |
| 14 | Not started | Multi-floor Orchestration / Persistent Anchors |

---

# 7. Step 12 planning reminder

When Step 12 begins, split the plan internally into:

```text
Step 12A. Pre-repair validation / defect report
Step 12B. Repair / rectangularization
Step 12C. Post-repair validation / FailureRecord
```

Do not create separate global docs for these unless needed.

---

# 8. Working rule

Before starting a new Step:

```text
1. Read this progress tracker.
2. Check the canonical framework in 000_Pipeline_Overview.md.
3. Check relevant decisions in 000_Architecture_Decisions.md.
4. Create the active Step plan/tracker.
5. Update this file when the Step starts (kickoff §4.1), pauses, or finishes (close §4.8).
```
