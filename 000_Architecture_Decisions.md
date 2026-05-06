# 000 Architecture Decisions

Status: Canonical decision record  
Scope: accepted proto3 architecture decisions, invariant vs replaceable choices, and decision history appendix  
Last updated: 2026-05-02

---

## 0. Purpose

This document records accepted decisions for proto3.

Use this file to answer:

- What has already been decided?
- What is an architecture invariant?
- What is only a first-pass implementation choice?
- Why was the decision made?
- What should be changed only with deliberate review?

Canonical framework and pipeline definitions live in `000_Pipeline_Overview.md`. Current implementation status lives in `000_Progress_Tracker.md`.

---

# 1. Decision status labels

| Status | Meaning |
|---|---|
| **Accepted** | Current working decision. Use unless explicitly revised. |
| **Replaceable** | Current first-pass choice, but not a framework invariant. |
| **Deferred** | Known issue or future decision, not required immediately. |
| **Rejected** | Decision considered and intentionally not used. |

---

# 2. Architecture invariants vs replaceable choices

This distinction matters.

Architecture invariants define proto3 itself. Replaceable choices are initial implementation defaults.

| Category | Examples |
|---|---|
| Architecture invariant | spine-first search schema, region/atom dual layer, floor-rooted access, domain constraints as gates, failure-to-pruning backtracking |
| Replaceable implementation choice | greedy multi-source growth, specific atom size defaults, reflex-cut decomposition first pass, SVG implementation library |

Changing an invariant changes the framework. Changing a replaceable choice should not require rewriting the framework.

---

# 3. Accepted decisions

## D001. Use separate Step, Stage, Search Orchestrator, Cross-cutting Infrastructure, and Target concepts

Status: Accepted  
Type: Architecture invariant

Definitions:

| Term | Meaning |
|---|---|
| Step | Development roadmap unit. |
| Stage | Runtime candidate pipeline unit. |
| Search Orchestrator | Control loop outside the Stage pipeline. |
| Cross-cutting Infrastructure | Shared systems such as provenance, visualization, debug output, no-good store. |
| Target | Typology/domain adapter. |

Decision:

- Step and Stage must not be treated as the same thing.
- Candidate Search is not a Stage.
- Provenance, visualization, debug output, run config, and no-good records are cross-cutting infrastructure.

Reason:

The old model blurred implementation order, runtime pipeline, and search orchestration. This made it unclear whether candidate search was a Stage or a system-level loop. The current distinction keeps the architecture implementable.

---

## D002. Use 000 global docs and 001–014 Step docs

Status: Accepted  
Type: Documentation / repo convention

Decision:

- `000_*` files are global docs.
- Step 00 does not exist.
- Implementation Step files use prefixes `001` through `014`.
- Step number in prose uses two digits, e.g. Step 05.
- File prefix uses three digits, e.g. `005_Step05_GeometryKernel_Plan.md`.

Root global docs:

```text
000_Pipeline_Overview.md
000_Architecture_Decisions.md
000_Progress_Tracker.md
000_User_Profile.md
```

Step-specific files are created only when actively working on that Step and may move to `legacy/stepXX/` after completion.

Reason:

The previous `010`, `020`, `140` style required mental mapping between file prefix and Step number. Direct `001`–`014` naming is simpler.

---

## D003. Use apartment-first implementation, but floor-rooted architecture

Status: Accepted  
Type: Architecture invariant

Decision:

- The first Target is Apartment Unit.
- Core architecture must remain floor-rooted, not apartment-core.
- Core schema must support `BuildingInput`, `FloorInput`, floor roots, and empty persistent anchor fields from the beginning.

Reason:

Apartment layouts are the best first implementation target, but the framework should later support multi-floor houses, hotel floors, warehouses, and offices without rewriting core types.

---

## D004. Treat ProgramInstance as the source of cardinality

Status: Accepted  
Type: Architecture invariant

Decision:

- `ProgramInstance` decides required space counts.
- `ClusterSpec` groups already-instantiated spaces.
- Cluster does not create or guarantee cardinality.

Reason:

Relying on clusters or usage fallback can recreate failures such as required bathrooms disappearing. Cardinality must be explicit before clustering, spine generation, seed placement, or growth.

Regression rule:

> A required apartment bathroom count of zero is a ProgramInstantiationFailure, not a growth failure.

---

## D005. Domain constraints are gates, not role scores

Status: Accepted  
Type: Architecture invariant

Decision:

- Domain constraints must be first-class gates and validations.
- Role scoring is preference only.

Hard domain gates include:

- required cardinality,
- minimum area,
- minimum dimension,
- required access validity,
- required door-capable boundary,
- no overlaps,
- inside footprint,
- persistent anchors preserved.

Soft domain constraints include:

- preferred area ratio,
- preferred aspect ratio,
- exterior contact preference,
- wet/service proximity,
- compactness / rectangularity.

Reason:

The previous BSP/R1 failures were not caused by weak vocabulary alone. They came from domain rules not being enforced as first-class constraints.

---

## D006. Use a region/atom dual layer

Status: Accepted  
Type: Architecture invariant

Decision:

- Region is the coarse architectural territory layer.
- Atom is the fine geometric growth layer.
- Both are required.

Reason:

Region-only is too rigid. Atom-only lacks architectural meaning and can turn the problem into unstructured pixel growth. The dual layer separates intent from growth mechanics.

Initial atom defaults are first-pass commitments, not universal laws:

| Item | Initial default |
|---|---:|
| Internal coordinate unit | millimeter |
| Default layout atom size | 600mm nominal side |
| Minimum atom side | 300mm |
| Tiny atom area threshold | 0.18㎡ |
| Door-capable shared boundary | 800mm minimum |
| Preferred door boundary | 900mm or more |

Step 05 Geometry Kernel must confirm or revise these defaults before serious decomposition and growth work.

---

## D007. Use floor-rooted spine-first candidate search

Status: Accepted  
Type: Architecture invariant

Decision:

The core search schema is spine-first:

```text
floor root
→ hub
→ trunk / branch / stub spine
→ branch slots
→ seeds
→ atom growth
```

The system should form access/spine hypotheses before growing rooms.

Reason:

Previous approaches pushed too many decisions into growth. The spine-first schema gives access, clustering, and attachment structure before atom assignment.

Important:

The spine is not necessarily a corridor. It may become hall, living access host, explicit corridor, stair landing, warehouse aisle, hotel corridor, or another Target-specific access carrier.

---

## D008. Candidate Search is not Stage 14

Status: Accepted  
Type: Architecture invariant

Decision:

Candidate Search is the Search Orchestrator around Stage 00–13.

It is responsible for:

- candidate pool,
- retry ladder,
- no-good records,
- search budget,
- penalties,
- deciding where to resume.

Reason:

A Stage transforms one candidate. Candidate Search manages many candidates and repeated execution of the Stage pipeline. Treating it as a Stage makes the model ambiguous.

Canonical sentence:

> Candidate Search is not a pipeline Stage. It is the control loop that repeatedly runs Stage 00–13, updates no-good records, and decides which earlier Stage to revisit.

---

## D009. Use pre-repair and post-repair validation

Status: Accepted  
Type: Architecture invariant

Decision:

The final runtime pipeline uses:

```text
Stage 10 Atom Growth
→ Stage 11 Pre-repair Validation / Defect Detection
→ Stage 12 Repair / Rectangularization
→ Stage 13 Post-repair Validation / Failure Diagnosis / Output Assembly
```

Reason:

Repair should be defect-directed. If validation only happens after repair, it becomes unclear what repair was supposed to fix and whether repair introduced new failures.

Required distinction:

- Pre-repair validation identifies defects and repairability.
- Repair modifies geometry using a defect report.
- Post-repair validation checks whether the candidate is valid and whether repair caused regressions.

Stage 13 must assemble both valid and invalid candidate outputs. Invalid outputs must still include FailureRecords, provenance, and debug artifacts.

---

## D010. Use failure-to-pruning backtracking

Status: Accepted  
Type: Architecture invariant

Decision:

Failure-directed retry must update future search.

Every meaningful failure should produce at least one of:

- rejected candidate,
- rejected pattern,
- soft penalty,
- required invariant update,
- retry-level escalation,
- no-good record.

Reason:

Retry labels such as “seed retry or spine retry” are too vague. A failure becomes useful only when evidence identifies what should be avoided or protected next.

---

## D011. Use access-preserving atom growth as the invariant

Status: Accepted  
Type: Architecture invariant with replaceable first-pass algorithm

Decision:

The framework requires **access-preserving atom growth**, not greedy growth specifically.

Growth must:

- assign atoms to SpaceUnits,
- preserve required access/parent boundary conditions,
- respect hard domain constraints,
- preserve provenance of growth decisions,
- produce validation evidence.

First-pass implementation choice:

> Use greedy multi-source priority growth initially.

Status of greedy growth:

- Replaceable.
- Suitable for first implementation and debugging.
- Not a framework invariant.

Possible replacements:

- beam search growth,
- staged growth by priority,
- min-cost assignment + repair,
- hybrid methods.

---

## D012. Start with dataclasses for schema

Status: Accepted  
Type: Replaceable implementation choice

Decision:

Start with Python dataclasses, type hints, and explicit serialization helpers.

Do not start with pydantic unless validation or JSON schema needs become painful.

Minimum schema stubs should include:

```text
BuildingInput
FloorInput
RunConfig
PersistentAnchor
ProgramInstance
SpaceUnitSpec
ClusterSpec
AccessPolicy
Region
RegionSet
Atom
AtomSet
ContactGraph
HubCandidate
TerminalCandidate
SpineCandidate
SlotCandidate
SeedCandidate
GrowthResult
LayoutCandidate
ValidationResult
FailureRecord
NoGoodRecord
DebugArtifact
```

Reason:

The data model needs shape immediately. Deferring this as “dataclass vs pydantic” would let later Steps define incompatible fields.

---

## D013. Use SVG-first visualization

Status: Accepted  
Type: Replaceable implementation choice

Decision:

Use an SVG-first renderer for debug visualization.

Reason:

Layout debugging needs polygon overlays, stable layer order, readable labels, and browser-friendly outputs. SVG is a better default than ad-hoc plots for this use case.

Initial visual requirements:

- one shared renderer,
- stable layer order,
- stable visual vocabulary,
- each major Stage can emit SVG overlays.

Initial layer order:

1. footprint boundary,
2. persistent anchors,
3. regions,
4. atoms,
5. graph edges,
6. role scores / heatmap,
7. spine / access tree,
8. slots,
9. seeds / patches,
10. grown spaces,
11. door candidates,
12. validation / failure overlay.

---

## D014. Keep debug outputs out of version control by default

Status: Accepted  
Type: Repo convention

Decision:

Generated debug outputs should not be committed by default.

Initial `.gitignore` policy:

```gitignore
__pycache__/
*.pyc
.venv/
.env

outputs/debug_runs/*
!outputs/debug_runs/.gitkeep

experiments/runs/*
!experiments/runs/.gitkeep

.cache/
.pytest_cache/
.mypy_cache/
.ruff_cache/

.DS_Store
```

Reason:

proto3 will generate many JSON/SVG debug artifacts. Keeping them tracked by default would quickly pollute the repo.

---

## D015. Per-Step branch + per-work-item commit + no-squash merge

Status: Accepted
Type: Repo / VCS convention

Decision:

For Step-level (or larger Stage-level) work:

- **Start**: checkout a new branch (e.g., `step02-core-schema`).
- **During**: commit each completed work item separately. Plan §4 work-item granularity defines commit granularity by default. Design commit boundaries during Plan-time, not after.
- **Judgment exception**: very simple/small work may stay on `main` directly.
- **Finish**: merge with `git merge --no-ff` (no squash). Then delete the branch (`git branch -d <branch>`).
- **Commit message**: prefix-style 1~2 lines, e.g. `git commit -m "feat: 제목, 간단한 내용"`. Common prefixes: `feat`, `fix`, `refactor`, `docs`, `chore`.

Reason:

- Squash discards per-commit history. Failure-to-pruning ([D010](000_Architecture_Decisions.md)) and provenance ([Pipeline Overview §12.1](000_Pipeline_Overview.md)) work better when each commit corresponds to a Plan §4 work item — diagnosing "when did this break" is easier with per-commit history aligned to plan items.
- Per-Step branch makes work-in-progress visible without cluttering main, while merge --no-ff preserves the Step's commit cluster as a reviewable unit.
- The Plan §4 ↔ commit mapping makes automated execution and code review easier.

Step 01 was an exception: this convention was decided mid-Step-01, so Step 01 was bundled into a single `feat: step01 project skeleton` commit on `main` (see Step 01 Plan / Tracker for details). Step 02 onward applies D015 from the start.

---

## D016. Per-Step companion docs: Plan + Tracker

Status: Accepted
Type: Documentation / repo convention

Decision:

Each implementation Step has two companion documents at the repo root:

- **`NNN_StepNN_<name>_Plan.md`** — living decision doc + work specification. Updated during discussion, frozen once decided. Detailed enough that an automated executor can run from it without consulting other files.
- **`NNN_StepNN_<name>_Tracker.md`** — progress log + checklist. Updated continuously while working.

Plan section structure (followed by Step 01):

- §0 Purpose (with cross-references)
- §1 Definition of Done (with verification commands)
- §2 결정 기록 (decision table; per-Step decision IDs prefixed with the step, e.g. `S01-D1`)
- §3 Directory structure (target state)
- §4 Work items (each with command + verification)
- §5 의도적으로 하지 않는 것 (explicit non-goals with "유예" reasoning)
- §6 Risks
- §7 Next-Step linkage
- (optional) §A Appendix — inline file contents for automation. **Single-use scaffolding**: stripped during Step-close cleanup. The first Step (Step 01) keeps it heavy while workflow is being established; later Steps may skip it from the start.

Tracker mirrors Plan §4 numbering 1:1 in its §1 checklist; automation depends on this.

Step-close cleanup sequence (at the **closing** Step's final commit):

1. Verify all Plan §4 items checked.
2. Verify all DoD items checked.
3. `git status` clean.
4. Update `000_Progress_Tracker.md` (current step status, active files, step status table).
5. Strip Plan §A.
6. git commit per [D015](000_Architecture_Decisions.md), then `git merge --no-ff` to main and delete branch.

Then at the **next** Step's kickoff §4.1 commit:

7. `git mv` previous Step files to `legacy/stepNN/` ([Pipeline Overview §16](000_Pipeline_Overview.md)) together with the next Step's module scaffold.

Reason:

- Separates *decisions* (Plan, slow-changing, frozen on completion) from *progress* (Tracker, fast-changing, archived on completion). Mixing them makes both worse.
- Plan §4 ↔ Tracker §1 numbering preserves traceability and enables automated execution.
- Single-use Appendix avoids the "huge inline scaffolding lives forever in the repo" failure mode.
- **Deferred archive (step 7)**: moving Plan/Tracker mid-cleanup creates a self-reference paradox — the cleanup checklist itself ends up under `legacy/`, and the closing Tracker would have to mark its own archival as "done" before the move. By archiving at the *next* Step's kickoff §4.1, the previous Step's docs stay accessible at repo root through the close, and the new Step's first commit naturally bundles "archive previous + scaffold current". Pattern validated across Step 01 → 02 → 03.

---

# 4. Deferred decisions

These are intentionally not fully settled yet.

## Q001. Exact decomposition algorithm

Current direction:

```text
manual/semi-manual fixtures
→ reflex vertex extension
→ rectangle scoring helper
```

Deferred:

- when to add maximal rectangle search,
- whether to add medial-axis/skeleton hints,
- whether atom-first clustering is useful.

## Q002. Exact growth replacement path

Current first-pass:

```text
greedy multi-source priority growth
```

Deferred:

- beam growth,
- min-cost assignment + repair,
- hybrid approaches.

## Q003. Multi-floor orchestration details

Current decision:

- schema supports anchors early,
- Stage 03 is a no-op for apartment-first,
- Step 14 implements non-trivial persistent anchors and floor orchestration.

Deferred:

- floor allocation grammar,
- stair/core placement search,
- cross-floor wet stack scoring,
- multi-floor validation metrics.

---

# 5. Decision history appendix

This appendix is a chronological log of major changes. It is not a separate source of truth.

## H001. Narrowed the claim

The framing was narrowed from “innovative framework” to:

> spine-first + region/atom dual layer + failure-directed backtracking schema.

Reason: this is more honest, testable, and implementable.

## H002. Promoted region decomposition and atom growth from implementation details to core algorithm choices

Region decomposition and atom growth are not downstream details. They shape what the system can perceive and produce.

## H003. Added Program & Domain Constraint Layer

Cardinality, area, aspect ratio, min dimension, access policy, and required door boundary became first-class gates/validations.

## H004. Reframed failure-directed retry as failure-to-pruning

Retry is not useful unless a failure updates the search space through a reject, penalty, invariant, escalation, or no-good record.

## H005. Changed final framework reference from v1 roadmap to canonical framework

Implementation sequencing was separated from the final architecture reference.

## H006. Reorganized docs into three global files

Global docs are:

```text
000_Pipeline_Overview.md
000_Architecture_Decisions.md
000_Progress_Tracker.md
```

`000_User_Profile.md` is maintained separately by the user.

## H007. Removed Step 00 and adopted 001–014 implementation Steps

`000_*` is reserved for global docs. Actual implementation Steps start at Step 01.

## H008. Separated Candidate Search from Stage pipeline

Candidate Search became Search Orchestrator, not Stage 14.

## H009. Split validation into pre-repair and post-repair

Repair now consumes a defect report and is validated afterward.

## H010. Codified Step-level documentation and VCS workflow during Step 01

Step 01 set up the project skeleton. During execution, two workflow patterns emerged from collaboration and were promoted to accepted decisions:

- D016 (Per-Step Plan + Tracker companion docs) — decision/progress separation, Plan §A as single-use scaffolding, Step-close cleanup sequence.
- D015 (Per-Step branch + per-work-item commit + no-squash merge) — Step 01 itself was bundled into one `main` commit as an exception, since the convention was decided mid-Step-01.

These patterns proved their value during Step 01 and would otherwise live only in session memory, invisible to anyone reading the global docs. Promoted to D015/D016 to make them auditable and durable.

## H011. Deferred Plan/Tracker archive to next-Step kickoff (D016 amendment)

Original D016 step 6 said "Move both Step files to `legacy/stepNN/`" as part of Step-close cleanup. In practice, doing the `git mv` mid-cleanup creates a self-reference paradox: the cleanup checklist itself ends up under `legacy/`, and the closing Tracker would have to mark its own archival before the move. Across Step 01, 02, 03 the actual practice was to defer the move to the next Step's §4.1 kickoff commit, where it bundles cleanly with "scaffold next-Step modules". The user codified this deferral on 2026-05-03.

D016 wording was amended on 2026-05-06 (Step 03 review followups #4) to reflect the actual practice: cleanup steps 1–6 happen at Step-close; archive (step 7) happens at the *next* Step's kickoff §4.1. Documented after a reviewer flagged the inconsistency between D016 text and Progress Tracker statements.

---

# 6. Summary

Architecture invariants:

```text
- Step / Stage / Search Orchestrator / Cross-cutting Infrastructure / Target separation
- apartment-first but floor-rooted architecture
- ProgramInstance owns cardinality
- domain constraints are gates, not role scores
- region/atom dual layer
- floor-rooted spine-first candidate search
- Candidate Search is not a Stage
- pre-repair and post-repair validation
- failure-to-pruning backtracking
- access-preserving atom growth
```

Replaceable first-pass choices:

```text
- greedy multi-source priority growth
- SVG-first renderer implementation details
- dataclass-first schema
- initial atom resolution defaults
- reflex-cut decomposition first pass
```
