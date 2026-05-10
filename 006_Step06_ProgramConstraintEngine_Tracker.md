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
| 4.1 | Step 05 archive + scaffold step06 module + step05 schema export cleanup | `chore: archive step05 + scaffold step06 module + step05 schema export cleanup` | [x] | 2026-05-09 (`3f09cbe`) |
| 4.2 | ProgramRequest dataclass + Role literal + spaces strict deserialize | `feat: ProgramRequest dataclass + Role literal + spaces strict deserialize (S06-D8, D10)` | [x] | 2026-05-09 (`f241d58`) |
| 4.3 | TargetRules + apartment.json data package + adapter target check | `feat: TargetRules + apartment.json data package + adapter target check (S06-D4, D5, D9, D15, D17)` | [x] | 2026-05-09 (`0da364b`) |
| 4.3a | Generic TargetAdapter reform (S06-D22) | `refactor: generic TargetAdapter + JSON self-describing typology + 3-layer extensibility (S06-D5, D17, D22 + .gitignore build/dist)` | [x] | 2026-05-09 (`372090b`) |
| 4.4 | DomainGateFailure hierarchy + gates module | `feat: DomainGateFailure hierarchy + gates module (S06-D6, D12, D13, D023, D024)` | [x] | 2026-05-09 (`8c1903d`) |
| 4.5 | Stage 01 full program preservation + dup/unknown/type guards | `feat: stage 01 full program preservation + dup/unknown/type guards (S06-D7, D10, D023)` | [x] | 2026-05-09 (`bb6a32a`) |
| 4.6 | Stage 02 gate + Pipeline §9.10 update + R2 regression | `feat: stage 02 gate + R2 AreaGateFailure regression (S06-D6, D24, review #2)` | [x] | 2026-05-09 |
| 4.7 | Fail-loud sweep — RunConfig + threshold wiring + palette + render strict | `feat: fail-loud sweep — RunConfig + threshold wiring + palette + render strict (S06-D11, D14, review #3, #11, #12)` | [x] | 2026-05-09 |
| 4.8 | step06 program gate overview notebook | `feat: step06 program gate overview notebook (S06-D16)` | [x] | 2026-05-09 |
| 4.9 | Step 06 cleanup (Plan/Tracker, Progress Tracker, D020/D021) | `docs: step06 cleanup (Plan/Tracker, Progress Tracker, D020/D021)` | [ ] | |

실행 순서: 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 → 4.7 → 4.8 → 4.9 → (Step 종료) merge --no-ff to main.

---

## 2. DoD 검증 결과

[Plan §1](006_Step06_ProgramConstraintEngine_Plan.md)의 DoD-1 ~ DoD-28.

| # | 조건 | 결과 | 검증 시각 |
|---|---|:---:|---|
| DoD-1 | ProgramRequest dataclass + BuildingInput 타입 변경 + 잘못된 spaces type ValueError | [x] | 2026-05-09 (§4.2) |
| DoD-2 | Role Literal + SpaceUnitSpec.role 좁힘 + 미지값 fail | [x] | 2026-05-09 (§4.2) |
| DoD-3 | TargetRules dataclass — 모든 필드 required | [x] | 2026-05-09 (§4.3) |
| DoD-4 | data/target_rules/apartment.json + README + namespace package | [x] | 2026-05-09 (§4.3 + §4.3a 강화) |
| DoD-5 | pyproject.toml package-data 추가 + wheel 포함 검증 | [x] | 2026-05-09 (§4.3) |
| DoD-6 | rules_loader 검증 layer (필드/타입/role/범위) | [x] | 2026-05-09 (§4.3, +target_type §4.3a) |
| DoD-7 | TargetAdapter(rules_path) required + DEFAULT_APARTMENT_RULES_PATH 상수 (§4.3a generic) | [x] | 2026-05-09 (§4.3 + §4.3a) |
| DoD-8 | TargetAdapter.load_fixture target_type 검사 | [x] | 2026-05-09 (§4.3 + §4.3a) |
| DoD-9 | stage00_load._DEFAULT_ADAPTERS uses DEFAULT_APARTMENT_RULES_PATH | [x] | 2026-05-09 (§4.3 + §4.3a) |
| DoD-10 | constraints.gates 4 pure functions | [x] | 2026-05-09 (§4.4) |
| DoD-11 | DomainGateFailure 부모 + 3 자식 | [x] | 2026-05-09 (§4.4) |
| DoD-12 | stage02_gate.run gates 호출 + raise | [x] | 2026-05-09 (§4.6) |
| DoD-13 | Stage 01 모든 SpaceUnitSpec 필드 보존 + dup/unknown/type 가드 | [x] | 2026-05-09 (§4.5) |
| DoD-14 | RunConfig.__post_init__ value validation | [x] | 2026-05-09 (§4.7) |
| DoD-15 | decompose.run() threshold 인자 + recursive.py 0.5 hardcoded 제거 | [x] | 2026-05-09 (§4.7) |
| DoD-16 | viz.palette 미지 role ValueError | [x] | 2026-05-09 (§4.7) |
| DoD-17 | viz.svg.render 미지원 kwarg ValueError | [x] | 2026-05-09 (§4.7, atoms/regions/spine 만; 나머지 silent) |
| DoD-18 | R2 → AreaGateFailure 회로 작동 | [x] | 2026-05-09 (§4.6) |
| DoD-19 | A1/A2/B1/D1 Stage 02 통과 (false-reject 없음) | [x] | 2026-05-09 (§4.6) |
| DoD-20 | step06_program_gate_overview notebook | [x] | 2026-05-09 (§4.8, 17 cells / 6 visualizations / 4 PNG charts) |
| DoD-21 | pytest 통과 (현재 82 + 신규) | [ ] | |
| DoD-22 | python -m pip install -e . 회귀 없음 | [ ] | |
| DoD-23 | Pipeline §9.10 Stage 02 outputs 갱신 | [x] | 2026-05-09 (`01e42d3` design commit) |
| DoD-24 | schema.__init__ +GeometricPiece +Decomposition + test_smoke 22→24 (§4.2 에서 25) | [x] | 2026-05-09 (§4.1 + §4.2) |
| DoD-25 | Step 05 docs legacy/step05/ + Plan header `(merged 7064132)` 갱신 | [x] | 2026-05-09 (§4.1) |
| DoD-26 | Progress Tracker 4.1 In progress + stale §4 + Last updated 갱신 | [x] | 2026-05-09 (§4.1) |
| DoD-27 | §4 commits all on step06 branch + merge --no-ff + branch 삭제 | [ ] | 진행 중 (4.1~4.3a land; 4.4~4.9 남음) |
| DoD-28 | Architecture Decisions D020 + D021 추가 + D006 cross-link (§4.9 close 시 finalize) | [~] | placeholder land (`3f09cbe` D020/D021, `372090b` D022); 본문 finalize §4.9 |

---

## 3. 진행 로그 (시간순)

| 시각 | 이벤트 |
|---|---|
| 2026-05-09 | Step 05 close (`7064132`) 후 main 동기화. `step06-program-constraint-engine` 브랜치 checkout. Step 06 결정 토론 진행 (scope 정상, density 0.85, role hard fail, min_area 중간안, 외부 JSON config 패턴, ApartmentAdapter rules_path required, 4-layer rules 분리) |
| 2026-05-09 | Plan v1 draft 작성 (16 decisions) |
| 2026-05-09 | §4.1 commit `3f09cbe` (Step 05 archive + scaffold). 82 passed. |
| 2026-05-09 | §4.2 commit `f241d58` (ProgramRequest + Role + spaces strict + serialize typing.Union fix). 92 passed. |
| 2026-05-09 | §4.3 commit `0da364b` (TargetRules + apartment.json + adapter target_type guard + package-data). 117 passed. |
| 2026-05-09 | §4.3a — generic TargetAdapter reform 토론 후 채택. typology 4개 (B/C/D/E) 본격 진입 확정 → per-typology 클래스 boilerplate 회피 동기. 단일 `TargetAdapter` + JSON self-describing typology + 3-layer extensibility. README 대폭 강화 (mission scope + 3-layer model). D022 신설. commit `372090b`. 120 passed. |
| 2026-05-09 | 외부 review (또 다른 Claude 인스턴스) — §4.4 진입 전 점검. 14 항목 + 추가 모델링 결함 8 항목 (required/optional, repair-vs-fail, cardinality 중복, access gate 데이터 부재, generic typology claim 과장, rules_loader completeness, area gate boundary, multi-floor 가정). cleanup 2 commit 으로 분리: (1) chore (serialize docstring + Plan/Tracker drift + ApartmentAdapter 잔재 + _MismatchAdapter target_type), (2) design (모델링 결함 8 항목). |
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
