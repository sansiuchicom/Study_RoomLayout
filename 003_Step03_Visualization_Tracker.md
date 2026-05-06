# 003 Step 03 — Visualization Renderer / Visual Vocabulary Tracker

Status: Completed
Started: 2026-05-06
Completed: 2026-05-06
Branch: `step03-visualization` (merged into main via `--no-ff` at 22737ad, deleted)
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
| 4.5 | Smoke test (4 assertions covering DoD-4/6) | `feat: viz smoke test (12-layer stable order verified)` | [x] | 2026-05-06 |
| 4.6 | Notebook + .gitattributes + dev deps (nbstripout 정책 포함) | `feat: step03 viz demo notebook + nbstripout policy + dev deps` | [x] | 2026-05-06 |
| 4.7 | Step 03 cleanup (Plan/Tracker, Progress Tracker, merge --no-ff) | `docs: step03 cleanup (Plan/Tracker, Progress Tracker)` | [x] | 2026-05-06 |

실행 순서: 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 → 4.7 → (Step 종료) merge --no-ff to main.

---

## 2. DoD 검증 결과

[Plan §1](003_Step03_Visualization_Plan.md)의 DoD-1 ~ DoD-12.

| # | 조건 | 결과 | 검증 시각 |
|---|---|:---:|---|
| DoD-1 | `src/proto3/viz/` module tree exists per §3 (3 files) and all imports OK | [x] | 2026-05-06 (§4.1 후) |
| DoD-2 | `palette.py`: 12-entry `LAYER_ORDER` + `LAYER_COLORS` matching Pipeline §12.3 | [x] | 2026-05-06 (§4.2: 12 layers, 9 colors, 6 role mappings + fallback) |
| DoD-3 | `svg.py`: `render(building, *, ..., out_path)` keyword-only API | [x] | 2026-05-06 (§4.4) |
| DoD-4 | SVG contains exactly 12 `<g class="layer-NN-name">` in D013 order, even empty | [x] | 2026-05-06 (smoke test `test_render_layer_order_stable` 통과) |
| DoD-5 | `fixtures/apartment_minimal.json` exists + round-trip OK via Step 02 schema | [x] | 2026-05-06 (§4.3: from_json + to_json round-trip OK) |
| DoD-6 | Smoke test: file exists + valid XML + 12 layer groups + ≥1 footprint polygon | [x] | 2026-05-06 (§4.5: 4 assertions all pass) |
| DoD-7 | `pytest -q` passes (≥ 17 tests total) | [x] | 2026-05-06 (19 passed) |
| DoD-8 | `pip install -e .` regression-free (no new deps) | [x] | 2026-05-06 (runtime deps unchanged; jupyter/nbstripout in optional `dev` extras only) |
| DoD-9 | Step 02 docs moved to `legacy/step02/` via `git mv` | [x] | 2026-05-06 (§4.1) |
| DoD-10 | `000_Progress_Tracker.md` updated (Step 03 → Done) | [x] | 2026-05-06 (§4.7) |
| DoD-11 | All §4 commits land on `step03-visualization` branch | [x] | 2026-05-06 (7 commits 4.1~4.7) |
| DoD-12 | `git merge --no-ff` to main, branch deleted | [x] | 2026-05-06 (merge commit 22737ad; branch `step03-visualization` deleted; pushed to origin) |
| DoD-13 | Notebook executes top-to-bottom + writes `outputs/notebooks/step03_viz_demo/<run_id>/minimal.svg` | [x] | 2026-05-06 (사용자 VSCode 실행 후 SVG 생성 확인 — `outputs/notebooks/step03_viz_demo/20260506T125041/minimal.svg`) |
| DoD-14 | `.gitattributes` + `pyproject.toml [project.optional-dependencies] dev` set up | [x] | 2026-05-06 (§4.6) |

---

## 3. 진행 로그 (시간순)

| 시각 | 이벤트 |
|---|---|
| 2026-05-06 | Step 02 완료 후 main 동기화. `step03-visualization` 브랜치 checkout |
| 2026-05-06 | 사용자와 의논 → S03-D1~D11 합의 (Layer 12개 모두 stub / module 위치 / output 형태 / vocabulary v1 / API / coord system / grid 100mm / English-only / structural smoke / fixture spec / stdlib XML) |
| 2026-05-06 | Plan 작성 완료 ([003_Step03_Visualization_Plan.md](003_Step03_Visualization_Plan.md)) |
| 2026-05-06 | 이 Tracker 생성 |
| 2026-05-06 | 사전 schema 확인 → S03-D10 fixture 형식 수정 (program_request: dict), S03-D4에 role_to_palette_key + corridor=grey 보강. 노트북 컨벤션 추가 합의 → S03-D12~D15 추가, work item 4.6 신설, DoD-13/14 추가 |
| 2026-05-06 | §4.1 완료 — Step 02 docs `legacy/step02/`로 git mv. `src/proto3/viz/` (3 files) + `tests/test_viz_smoke.py` placeholder. 15 passed |
| 2026-05-06 | §4.2 완료 — `palette.py`에 LAYER_ORDER (12) + LAYER_COLORS (9) + role_to_palette_key + GRID_SPACING_MM/LABEL_FONT_FAMILY/LABEL_FONT_SIZE_RATIO. corridor=#888. 15 passed |
| 2026-05-06 | §4.3 완료 — `fixtures/apartment_minimal.json` (8m×6m, 1 floor, 3 program spaces). from_json + to_json round-trip OK |
| 2026-05-06 | §4.4 완료 — `svg.py`에 `render()` 구현. 12 layer stable order, footprint polygon (stroke=40, black), 100mm grid in atoms layer, Y-axis flip, 5% padding viewBox, stdlib ET only |
| 2026-05-06 | §4.5 완료 — 4 smoke tests added: render creates file / 12 layers in stable order / footprint polygon present / empty layers stay empty. 19 passed |
| 2026-05-06 | §4.6 — notebook (6 cells), .gitattributes, pyproject.toml dev extras. 사용자 VSCode 실행 검증 중 I-S03-2 발견 (cwd) → walk-up resolver로 fix. I-S03-1 발견 (gitignore 누락) → .gitignore에 outputs/notebooks/* + .gitkeep 추가. SVG 시각 결과 (I-S03-3 dense grid)는 fine styling으로 deferred |
| 2026-05-06 | §4.7 — Progress Tracker 갱신, Tracker DoD/cleanup 마킹, 변경이력 업데이트. merge --no-ff 진행 |

---

## 4. 발견 이슈 / Plan 변경

작업 중 Plan 갱신을 유발한 사항을 기록한다.

### I-S03-1. `outputs/notebooks/*`가 `.gitignore`에 누락 (2026-05-06, §4.6) — **해결**

S03-D13 Plan에서 "outputs/는 이미 gitignored"라고 단정했으나, 실제 `.gitignore`는 `outputs/debug_runs/*` (subdir 단위 selective)만 커버하고 `outputs/notebooks/*`는 미커버. 사용자가 노트북 실행하니 SVG가 untracked로 떠올랐음.

**수정**: `.gitignore`에 `outputs/notebooks/*` + `!outputs/notebooks/.gitkeep` 추가 (debug_runs 패턴과 일관). `outputs/notebooks/.gitkeep` 빈 파일 생성. Plan §2 S03-D13 워딩도 정정 ("now gitignored via .gitignore extension in §4.6"). §4.6 commit에 함께 들어감.

### I-S03-2. VSCode Jupyter는 노트북 파일 디렉토리를 cwd로 잡음 (2026-05-06, §4.6) — **해결**

초기 guard cell이 `Path.cwd()` 기준으로 `pyproject.toml`이 cwd 직속에 있어야 한다고 가정. VSCode Jupyter는 cwd를 노트북 파일 위치(`notebooks/`)로 설정 → AssertionError.

**수정**: guard cell을 `_find_repo_root(start: Path)` 함수로 교체. `start.resolve()`부터 부모 dir들 순회하며 `pyproject.toml`을 찾을 때까지 올라감. cwd 어디든 동작. S03-D12 워딩에 walk-up 패턴 명시 (다른 노트북에도 같은 컨벤션 적용).

### I-S03-3. 100mm grid가 시각적으로 너무 dense (2026-05-06, §4.6) — **deferred**

8000×6000mm를 100mm 단위로 자르면 80×60 격자. 800px display에서 격자가 px 한두 개 간격이라 회색 단색처럼 보임. Footprint outline (stroke=40mm)도 grid line과 좌표 정렬되어 이중선처럼 보이는 효과 발생.

**판단**: fine styling 영역. Plan §5 Def-5에 "fine styling refinements"로 이미 deferred 처리되어 있음. Step 03 시점에는 기능적 정확성 (12 layer, polygon, grid 모두 그려짐)으로 OK 판단. major/minor grid (1000mm 진하게 + 100mm 옅게) 등은 추후 visual polish 후속.

### I-S03-4. 노트북 cell outputs가 stripped 안 된 채 §4.6 commit에 들어감 (2026-05-06, 사후 리뷰 #1) — **해결**

§4.6 commit `f321d5d`의 `notebooks/step03_viz_demo.ipynb`에 cell 1~4의 `execution_count` (1~4) + `outputs` (각각 1개씩, base64-inlined SVG 등 포함)가 그대로 들어감. S03-D14는 strip on commit 정책인데 활성화 안 됨.

**원인**: `.gitattributes`에 `*.ipynb filter=nbstripout`은 등록했지만, `nbstripout --install`은 사용자가 실행 안 함. 이 명령은 `.git/config`에 filter 정의를 등록하는 단계로, `.gitattributes`만으로는 git이 filter를 호출하지 못함. Plan §4.6 prereq 1줄에만 적혀 있었고 강조가 약했음.

**해결** (review followups #3): `nbstripout` 명령으로 cell outputs strip한 버전 commit. Plan §4.6에 **CRITICAL** 경고 추가 — "각 contributor는 clone마다 한 번 `nbstripout --install` 실행 필수". 이전 commit의 cell outputs는 git history에 남아있음 (force-push 안 함; 차후 필요 시 git-filter-repo로 정리 가능).

---

## 5. Step 종료 시 cleanup 체크리스트

[D016 cleanup 절차](000_Architecture_Decisions.md) 7단계 적용 (Plan §A 단계는 이번 Step에서 §A 미생성으로 skip).

- [x] §1의 모든 작업이 [x] (4.1~4.7)
- [x] §2의 모든 DoD가 [x] (DoD-1~14, DoD-12는 이 commit 직후 merge로 마무리)
- [x] `git status`로 의도하지 않은 untracked/dirty 없음 확인 (각 commit 직전)
- [x] [`000_Progress_Tracker.md`](000_Progress_Tracker.md) 갱신 (§4.7)
- [x] **Plan §A 제거** — *N/A* (S03-D 시점부터 §A 미생성, D016 권장)
- [x] Step 02 docs를 [`legacy/step02/`](legacy/) 로 이동 (§4.1) — `git mv` 사용
- [x] **Step 03 docs 이동은 Step 04 kickoff 시점으로 이연** (Step 01/02 패턴 일관)
- [x] **branch 종료**: main에 `git merge --no-ff step03-visualization` → `git branch -d step03-visualization` → `git push origin main` ([D015](000_Architecture_Decisions.md)) — 이 commit 직후 진행
- [x] git commit 메시지 컨벤션 ([D015](000_Architecture_Decisions.md)): prefix-style 1~2줄 — 7개 commit 모두 적용

---

## 6. 변경 이력 (이 Tracker 자체)

| 날짜 | 변경 |
|---|---|
| 2026-05-06 | 초기 생성. Plan §4 6개 작업 + DoD 12개 + cleanup 9단계. |
| 2026-05-06 | 사전 revision: schema 확인 결과 반영(D10 fixture, D4 role mapping). 노트북 컨벤션 추가(D12~D15). Work item 4.6 신설(notebook), 기존 4.6→4.7. DoD-13/14 추가. |
| 2026-05-06 | Step 03 마무리. Status: In progress → Completed. §1 작업 4.1~4.7 모두 [x], §2 DoD-1~14 모두 [x] (DoD-12는 merge 직후), §3 진행 로그 7건 추가, §4 발견 이슈 3건 기록 (I-S03-1/2 해결 / I-S03-3 deferred), §5 cleanup 9개 [x]. |
