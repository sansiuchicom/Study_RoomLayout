# 004 Step 04 — Apartment Fixtures / Target Adapter Tracker

Status: Completed (pending merge)
Started: 2026-05-07
Completed: 2026-05-07
Branch: `step04-apartment-fixtures`
Companion plan: [004_Step04_ApartmentFixtures_Plan.md](004_Step04_ApartmentFixtures_Plan.md)

---

## 0. Purpose

이 문서는 **진행 로그 / 체크리스트**. [Plan](004_Step04_ApartmentFixtures_Plan.md)과 1:1 매칭, 작업하면서 수시로 갱신.

| | Plan | Tracker |
|---|---|---|
| 무엇 | 결정·사양 | 진행 상태·로그·이슈 |
| 갱신 | 의논 중에는 자주, 결정 후 동결 | 작업하며 수시 |

---

## 1. 작업 체크리스트

[Plan §4](004_Step04_ApartmentFixtures_Plan.md)의 항목과 **동일한 번호**. 각 항목은 [Plan §8](004_Step04_ApartmentFixtures_Plan.md) commit 1개와 매칭.

| # | 작업 | commit msg | 상태 | 완료일 |
|---|---|---|:---:|---|
| 4.1 | Step 03 docs archive + scaffold target/stages modules + Plan/Tracker 추가 | `chore: archive step03 docs + scaffold step04 module structure` | [x] | 2026-05-07 |
| 4.2 | TargetAdapter Protocol + ApartmentAdapter | `feat: target adapter protocol + apartment adapter (S04-D3, D12)` | [x] | 2026-05-07 |
| 4.3 | Stage 00 input load + normalization | `feat: stage 00 input load + normalization (S04-D4, D13)` | [x] | 2026-05-07 |
| 4.4 | Stage 01 program resolution frame + cardinality gate + ProgramInstantiationFailure | `feat: stage 01 program resolution frame + cardinality gate (S04-D4, D11, D12)` | [x] | 2026-05-07 |
| 4.5 | 5-fixture matrix (A2/B1/R1/R2 new + A1 reuse) + fixture_matrix.py | `feat: 5-fixture matrix (A2/B1/R1/R2 new + A1 reuse, S04-D1)` | [x] | 2026-05-07 |
| 4.6 | Tests: target adapter / stage00 / stage01 (R1 fail) / roundtrip | `feat: step04 tests (target adapter + stage 00/01 + R1 regression)` | [x] | 2026-05-07 |
| 4.7 | step04_fixture_overview notebook | `feat: step04 fixture overview notebook (5-fixture compare, S04-D9)` | [x] | 2026-05-07 |
| 4.8 | Step 04 cleanup (Plan/Tracker, Progress Tracker, merge --no-ff) | `docs: step04 cleanup (Plan/Tracker, Progress Tracker)` | [x] | 2026-05-07 |

실행 순서: 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 → 4.7 → 4.8 → (Step 종료) merge --no-ff to main.

---

## 2. DoD 검증 결과

[Plan §1](004_Step04_ApartmentFixtures_Plan.md)의 DoD-1 ~ DoD-14.

| # | 조건 | 결과 | 검증 시각 |
|---|---|:---:|---|
| DoD-1 | `src/proto3/target/` 모듈 트리 존재 + import OK | [x] | 2026-05-07 (§4.1 후 22 passed; §4.2에서 Protocol + ApartmentAdapter 구현) |
| DoD-2 | `src/proto3/stages/` 모듈 트리 존재 + import OK | [x] | 2026-05-07 (§4.1 후 22 passed) |
| DoD-3 | `ApartmentAdapter.load_fixture(path)` returns valid BuildingInput | [x] | 2026-05-07 (§4.6 test_target_adapter) |
| DoD-4 | Stage 00: fixture path → BuildingInput + target consistency check | [x] | 2026-05-07 (§4.6 test_stage00_load 5개) |
| DoD-5 | Stage 01: program_request → ProgramInstance + cardinality fail (D004) | [x] | 2026-05-07 (§4.4) |
| DoD-6 | 5 fixture 파일 존재 + 각 round-trip OK | [x] | 2026-05-07 (§4.5 sanity check 5/5 round-trip OK) |
| DoD-7 | `tests/fixture_matrix.py` 매핑 + metadata | [x] | 2026-05-07 (§4.5: A1~R2 5개 ID + expected_failure) |
| DoD-8 | R1 fixture가 Stage 01에서 ProgramInstantiationFailure 발생 | [x] | 2026-05-07 (§4.6 test_stage01_program::test_stage01_r1_raises) |
| DoD-9 | `pytest -q` 통과 (≥ 19 + 신규) | [x] | 2026-05-07 (39 passed: 22 기존 + 17 신규) |
| DoD-10 | `python -m pip install -e .` 회귀 없음 | [x] | 2026-05-07 (system `pip` alias targets py3.10 → fails on requires-python>=3.11; verified with `python -m pip install -e .` OK) |
| DoD-11 | Step 03 docs → `legacy/step03/` via git mv | [x] | 2026-05-07 (§4.1) |
| DoD-12 | `000_Progress_Tracker.md`가 Step 04 close 시점에 "Done" 갱신 | [x] | 2026-05-07 (§4.8) |
| DoD-13 | `notebooks/step04_fixture_overview.ipynb` 실행 시 5 SVG 생성 | [x] | 2026-05-07 사용자 VSCode 실행 후 5 SVG inline 표시 확인 (B1 외곽 L자 + 100mm grid 검증). 점선 모양은 stroke + grid 시각 겹침 (R-S03-3 styling 이슈, Step 05+) |
| DoD-14 | §4 commits all on `step04-apartment-fixtures` + merge --no-ff + branch 삭제 | [~] | 2026-05-07 (§4.8) Plan/Tracker/Progress Tracker 갱신 commit까지; merge --no-ff + branch 삭제는 사용자 확인 후 |
| DoD-15 | Progress Tracker가 4.1에서 "In progress", 4.8에서 "Done"으로 두 번 갱신 | [x] | 2026-05-07 (§4.1 In progress + §4.8 Done) |
| DoD-16 | `proto3.schema.validation.ProgramInstantiationFailure` exception 정의 + import OK | [x] | 2026-05-07 (§4.4) |

---

## 3. 진행 로그 (시간순)

| 시각 | 이벤트 |
|---|---|
| 2026-05-07 | Step 03 완료 후 main 동기화. `step04-apartment-fixtures` 브랜치 checkout. Step 03 docs `legacy/step03/`로 git mv staged (commit 4.1에 묶을 예정) |
| 2026-05-07 | 다른 세션 + 현 세션 합쳐 fixture matrix 8 → 5 축소 합의 (A1, A2, B1, R1, R2). 사선/곡선 deferred. R1만 Step 04 회로, R2는 Step 06 대기 |
| 2026-05-07 | 결정사항 S04-D1~D10 확정. Plan/Tracker 작성 |
| 2026-05-07 | 리뷰 반영 #1. S04-D11~D14 추가 (ProgramInstantiationFailure exception, R1 표현 방식, Stage 00 signature, legacy link 정책). DoD-15/16 추가. Plan §3.1 fixture 명세 표 신설 |
| 2026-05-07 | §4.1 완료 — Step 03 docs `legacy/step03/` 이동, target/stages 모듈 scaffold, drift fix (palette.py / debug.py), D016 amendment (H012), Pipeline §16 mirror, Progress Tracker kickoff update. commit `7ce53f4`. 22 passed |
| 2026-05-07 | §4.2 완료 — TargetAdapter Protocol (`target/base.py`) + ApartmentAdapter (`target/apartment.py`) 구현. `load_fixture` (from_json wrapper) + `target_rules` (apartment min_cardinality dict). commit `1e02b87` |
| 2026-05-07 | §4.3 완료 — `stages/stage00_load.run(path, *, run_config, adapter)` 구현. adapter resolution: explicit > run_config.target_type > apartment default. run_config 있으면 assert_target_consistent 호출. commit `2b03703` |
| 2026-05-07 | §4.4 완료 — `ProgramInstantiationFailure(Exception)` 추가 (`schema/validation.py`). `stages/stage01_program.run(building, *, adapter)` 구현: program_request → ProgramInstance + adapter.target_rules min_cardinality 비교, 미충족 시 raise (FailureRecord 보관). commit `acd62e7` |
| 2026-05-07 | §4.5 완료 — fixture 4개 신규 작성 (apartment_4bed_2bath, _l_shape, _no_bath, _too_small) + `tests/fixture_matrix.py` (5 matrix ID + expected_failure metadata). 5/5 round-trip OK. commit `1e165d3` |
| 2026-05-07 | §4.6 완료 — 4 test 파일 신규 (target_adapter, stage00_load, stage01_program, fixtures_roundtrip). 17 신규 테스트, 총 39 passed. 상대 import (`from .fixture_matrix`) 패턴 채택. commit `df58530` |
| 2026-05-07 | §4.7 완료 — `notebooks/step04_fixture_overview.ipynb` 작성 (6 cells: walk-up resolver, fixture_matrix import, 5-fixture render loop, inline SVG display, notes). 코드 검증 OK (5 SVG 생성 inline simulation). notebook execute는 사용자가 VSCode에서 verify. commit `d92edb5` |
| 2026-05-07 | 사용자 VSCode 실행 검증 — 5 SVG inline 표시 확인 (B1 L자 footprint 정확). DoD-13 [x] |
| 2026-05-07 | §4.8 cleanup 진행 — Plan/Tracker mark complete, Progress Tracker "Step 04 → Done" 갱신, 변경이력 업데이트 |

---

## 4. 이슈 / 계획 변경

(아직 없음)

---

## 5. Step-close cleanup checklist (D016 amendment)

Step 종료 시 순서대로:

- [x] Plan §4 모든 항목 [x] 확인
- [x] DoD §2 모든 항목 [x] 확인 (DoD-14 [~] merge 대기)
- [x] `git status` clean 확인
- [x] `000_Progress_Tracker.md` 갱신: Current step → "Step 04 complete (pending merge)", Active files → Step 04 docs as "Completed; pending move to legacy/step04/ at Step 05 kickoff", Step status table → Step 04 Done
- [-] (D016 amendment) Step 04 docs는 **Step 05 kickoff 시** `legacy/step04/`로 이동 — 이 Step에서는 옮기지 않음 (의도된 미수행)
- [x] git commit (4.8 = ce77b4d)
- [ ] `git checkout main && git merge --no-ff step04-apartment-fixtures && git branch -d step04-apartment-fixtures && git push origin main` (merge 사용자 확인 대기)

---

## 6. 변경이력

| Date | Change |
|---|---|
| 2026-05-07 | Initial. 8 work items, 14 DoD. |
| 2026-05-07 | 리뷰 반영 #1. DoD-15/16 추가. |
| 2026-05-07 | §4.8 close. 8 commits on `step04-apartment-fixtures` (7ce53f4 → cleanup). 39 passed. 14/16 DoD [x], DoD-14 [~] (merge 사용자 확인 대기). |
| 2026-05-07 | 리뷰 반영 #1 — Status 정정, cleanup checklist 마킹, DoD-10 명령 `python -m pip` + 검증 [x] (#1, #2). |
| 2026-05-07 | 리뷰 반영 #2 — Stage 01 program_request schema validation 추가 (#3). 3 tests 추가, total 42 passed. |
| 2026-05-07 | 리뷰 반영 #3 — `tests/test_fixtures_render_smoke.py` 신규 (#4). 5 fixture × geometry sanity (vertices/area/floor_root) + render-time XML/12-layer/footprint polygon 검증. 10 tests 추가, total 52 passed. |
