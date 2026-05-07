# 000 Progress Tracker

Status: Current working status only  
Scope: active Step, active files, completed work, next actions, blockers  
Last updated: 2026-05-07

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
Step 04 in progress.
```

Current Step:

```text
Step 04. Apartment Fixtures / Target Adapter
```

Current Step status:

```text
In progress; §4.1 (archive Step 03 docs + scaffold step04 modules + Plan/Tracker
+ drift fix + Progress Tracker kickoff update + D016 amendment) landing.
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
004_Step04_ApartmentFixtures_Plan.md     (In progress)
004_Step04_ApartmentFixtures_Tracker.md  (In progress)
```

Step 01 docs archived to `legacy/step01/` (during Step 02 §4.1).
Step 02 docs archived to `legacy/step02/` (during Step 03 §4.1).
Step 03 docs archived to `legacy/step03/` (during Step 04 §4.1, 2026-05-07).

Next Step files to create:

```text
TBD at Step 05 kickoff (e.g., 005_Step05_GeometryKernel_Plan.md, 005_Step05_GeometryKernel_Tracker.md)
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
Step 04 §4.2 — Target adapter Protocol + ApartmentAdapter (target_rules with
min_cardinality dict per S04-D12). Then §4.3 Stage 00, §4.4 Stage 01 with
ProgramInstantiationFailure (per S04-D11/D13).
```

Step 04 produces:

```text
- proto3.target.{TargetAdapter, ApartmentAdapter}
- proto3.stages.{stage00_load, stage01_program} (와꾸; Step 06 replaces/extends)
- proto3.schema.validation.ProgramInstantiationFailure
- 5 fixtures (apartment_minimal, _4bed_2bath, _l_shape, _no_bath, _too_small)
- tests/fixture_matrix.py (MATRIX dict + expected_failure metadata)
- notebooks/step04_fixture_overview.ipynb
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
| 04 | In progress | Apartment Fixtures / Target Adapter (kickoff 2026-05-07) |
| 05 | Not started | Geometry Kernel / Atom Resolution Commitments |
| 06 | Not started | Program & Domain Constraint Engine |
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
