# 002 Step 02 — Core Schema / Run Config / Debug Output Contract Tracker

Status: In progress
Started: 2026-05-04
Last updated: 2026-05-04
Branch: `step02-core-schema`
Companion plan: [002_Step02_CoreSchema_Plan.md](002_Step02_CoreSchema_Plan.md)

---

## 0. Purpose

이 문서는 **진행 로그 / 체크리스트**. [Plan](002_Step02_CoreSchema_Plan.md)과 1:1 매칭, 작업하면서 수시로 갱신.

| | Plan | Tracker |
|---|---|---|
| 무엇 | 결정·사양·인라인 자료 | 진행 상태·로그·이슈 |
| 갱신 | 의논 중에는 자주, 결정 후 동결 | 작업하며 수시 |

---

## 1. 작업 체크리스트

[Plan §4](002_Step02_CoreSchema_Plan.md)의 항목과 **동일한 번호**. 각 항목은 [§8 P5](002_Step02_CoreSchema_Plan.md) commit 1개와 매칭.

| # | 작업 | commit msg | 상태 | 완료일 |
|---|---|---|:---:|---|
| 4.1 | Step 01 docs archive + scaffold step02 modules + Plan/Tracker 추가 | `chore: archive step01 docs + scaffold step02 module structure` | [x] | 2026-05-04 |
| 4.2 | 22개 schema dataclass 정의 (input/program/region-atom/candidate/growth/validation) | `feat: schema dataclasses (input/program/region-atom/candidate/growth/validation)` | [x] | 2026-05-04 |
| 4.3 | RunConfig + DebugArtifact + run folder contract | `feat: RunConfig + DebugArtifact + run folder contract` | [x] | 2026-05-04 |
| 4.4 | serialize.py + smoke tests + serialize round-trip 1개 | `feat: serialization helpers + smoke tests` | [x] | 2026-05-04 |
| 4.5 | step02 cleanup (Plan/Tracker 마무리, Progress Tracker 갱신) | `docs: step02 cleanup (Plan/Tracker, Progress Tracker)` | [ ] | |

실행 순서: 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → (Step 종료) merge --no-ff to main.

---

## 2. DoD 검증 결과

[Plan §1](002_Step02_CoreSchema_Plan.md)의 DoD-1 ~ DoD-11.

| # | 조건 | 결과 | 검증 시각 |
|---|---|:---:|---|
| DoD-1 | §3 모듈 트리 모두 존재 | [x] | 2026-05-04 (4.1 후 — 11 modules import OK) |
| DoD-2 | 22개 schema dataclass 정의 (필드 + TBD 주석) | [x] | 2026-05-04 (모두 default instantiation OK + cross-module compose OK) |
| DoD-3 | `RunConfig` 정의 (S02-D4 6필드) | [x] | 2026-05-04 (default + override + atom defaults 600/300/800 검증) |
| DoD-4 | `DebugArtifact` + 17개 파일명 상수 + `run_folder()` 헬퍼 | [x] | 2026-05-04 (15 JSON distinct + SVG prefix/suffix + run_folder + stage_svg_filename) |
| DoD-5 | `to_json` / `from_json` round-trip OK | [x] | 2026-05-04 (BuildingInput full round-trip + RunConfig round-trip + missing-key default) |
| DoD-6 | `pytest -q` 모두 통과 | [x] | 2026-05-04 (9 passed) |
| DoD-7 | `pip install -e .` 회귀 없음 | [x] | 2026-05-04 (4.1 후 — 모든 새 모듈 import OK) |
| DoD-8 | Step 01 docs `legacy/step01/`로 이동됨 | [x] | 2026-05-04 (`git mv` 사용 — history 보존) |
| DoD-9 | `000_Progress_Tracker.md` Step 02 완료로 갱신 | [ ] | |
| DoD-10 | 5개 commit (P5)이 `step02-core-schema` 브랜치에 들어감 | [ ] | |
| DoD-11 | merge `--no-ff` 후 main 반영, branch 삭제 | [ ] | |

---

## 3. 진행 로그 (시간순)

| 시각 | 이벤트 |
|---|---|
| 2026-05-04 | Step 01 완료 후 main 동기화. `step02-core-schema` 브랜치 checkout |
| 2026-05-04 | Q1~Q8 의논 → 결정 S02-D1~D12 합의 |
| 2026-05-04 | RunConfig 확장성 우려 의논 → S02-D4에 확장 정책, §4.4 `from_dict` missing-key 처리로 보강 |
| 2026-05-04 | Plan 작성 완료 ([002_Step02_CoreSchema_Plan.md](002_Step02_CoreSchema_Plan.md)) |
| 2026-05-04 | 이 Tracker 생성 |
| 2026-05-04 | §4.1 완료 — Step 01 docs를 `legacy/step01/`로 git mv. `src/proto3/{config.py,debug.py}` + `src/proto3/schema/` (8 sub-modules) scaffold. 11개 모듈 모두 import OK |
| 2026-05-04 | §4.2 완료 — 22개 schema dataclass 정의 (input 3 / program 4 / region_atom 5 / candidate 5 / growth 2 / validation 3). `from __future__ import annotations` + `dataclass` + `field`. Cross-module reference 동작 (growth → candidate, program). 22개 default instantiation 통과 |
| 2026-05-04 | §4.3 완료 — `RunConfig` (6필드, default 모두 명시) + `DebugArtifact` + 15 JSON 파일명 상수 + `STAGE_SVG_PREFIX/SUFFIX` + `run_folder(run_id, base)` + `stage_svg_filename(stage_num, name)`. 모든 contract 검증 통과 |
| 2026-05-04 | §4.4 완료 — `serialize.py` (to_dict, from_dict, _reconstruct, to_json, from_json). I-S02-1 발견 + 즉시 해결 (nested generic 재귀). `tests/test_smoke.py` 확장 (6개 테스트), `tests/test_serialize.py` 신설 (3개). **9 passed in 0.02s** |

---

## 4. 발견 이슈 / Plan 변경

작업 중 Plan 갱신을 유발한 사항을 기록한다.

### I-S02-1. `_reconstruct`가 `list[tuple[float, float]]`의 안쪽 tuple을 처리 못함 (2026-05-04) — **해결**

§4.4 첫 pytest에서 `test_building_input_round_trip` fail. `FloorInput.footprint: list[tuple[float, float]]`가 round-trip 후 `list[list[float]]`로 됨.

원인: `_reconstruct`의 list 처리가 inner type을 dataclass인 경우만 재귀했고, tuple 같은 nested generic은 그냥 `list(value)` 반환.

**수정**: list 처리 시 항상 `_reconstruct(args[0], v)` 재귀. tuple도 동일하게 element 재귀. 한 번에 list[Dataclass], list[tuple], list[list[X]], tuple[Dataclass] 모두 동작.

→ 9 passed.

---

## 5. Step 종료 시 cleanup 체크리스트

[D016 cleanup 절차](000_Architecture_Decisions.md) 7단계 적용 (Plan §A 단계는 이번 Step에서 §A 미생성으로 skip).

- [ ] §1의 모든 작업이 [x] (4.1~4.5)
- [ ] §2의 모든 DoD가 [x] (DoD-1~11)
- [ ] `git status`로 의도하지 않은 untracked/dirty 없음 확인 (각 commit 직전)
- [ ] [`000_Progress_Tracker.md`](000_Progress_Tracker.md) 갱신 (Plan §4.5)
- [x] **Plan §A 제거** — *N/A* (S02-D7로 §A 미생성. D016 권장 첫 적용)
- [ ] Step 01 docs를 [`legacy/step01/`](legacy/) 로 이동 (Plan §4.1)
- [ ] **Step 02 docs 이동은 Step 03 kickoff 시점으로 이연** — Step 01 cleanup 패턴 일관 (사용자 결정 2026-05-03)
- [ ] **branch 종료**: main에 `git merge --no-ff step02-core-schema` → `git branch -d step02-core-schema` → `git push origin main` ([D015](000_Architecture_Decisions.md))
- [ ] git commit 메시지 컨벤션 ([D015](000_Architecture_Decisions.md)): prefix-style 1~2줄

---

## 6. 변경 이력 (이 Tracker 자체)

| 날짜 | 변경 |
|---|---|
| 2026-05-04 | 초기 생성. Plan §4 P5 5개 작업 + DoD 11개 + cleanup 8단계. |
