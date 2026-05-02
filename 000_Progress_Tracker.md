# 000 Progress Tracker

Status: Current working status only  
Scope: active Step, active files, completed work, next actions, blockers  
Last updated: 2026-05-02

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
Pre-implementation planning complete enough to start Step 01.
```

Current Step:

```text
Step 01. Project Skeleton / Global Docs
```

Current Step status:

```text
Ready to begin.
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
None yet.
```

Next Step files to create:

```text
001_Step01_ProjectSkeleton_Plan.md
001_Step01_ProjectSkeleton_Tracker.md
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
```

---

# 4. Next actions

Immediate next action:

```text
Create Step 01 plan/tracker and initialize repo skeleton.
```

Step 01 should cover:

```text
- create base repo folders,
- create initial .gitignore,
- place the 000 global docs,
- create placeholder src/ package structure,
- create fixtures/, outputs/, experiments/, tests/, legacy/ folders,
- add .gitkeep files where needed,
- define minimal project run/test expectation.
```

---

# 5. Known open issues

These are not blockers for Step 01.

```text
- Exact geometry library choice is not yet fixed.
- Exact decomposition algorithm is not yet fixed.
- Exact growth scoring formula is not yet fixed.
- Exact multi-floor anchor behavior is deferred to Step 14.
```

These should not block project skeleton setup.

---

# 6. Step status table

Canonical Step definitions live in `000_Pipeline_Overview.md`. This table only tracks progress.

| Step | Status | Notes |
|---:|---|---|
| 01 | Ready | Project Skeleton / Global Docs |
| 02 | Not started | Core Schema / Run Config / Debug Output Contract |
| 03 | Not started | Visualization Renderer / Visual Vocabulary |
| 04 | Not started | Apartment Fixtures / Target Adapter |
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
5. Update this file when the Step starts, pauses, or finishes.
```
