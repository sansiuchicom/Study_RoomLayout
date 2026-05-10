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
Step 06 done 2026-05-09 (pending merge). Ready for Step 07 kickoff after
merge --no-ff to main.
```

Current Step:

```text
Step 06. Program & Domain Constraint Engine
```

Current Step status:

```text
Done 2026-05-09. 11 commits on `step06-program-constraint-engine`:
  §4.1   3f09cbe  archive + scaffold + step05 schema export cleanup
  §4.2   f241d58  ProgramRequest dataclass + Role + spaces strict + serialize Union fix
  §4.3   0da364b  TargetRules + apartment.json + adapter target check + package-data
  §4.3a  372090b  generic TargetAdapter (S06-D22) + 3-layer extensibility README
  cleanup be906b4  review followups (serialize docstring + Tracker drift + ApartmentAdapter 잔재)
  design  01e42d3  모델링 결함 8 항목 (D023 신설 + D020/D022 본문 + Pipeline §9.10 + rules_loader completeness)
  §4.4   8c1903d  DomainGateFailure 계층 + gates module
  §4.5   bb6a32a  Stage 01 본격화 (preservation + dup/unknown/type guards + D023)
  §4.6   c920c4e  Stage 02 wiring + R2 AreaGateFailure 회로 작동
  §4.7   bd27fa5  fail-loud sweep (RunConfig + threshold wiring + palette + render)
  §4.8   17c852f  notebook (17 cells / 6 visualizations / 4 PNG charts)
  §4.9    (this)  close (Plan/Tracker/Progress + D020/D021/D022/D023 finalize)
221 passed (82 baseline + 139 신규). D020/D021/D022/D023 Status: Accepted.
Plan v5 / Tracker close. R2 `verified_at: Step 06` 약속 실현 — first live
AreaGateFailure trigger.
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
006_Step06_ProgramConstraintEngine_Plan.md     (Completed; pending move to legacy/step06/ at Step 07 kickoff)
006_Step06_ProgramConstraintEngine_Tracker.md  (Completed; pending move to legacy/step06/ at Step 07 kickoff)
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
Confirm Step 06 close: git merge --no-ff step06-program-constraint-engine
into main, delete branch, push to origin. Then Step 07 kickoff
(Region/Atom Decomposition) per Pipeline §15. Step 07 entry items:
  - Plan Def-6  Stage 00 normalize 책임 확장 (review #4)
  - Plan Def-11 Hole-aware decompose / schema (review #1, ㅁ자/atrium)
  - Plan Def-12 viz.svg.render atoms/regions/spine 본격 렌더
  - Plan Def-13 references docstring (cell_v3_2 / zone_v12 외부 의존)
  - Plan Def-14 Decomposition 단위 일관성 (mm/m)
  - Step 05 §5 Def-13 v12 zoning port (broad except / gap merge 정리)
  - Step 06 §4.7 atoms render activation (D012)
```

Step 06 delivered (pending merge, 2026-05-09):

```text
- proto3.schema.program.{ProgramRequest, Role} (typed, slim)
- proto3.target.{TargetRules, TargetAdapter (single generic), DEFAULT_APARTMENT_RULES_PATH}
- proto3.target.rules_loader (JSON full validation incl. NaN/Inf + completeness)
- src/proto3/data/target_rules/apartment.json + README.md (3-layer model + mission scope)
- pyproject [tool.setuptools.package-data]: ship JSON + README in wheel/sdist
- proto3.constraints.gates (4 pure functions; 3 active in Stage 02 + access dormant)
- proto3.schema.validation.DomainGateFailure 계층 (Area / Dim / AccessSchema)
- proto3.stages.stage01_program 본격화 (모든 필드 보존 + dup/unknown/type guards + D023 required-only)
- proto3.stages.stage02_gate 신규 (D020 fail-only, D024 boundary 명시)
- proto3.config.RunConfig.__post_init__ value validation (S06-D14)
- atom_inclusion_threshold dead config wiring (recursive.py + decompose.{auto_partition,run})
- proto3.viz.{palette, svg.render} fail-loud (S06-D11, atoms/regions/spine strict)
- D-decisions: D020 / D021 / D022 / D023 (Accepted 2026-05-09)
- 221 pytest passed (82 baseline + 139 신규)
- notebooks/step06_program_gate_overview.ipynb (17 cells, 4 PNG charts)
- 11 commits on step06-program-constraint-engine; merge --no-ff 사용자 확인 대기
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
| 06 | Done | Program & Domain Constraint Engine (2026-05-09; pending merge of `step06-program-constraint-engine` — 11 commits, 221 passed; D020/D021/D022/D023 Accepted; R2 `verified_at: Step 06` 실현) |
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
