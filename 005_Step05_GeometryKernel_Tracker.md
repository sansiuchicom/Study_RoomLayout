# 005 Step 05 — Geometry Kernel Tracker

Status: In progress
Started: 2026-05-08
Branch: `step05-geometry-kernel`
Companion plan: [005_Step05_GeometryKernel_Plan.md](005_Step05_GeometryKernel_Plan.md)

---

## 0. Purpose

이 문서는 **진행 로그 / 체크리스트**. [Plan](005_Step05_GeometryKernel_Plan.md)과 1:1 매칭, 작업하면서 수시로 갱신.

| | Plan | Tracker |
|---|---|---|
| 무엇 | 결정·사양 | 진행 상태·로그·이슈 |
| 갱신 | 의논 중에는 자주, 결정 후 동결 | 작업하며 수시 |

---

## 1. 작업 체크리스트

[Plan §4](005_Step05_GeometryKernel_Plan.md)의 항목과 **동일한 번호**. 각 항목은 [Plan §8](005_Step05_GeometryKernel_Plan.md) commit 1개와 매칭.

| # | 작업 | commit msg | 상태 | 완료일 |
|---|---|---|:---:|---|
| 4.1 | Step 04 archive + geometry scaffold + references 정리 + pyproject deps + RunConfig atom_size 600→300 + atom_inclusion_threshold 신설 + tests 갱신 + Plan/Tracker + Progress Tracker kickoff | `chore: archive step04 docs + scaffold step05 geometry module + references + atom default 300mm` | [x] | 2026-05-08 (`7201781`) |
| 4.2 | `proto3/geometry/lir.py` 통합 (rasterize + max_rect + LIR search) | `feat: geometry lir module — LIR search + max_rect (S05-D1)` | [x] | 2026-05-08 |
| 4.3 | `proto3/geometry/grid.py` 통합 (anisotropic grid + 50% merge) | `feat: geometry grid module — anisotropic grid + 50% merge (S05-D1, D4)` | [ ] | |
| 4.4 | `proto3/geometry/recursive.py` + `decompose.py` 통합 | `feat: geometry recursive + decompose wrapper (S05-D1, D4)` | [ ] | |
| 4.5 | `proto3/schema/geometry.py` — GeometricPiece + Decomposition dataclass | `feat: GeometricPiece + Decomposition schema (S05-D5)` | [ ] | |
| 4.6 | Algorithm tests (LIR + grid + recursive + 6-fixture integration) | `feat: geometry tests (lir + grid + recursive + 6-fixture integration)` | [ ] | |
| 4.7 | 사선 fixture (D1, apartment_diagonal.json) + matrix 갱신 + render smoke 6 fixture 확장 | `feat: diagonal fixture (D1, S04 Def-1 resolved, S05-D7)` | [ ] | |
| 4.8 | `notebooks/step05_decomposition.ipynb` (6 fixture × decomposition 시각화) | `feat: step05 decomposition notebook (S05-D9)` | [ ] | |
| 4.9 | D019 정식 등록 + D006 amendment 텍스트 + Pipeline §8 numerical defaults table update + Step 05 cleanup (Plan/Tracker, Progress Tracker, merge --no-ff) | `docs: step05 cleanup + D019 D006 amendment (per-family proportional atom + 300mm)` | [ ] | |

실행 순서: 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 → 4.7 → 4.8 → 4.9 → (Step 종료) merge --no-ff to main.

---

## 2. DoD 검증 결과

[Plan §1](005_Step05_GeometryKernel_Plan.md)의 DoD-1 ~ DoD-15.

| # | 조건 | 결과 | 검증 시각 |
|---|---|:---:|---|
| DoD-1 | `src/proto3/geometry/` 모듈 (lir/grid/recursive/decompose) import OK | [ ] | |
| DoD-2 | `proto3/schema/geometry.py` GeometricPiece + Decomposition import OK | [ ] | |
| DoD-3 | `shapely>=2.0 + numpy>=1.24` 정식 deps in pyproject | [ ] | |
| DoD-4 | `auto_partition()` 6 fixture 모두 작동 (gap < 1%) | [ ] | |
| DoD-5 | 사선 fixture (D1) round-trip + decompose 100% coverage | [ ] | |
| DoD-6 | 핵심 stress test 1-2개 재현 (한글 자모 + edge case) | [ ] | |
| DoD-7 | `python -m pip install -e .` 회귀 없음 | [ ] | |
| DoD-8 | `pytest -q` 통과 (52 + 신규) | [ ] | |
| DoD-9 | Step 04 docs → `legacy/step04/` via git mv | [ ] | |
| DoD-10 | `000_Progress_Tracker.md` 갱신 (kickoff + close) | [ ] | |
| DoD-11 | `notebooks/step05_decomposition.ipynb` 실행 시 6 SVG 생성 | [ ] | |
| DoD-12 | `D019` 정식 등록 in `000_Architecture_Decisions.md` | [ ] | |
| DoD-13 | references/ origin 보존 (4 files + README) | [ ] | |
| DoD-14 | §4 commits all on step05 branch + merge --no-ff + branch 삭제 | [ ] | |
| DoD-15 | 4.1 commit에 Progress Tracker In progress 갱신 포함 | [ ] | |
| DoD-16 | RunConfig.atom_size_mm=300 + atom_inclusion_threshold=0.5 + deprecation 마커 (4.1 코드 + 4.9 텍스트) | [ ] | |

---

## 3. 진행 로그 (시간순)

| 시각 | 이벤트 |
|---|---|
| 2026-05-08 | Step 04 완료 후 main 동기화 (`822786a`). atom shape/size design fundamentals 의논 시작 — 사용자 외부 연구 후 v3.2 algorithm 가져옴 (per-family recursive progressive fill). 30 stress test 검증 (29/30 100%). |
| 2026-05-08 | 결정 정리: Integration=A (그대로), target=0.3m, shapely 정식 deps, X2 scope split (Step 05 algorithm only / Step 07 schema integration), M2 (Region ↔ GeometricPiece 분리). |
| 2026-05-08 | `step05-geometry-kernel` 브랜치 checkout. references/ 4 파일 rename + README 신설. Step 04 docs `legacy/step04/`로 git mv staged. `src/proto3/geometry/` 5 scaffold + `src/proto3/schema/geometry.py` 1 scaffold. pyproject shapely + numpy 추가. Plan/Tracker 작성. |
| 2026-05-08 | §4.1 완료 — RunConfig atom_size 600→300, atom_inclusion_threshold=0.5 신설, test_smoke + test_serialize 갱신. 16 files added/created, 4 modified, 2 renamed. 52 passed. Progress Tracker kickoff. commit `7201781` |
| 2026-05-08 | §4.2 완료 — `proto3/geometry/lir.py` 통합 (rasterize_polygon, max_rect_in_histogram, max_rect_in_mask, lir_at_angle, candidate_angles_from_boundary, find_main_rect_refined). v3.2의 `matplotlib.Path.contains_points` → `shapely.contains_xy`로 minor refactor (matplotlib runtime dep 회피, S05-D2 정합). 6 inline smoke 통과 (rect LIR 48㎡, L-shape LIR 48㎡ 정확). 52 passed. |

---

## 4. 이슈 / 계획 변경

(아직 없음)

---

## 5. Step-close cleanup checklist (D016 amendment)

Step 종료 시 순서대로:

- [ ] Plan §4 모든 항목 [x] 확인
- [ ] DoD §2 모든 항목 [x] 확인
- [ ] `git status` clean 확인
- [ ] `000_Progress_Tracker.md` 갱신: Current step → "Step 05 done; ready for Step 06 kickoff", Step 05 docs as "Completed; pending move to legacy/step05/ at Step 06 kickoff", Step status table → Step 05 Done
- [ ] (D016 amendment) Step 05 docs는 **Step 06 kickoff 시** `legacy/step05/`로 이동
- [ ] git commit (4.9)
- [ ] `git checkout main && git merge --no-ff step05-geometry-kernel && git branch -d step05-geometry-kernel && git push origin main`

---

## 6. 변경이력

| Date | Change |
|---|---|
| 2026-05-08 | Initial. 9 work items, 15 DoD. v3.2 algorithm 외부 도입 (refs origin 보존). X2 scope split. M2 Region/GeometricPiece 분리. |
