# 000 Progress Tracker

Status: Current working status only  
Scope: active Step, active files, completed work, next actions, blockers  
Last updated: 2026-05-11

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
Step 06 done 2026-05-09, merged to main 2026-05-10 (`5e6de90`). Ready for
Step 07 kickoff (Region/Atom Decomposition) — awaiting external research
before locking Plan §4 work-items.
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
AreaGateFailure trigger. Merged to main 2026-05-10 (`5e6de90`) with 2
additional merge-prep commits (`856c5a9`, `6f6db5c`) — 260 passed post-merge.
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
Step 07 kickoff (Region/Atom Decomposition) per Pipeline §15 — awaiting
external research before locking Plan §4 work-items. Pre-kickoff post-merge
cleanup landed 2026-05-11 (this file's Last-updated bump): pending-merge
text removed, D006 D019-supersede note, Stage 01 default-fill ValueError
wrap, auto_partition holes docstring, references/ reference-only docstring,
.gitignore ipynb_checkpoints, README D22 single-floor boundary.

Step 07 entry items (carried forward, to land in Step 07 Plan §1 DoD / §4):
  - Plan Def-6  Stage 00 normalize 책임 확장 (review #4)
  - Plan Def-11 Hole-aware decompose / schema (review #1, ㅁ자/atrium)
  - Plan Def-12 viz.svg.render atoms/regions/spine 본격 렌더
  - Plan Def-13 references docstring (cell_v3_2 / zone_v12 외부 의존)
  - Plan Def-14 Decomposition 단위 일관성 (mm/m) — Region/Atom vertices/center
    + PersistentAnchor.geometry 단위 명시도 함께
  - Step 05 §5 Def-13 v12 zoning port (broad except / gap merge 정리)
  - Step 06 §4.7 atoms render activation (D012)
```

Step 06 delivered (merged 2026-05-10 `5e6de90`):

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

Cross-cutting / deferred items that span multiple Steps. Step-specific deferred items live in each Step Plan's §5.

```text
- Geometry library: shapely + numpy (Step 05 D019).
- Decomposition algorithm: v3.2 per-family proportional + 50% rule (Step 05 D019); RegionSet/AtomSet 통합은 Step 07.
- Hole-aware decompose: footprint exterior 만 처리 — ㅁ자/atrium 진입 시 Step 07 entry blocker (Step 06 Plan Def-11).
- Decomposition 단위 일관성 (mm↔m): Step 07 Stage 00 normalize 책임 확장과 묶음 (Step 06 Plan Def-14).
- Growth scoring formula: Step 11.
- Multi-floor anchor 본격: Step 14 (Stage 02 단정으로 차단 중).
- 외부 파이프라인 override layer (부분 override merge / RunConfig.target_rules_override 채널 / override 값 검증): 외부 scan-to-BIM 파이프라인 통합 시점 (Step 06 Plan Def-1).
- L2 strategy plugin registry (typology-specific spine / program-expand 변형): Step 09 first apartment strategy 진입 시 (Step 06 D022).
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
| 06 | Done | Program & Domain Constraint Engine (2026-05-09; merged 2026-05-10 `5e6de90` — 11 commits + 2 merge-prep, 260 passed; D020/D021/D022/D023 Accepted; R2 `verified_at: Step 06` 실현) |
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
