# 006 Step 06 — Program & Domain Constraint Engine Tracker

Status: In progress
Started: 2026-05-09
Branch: `step06-program-constraint-engine`
Companion plan: [006_Step06_ProgramConstraintEngine_Plan.md](006_Step06_ProgramConstraintEngine_Plan.md)

---

## 0. Purpose

이 문서는 **진행 로그 / 체크리스트**. [Plan](006_Step06_ProgramConstraintEngine_Plan.md)과 1:1 매칭, 작업하면서 수시로 갱신.

| | Plan | Tracker |
|---|---|---|
| 무엇 | 결정·사양 | 진행 상태·로그·이슈 |
| 갱신 | 의논 중에는 자주, 결정 후 동결 | 작업하며 수시 |

---

## 1. 작업 체크리스트

[Plan §4](006_Step06_ProgramConstraintEngine_Plan.md)의 항목과 **동일한 번호**. 각 항목은 commit 1개와 매칭.

| # | 작업 | commit msg | 상태 | 완료일 |
|---|---|---|:---:|---|
| 4.1 | Step 05 archive + scaffold step06 module + step05 schema export cleanup | `chore: archive step05 + scaffold step06 module + step05 schema export cleanup` | [ ] | |
| 4.2 | ProgramRequest dataclass + Role literal + spaces strict deserialize | `feat: ProgramRequest dataclass + Role literal + spaces strict deserialize (S06-D8, D10)` | [ ] | |
| 4.3 | TargetRules + apartment.json data package + adapter target check | `feat: TargetRules + apartment.json data package + adapter target check (S06-D4, D5, D9, D15, D17)` | [ ] | |
| 4.4 | DomainGateFailure hierarchy + gates module | `feat: DomainGateFailure hierarchy + gates module (S06-D6, D12, D13)` | [ ] | |
| 4.5 | Stage 01 full program preservation + dup/unknown/type guards | `feat: stage 01 full program preservation + dup/unknown/type guards (S06-D7, D10)` | [ ] | |
| 4.6 | Stage 02 gate + Pipeline §9.10 update + R2 regression | `feat: stage 02 gate + Pipeline §9.10 update + R2 regression (S06-D6, review #2, #7)` | [ ] | |
| 4.7 | Fail-loud sweep — RunConfig + threshold wiring + palette + render strict | `feat: fail-loud sweep — RunConfig + threshold wiring + palette + render strict (S06-D11, D14, review #3, #11, #12)` | [ ] | |
| 4.8 | step06 program gate overview notebook | `feat: step06 program gate overview notebook (S06-D16)` | [ ] | |
| 4.9 | Step 06 cleanup (Plan/Tracker, Progress Tracker, D020/D021) | `docs: step06 cleanup (Plan/Tracker, Progress Tracker, D020/D021)` | [ ] | |

실행 순서: 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 → 4.7 → 4.8 → 4.9 → (Step 종료) merge --no-ff to main.

---

## 2. DoD 검증 결과

[Plan §1](006_Step06_ProgramConstraintEngine_Plan.md)의 DoD-1 ~ DoD-28.

| # | 조건 | 결과 | 검증 시각 |
|---|---|:---:|---|
| DoD-1 | ProgramRequest dataclass + BuildingInput 타입 변경 + 잘못된 spaces type ValueError | [ ] | |
| DoD-2 | Role Literal + SpaceUnitSpec.role 좁힘 + 미지값 fail | [ ] | |
| DoD-3 | TargetRules dataclass — 모든 필드 required | [ ] | |
| DoD-4 | data/target_rules/apartment.json + README + namespace package | [ ] | |
| DoD-5 | pyproject.toml package-data 추가 + wheel 포함 검증 | [ ] | |
| DoD-6 | rules_loader 검증 layer (필드/타입/role/범위) | [ ] | |
| DoD-7 | ApartmentAdapter(rules_path) required + DEFAULT_APARTMENT_RULES_PATH 상수 | [ ] | |
| DoD-8 | ApartmentAdapter.load_fixture target_type 검사 | [ ] | |
| DoD-9 | stage00_load adapter=None 분기에서 DEFAULT_APARTMENT_RULES_PATH 사용 | [ ] | |
| DoD-10 | constraints.gates 4 pure functions | [ ] | |
| DoD-11 | DomainGateFailure 부모 + 3 자식 | [ ] | |
| DoD-12 | stage02_gate.run gates 호출 + raise | [ ] | |
| DoD-13 | Stage 01 모든 SpaceUnitSpec 필드 보존 + dup/unknown/type 가드 | [ ] | |
| DoD-14 | RunConfig.__post_init__ value validation | [ ] | |
| DoD-15 | decompose.run() threshold 인자 + recursive.py 0.5 hardcoded 제거 | [ ] | |
| DoD-16 | viz.palette 미지 role ValueError | [ ] | |
| DoD-17 | viz.svg.render 미지원 kwarg ValueError | [ ] | |
| DoD-18 | R2 → AreaGateFailure 회로 작동 | [ ] | |
| DoD-19 | A1/A2/B1/D1 Stage 02 통과 (false-reject 없음) | [ ] | |
| DoD-20 | step06_program_gate_overview notebook | [ ] | |
| DoD-21 | pytest 통과 (현재 82 + 신규) | [ ] | |
| DoD-22 | python -m pip install -e . 회귀 없음 | [ ] | |
| DoD-23 | Pipeline §9.10 Stage 02 outputs 갱신 | [ ] | |
| DoD-24 | schema.__init__ +GeometricPiece +Decomposition + test_smoke 22→24 | [ ] | |
| DoD-25 | Step 05 docs legacy/step05/ + Plan header `(merged 7064132)` 갱신 | [ ] | |
| DoD-26 | Progress Tracker 4.1 In progress + stale §4 + Last updated 갱신 | [ ] | |
| DoD-27 | §4 commits all on step06 branch + merge --no-ff + branch 삭제 | [ ] | |
| DoD-28 | Architecture Decisions D020 + D021 추가 + D006 cross-link | [ ] | |

---

## 3. 진행 로그 (시간순)

| 시각 | 이벤트 |
|---|---|
| 2026-05-09 | Step 05 close (`7064132`) 후 main 동기화. `step06-program-constraint-engine` 브랜치 checkout. Step 06 결정 토론 진행 (scope 정상, density 0.85, role hard fail, min_area 중간안, 외부 JSON config 패턴, ApartmentAdapter rules_path required, 4-layer rules 분리) |
| 2026-05-09 | Plan v1 draft 작성 (16 decisions) |
| 2026-05-09 | 외부 review (다른 Claude 인스턴스) 16 항목 받음. High 6 + Medium 6 + Docs/Workflow 4. Plan v2 갱신 — packaging `src/proto3/data/`로 이동, Stage 01 본격화 (모든 필드 보존), atom_inclusion_threshold wiring, viz/render fail-loud, adapter mismatch 검사, Pipeline §9.10 갱신, schema __init__ 잔여, hole-aware decompose Def-11, references docstring Def-13. 18 decisions / 9 work items / 28 DoD / 13 deferred / 11 risks |

---

## 4. 이슈 / 계획 변경

(아직 없음)

---

## 5. Step-close cleanup checklist (D016 amendment)

Step 종료 시 순서대로:

- [ ] Plan §4 모든 항목 [x] 확인
- [ ] DoD §2 모든 항목 [x] 확인
- [ ] `git status` clean 확인
- [ ] `000_Progress_Tracker.md` 갱신: Current step → "Step 06 complete (pending merge)", Active files → Step 06 docs as "Completed; pending move to legacy/step06/ at Step 07 kickoff", Step status table → Step 06 Done
- [ ] (D016 amendment) Step 06 docs는 **Step 07 kickoff 시** `legacy/step06/`로 이동 — 이 Step에서는 옮기지 않음
- [ ] git commit (4.9 = TBD)
- [ ] `git checkout main && git merge --no-ff step06-program-constraint-engine && git branch -d step06-program-constraint-engine && git push origin main`

---

## 6. 변경이력

| Date | Change |
|---|---|
| 2026-05-09 | Initial. 9 work items, 28 DoD. v2 (외부 review 16 항목 반영) 기준. |
