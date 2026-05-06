# 003 Step 03 — Visualization Renderer / Visual Vocabulary Tracker

Status: In progress
Started: 2026-05-06
Branch: `step03-visualization`
Companion plan: [003_Step03_Visualization_Plan.md](003_Step03_Visualization_Plan.md)

---

## 0. Purpose

이 문서는 **진행 로그 / 체크리스트**. [Plan](003_Step03_Visualization_Plan.md)과 1:1 매칭, 작업하면서 수시로 갱신.

| | Plan | Tracker |
|---|---|---|
| 무엇 | 결정·사양·인라인 자료 | 진행 상태·로그·이슈 |
| 갱신 | 의논 중에는 자주, 결정 후 동결 | 작업하며 수시 |

---

## 1. 작업 체크리스트

[Plan §4](003_Step03_Visualization_Plan.md)의 항목과 **동일한 번호**. 각 항목은 [§8](003_Step03_Visualization_Plan.md) commit 1개와 매칭.

| # | 작업 | commit msg | 상태 | 완료일 |
|---|---|---|:---:|---|
| 4.1 | Step 02 docs archive + scaffold viz module + Plan/Tracker 추가 | `chore: archive step02 docs + scaffold step03 module structure` | [x] | 2026-05-06 |
| 4.2 | Visual vocabulary palette + role_to_palette_key + corridor=grey | `feat: visual vocabulary v1 (12-layer order + palette + role mapping)` | [x] | 2026-05-06 |
| 4.3 | Minimal apartment fixture (`fixtures/apartment_minimal.json`, program_request dict 형식) | `feat: minimal apartment fixture (S03-D10)` | [x] | 2026-05-06 |
| 4.4 | SVG renderer core (12 layers, footprint + grid, Y-flip) | `feat: SVG renderer core (12-layer stable order, footprint+grid)` | [x] | 2026-05-06 |
| 4.5 | Smoke test (4 assertions covering DoD-4/6) | `feat: viz smoke test (12-layer stable order verified)` | [ ] | — |
| 4.6 | Notebook + .gitattributes + dev deps (nbstripout 정책 포함) | `feat: step03 viz demo notebook + nbstripout policy + dev deps` | [ ] | — |
| 4.7 | Step 03 cleanup (Plan/Tracker, Progress Tracker, merge --no-ff) | `docs: step03 cleanup (Plan/Tracker, Progress Tracker)` | [ ] | — |

실행 순서: 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 → 4.7 → (Step 종료) merge --no-ff to main.

---

## 2. DoD 검증 결과

[Plan §1](003_Step03_Visualization_Plan.md)의 DoD-1 ~ DoD-12.

| # | 조건 | 결과 | 검증 시각 |
|---|---|:---:|---|
| DoD-1 | `src/proto3/viz/` module tree exists per §3 (3 files) and all imports OK | [ ] | — |
| DoD-2 | `palette.py`: 12-entry `LAYER_ORDER` + `LAYER_COLORS` matching Pipeline §12.3 | [ ] | — |
| DoD-3 | `svg.py`: `render(building, *, ..., out_path)` keyword-only API | [ ] | — |
| DoD-4 | SVG contains exactly 12 `<g class="layer-NN-name">` in D013 order, even empty | [ ] | — |
| DoD-5 | `fixtures/apartment_minimal.json` exists + round-trip OK via Step 02 schema | [ ] | — |
| DoD-6 | Smoke test: file exists + valid XML + 12 layer groups + ≥1 footprint polygon | [ ] | — |
| DoD-7 | `pytest -q` passes (≥ 17 tests total) | [ ] | — |
| DoD-8 | `pip install -e .` regression-free (no new deps) | [ ] | — |
| DoD-9 | Step 02 docs moved to `legacy/step02/` via `git mv` | [ ] | — |
| DoD-10 | `000_Progress_Tracker.md` updated (Step 03 → Done) | [ ] | — |
| DoD-11 | All §4 commits land on `step03-visualization` branch | [ ] | — |
| DoD-12 | `git merge --no-ff` to main, branch deleted | [ ] | — |
| DoD-13 | Notebook executes top-to-bottom + writes `outputs/notebooks/step03_viz_demo/<run_id>/minimal.svg` | [ ] | — |
| DoD-14 | `.gitattributes` + `pyproject.toml [project.optional-dependencies] dev` set up | [ ] | — |

---

## 3. 진행 로그 (시간순)

| 시각 | 이벤트 |
|---|---|
| 2026-05-06 | Step 02 완료 후 main 동기화. `step03-visualization` 브랜치 checkout |
| 2026-05-06 | 사용자와 의논 → S03-D1~D11 합의 (Layer 12개 모두 stub / module 위치 / output 형태 / vocabulary v1 / API / coord system / grid 100mm / English-only / structural smoke / fixture spec / stdlib XML) |
| 2026-05-06 | Plan 작성 완료 ([003_Step03_Visualization_Plan.md](003_Step03_Visualization_Plan.md)) |
| 2026-05-06 | 이 Tracker 생성 |
| 2026-05-06 | 사전 schema 확인 → S03-D10 fixture 형식 수정 (program_request: dict), S03-D4에 role_to_palette_key + corridor=grey 보강. 노트북 컨벤션 추가 합의 → S03-D12~D15 추가, work item 4.6 신설, DoD-13/14 추가 |

---

## 4. 발견 이슈 / Plan 변경

작업 중 Plan 갱신을 유발한 사항을 기록한다.

(아직 없음.)

---

## 5. Step 종료 시 cleanup 체크리스트

[D016 cleanup 절차](000_Architecture_Decisions.md) 7단계 적용 (Plan §A 단계는 이번 Step에서 §A 미생성으로 skip).

- [ ] §1의 모든 작업이 [x] (4.1~4.7)
- [ ] §2의 모든 DoD가 [x] (DoD-1~14)
- [ ] `git status`로 의도하지 않은 untracked/dirty 없음 확인 (각 commit 직전)
- [ ] [`000_Progress_Tracker.md`](000_Progress_Tracker.md) 갱신 (§4.7에서)
- [ ] **Plan §A 제거** — *N/A* (S03-D 시점부터 §A 미생성, D016 권장)
- [ ] Step 02 docs를 [`legacy/step02/`](legacy/) 로 이동 (§4.1) — `git mv` 사용
- [ ] **Step 03 docs 이동은 Step 04 kickoff 시점으로 이연** (Step 01/02 패턴 일관)
- [ ] **branch 종료**: main에 `git merge --no-ff step03-visualization` → `git branch -d step03-visualization` → `git push origin main` ([D015](000_Architecture_Decisions.md))
- [ ] git commit 메시지 컨벤션 ([D015](000_Architecture_Decisions.md)): prefix-style 1~2줄

---

## 6. 변경 이력 (이 Tracker 자체)

| 날짜 | 변경 |
|---|---|
| 2026-05-06 | 초기 생성. Plan §4 6개 작업 + DoD 12개 + cleanup 9단계. |
| 2026-05-06 | 사전 revision: schema 확인 결과 반영(D10 fixture, D4 role mapping). 노트북 컨벤션 추가(D12~D15). Work item 4.6 신설(notebook), 기존 4.6→4.7. DoD-13/14 추가. |
