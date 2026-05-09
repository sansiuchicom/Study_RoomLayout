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
Step 05 done (merged `7064132`). Ready for Step 06 kickoff.
```

Current Step:

```text
Step 05. Geometry Kernel / Atom Resolution Commitments
```

Current Step status:

```text
Done 2026-05-08; 9 work-item commits + 2 review-followup commits merged via
`--no-ff` to main as `7064132`; `step05-geometry-kernel` branch deleted.
v3.2 algorithm imported (LIR + per-family recursive + 50% rule); D006 amended
via D019 (atom_size 300mm + atom_inclusion_threshold 0.5; per-family proportional
sizing; interior grid + boundary polygon). 80 pytest passed. D1 sloped fixture
added. X2 scope split honored (Step 05 algorithm only; Step 07 will integrate
Decomposition → RegionSet/AtomSet via M2 layered approach + v12 zoning).
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
005_Step05_GeometryKernel_Plan.md     (Completed; pending move to legacy/step05/ at Step 06 kickoff)
005_Step05_GeometryKernel_Tracker.md  (Completed; pending move to legacy/step05/ at Step 06 kickoff)
```

Step 04 docs archived to `legacy/step04/` (during Step 05 §4.1, 2026-05-08).

Step 01 docs archived to `legacy/step01/` (during Step 02 §4.1).
Step 02 docs archived to `legacy/step02/` (during Step 03 §4.1).
Step 03 docs archived to `legacy/step03/` (during Step 04 §4.1, 2026-05-07).

Next Step files to create:

```text
TBD at Step 06 kickoff (e.g., 006_Step06_ProgramConstraintEngine_Plan.md, _Tracker.md)
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
Confirm Step 04 close: git merge --no-ff step04-apartment-fixtures into main,
delete branch, push to origin. Then Step 05 kickoff (Geometry Kernel /
Atom Resolution Commitments) per Pipeline §15.
```

Step 04 delivered:

```text
- proto3.target.{TargetAdapter, ApartmentAdapter}
- proto3.stages.{stage00_load, stage01_program} (frame; Step 06 replaces/extends)
- proto3.schema.validation.ProgramInstantiationFailure
- 5 fixtures (apartment_minimal, _4bed_2bath, _l_shape, _no_bath, _too_small)
- tests/fixture_matrix.py (MATRIX dict + expected_failure metadata)
- tests/test_target_adapter.py + test_stage00_load.py + test_stage01_program.py + test_fixtures_roundtrip.py (17 신규 tests; total 39 passed)
- notebooks/step04_fixture_overview.ipynb
- D-decisions: D016 amendment H012 (legacy link policy)
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
