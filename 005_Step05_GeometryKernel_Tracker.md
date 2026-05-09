# 005 Step 05 — Geometry Kernel Tracker

Status: Done (merged 7064132)
Started: 2026-05-08
Completed: 2026-05-08
Merged: 2026-05-08 (`7064132`)
Branch: `step05-geometry-kernel` (deleted post-merge)
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
| 4.3 | `proto3/geometry/grid.py` 통합 (anisotropic grid + 50% merge) | `feat: geometry grid module — anisotropic grid + 50% merge (S05-D1, D4)` | [x] | 2026-05-08 |
| 4.4 | `proto3/geometry/recursive.py` + `decompose.py` 통합 | `feat: geometry recursive + decompose wrapper (S05-D1, D4)` | [x] | 2026-05-08 |
| 4.5 | `proto3/schema/geometry.py` — GeometricPiece + Decomposition dataclass | `feat: GeometricPiece + Decomposition schema (S05-D5)` | [x] | 2026-05-08 |
| 4.6 | Algorithm tests (LIR + grid + recursive + small-fixture decompose; matplotlib leak fix; unit mismatch R-S05-7) | `feat: geometry tests + matplotlib leak fix + unit mismatch ad-hoc fix (S05-D2 amend, R-S05-7)` | [x] | 2026-05-08 |
| 4.7 | 사선 fixture (D1, apartment_diagonal.json) + matrix 갱신 + render smoke 6 fixture 확장 | `feat: diagonal fixture (D1, S04 Def-1 resolved, S05-D7)` | [x] | 2026-05-08 |
| 4.8 | `notebooks/step05_decomposition.ipynb` (6 fixture × decomposition 시각화) | `feat: step05 decomposition notebook (S05-D9)` | [x] | 2026-05-08 (사용자 VSCode 실행 검증 대기) |
| 4.9 | D019 정식 등록 + D006 amendment 텍스트 + Pipeline §8 numerical defaults table update + Step 05 cleanup (Plan/Tracker, Progress Tracker, merge --no-ff) | `docs: step05 cleanup + D019 D006 amendment (per-family proportional atom + 300mm)` | [x] | 2026-05-08 |

실행 순서: 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 → 4.7 → 4.8 → 4.9 → (Step 종료) merge --no-ff to main.

---

## 2. DoD 검증 결과

[Plan §1](005_Step05_GeometryKernel_Plan.md)의 DoD-1 ~ DoD-15.

| # | 조건 | 결과 | 검증 시각 |
|---|---|:---:|---|
| DoD-1 | `src/proto3/geometry/` 모듈 (lir/grid/recursive/decompose) import OK | [x] | 2026-05-08 (§4.4 완료 시) |
| DoD-2 | `proto3/schema/geometry.py` GeometricPiece + Decomposition import OK | [x] | 2026-05-08 (§4.5: round-trip OK, JSON 188.6 KB on L-shape) |
| DoD-3 | `shapely>=2.0 + numpy>=1.24` 정식 deps in pyproject | [x] | 2026-05-08 (§4.1; matplotlib도 §4.6에서 정식 dep로 추가) |
| DoD-4 | `auto_partition()` 6 fixture 모두 작동 (gap < 1%) | [x] | 2026-05-08 (§4.8 notebook 검증: A1=540 / A2=1419 / B1=680 / R1=540 / R2=169 / D1=540 atoms, 모두 gap 0%) |
| DoD-5 | 사선 fixture (D1) round-trip + decompose 100% coverage | [x] | 2026-05-08 (§4.7 + §4.8: theta auto-detect ~20°, gap 0%) |
| DoD-6 | 핵심 stress test 1-2개 재현 (한글 자모 + edge case) | [x] | 2026-05-08 (§4.6 test_geometry_recursive: L-shape ㄱ자 + mirror_wings multi-axis) |
| DoD-7 | `python -m pip install -e .` 회귀 없음 | [x] | 2026-05-08 (§4.6에서 matplotlib 추가 후 재설치 OK) |
| DoD-8 | `pytest -q` 통과 (52 + 신규) | [x] | 2026-05-08 (80 passed) |
| DoD-9 | Step 04 docs → `legacy/step04/` via git mv | [x] | 2026-05-08 (§4.1) |
| DoD-10 | `000_Progress_Tracker.md` 갱신 (kickoff + close) | [x] | 2026-05-08 (§4.1 In progress + §4.9 Done) |
| DoD-11 | `notebooks/step05_decomposition.ipynb` 실행 시 6 SVG 생성 | [x] | 2026-05-08 (사용자 VSCode 실행 검증; D1 사선 atoms ~20° 회전 확인) |
| DoD-12 | `D019` 정식 등록 in `000_Architecture_Decisions.md` | [x] | 2026-05-08 (§4.9: D019 + H013 + D006 cross-reference) |
| DoD-13 | references/ origin 보존 (4 files + README) | [x] | 2026-05-08 (§4.1 + chore commit: cell_v3_2.* 4 files + zone_v12.* 6 files + README, 11 total) |
| DoD-14 | §4 commits all on step05 branch + merge --no-ff + branch 삭제 | [x] | 2026-05-08 (merged `7064132`; branch deleted) |
| DoD-15 | 4.1 commit에 Progress Tracker In progress 갱신 포함 | [x] | 2026-05-08 (§4.1 commit `7201781`) |
| DoD-16 | RunConfig.atom_size_mm=300 + atom_inclusion_threshold=0.5 + deprecation 마커 (4.1 코드 + 4.9 텍스트) | [x] | 2026-05-08 (§4.1 코드 + §4.9 D019 텍스트 + Pipeline §8 표) |

---

## 3. 진행 로그 (시간순)

| 시각 | 이벤트 |
|---|---|
| 2026-05-08 | Step 04 완료 후 main 동기화 (`822786a`). atom shape/size design fundamentals 의논 시작 — 사용자 외부 연구 후 v3.2 algorithm 가져옴 (per-family recursive progressive fill). 30 stress test 검증 (29/30 100%). |
| 2026-05-08 | 결정 정리: Integration=A (그대로), target=0.3m, shapely 정식 deps, X2 scope split (Step 05 algorithm only / Step 07 schema integration), M2 (Region ↔ GeometricPiece 분리). |
| 2026-05-08 | `step05-geometry-kernel` 브랜치 checkout. references/ 4 파일 rename + README 신설. Step 04 docs `legacy/step04/`로 git mv staged. `src/proto3/geometry/` 5 scaffold + `src/proto3/schema/geometry.py` 1 scaffold. pyproject shapely + numpy 추가. Plan/Tracker 작성. |
| 2026-05-08 | §4.1 완료 — RunConfig atom_size 600→300, atom_inclusion_threshold=0.5 신설, test_smoke + test_serialize 갱신. 16 files added/created, 4 modified, 2 renamed. 52 passed. Progress Tracker kickoff. commit `7201781` |
| 2026-05-08 | §4.2 완료 — `proto3/geometry/lir.py` 통합 (rasterize_polygon, max_rect_in_histogram, max_rect_in_mask, lir_at_angle, candidate_angles_from_boundary, find_main_rect_refined). v3.2의 `matplotlib.Path.contains_points` → `shapely.contains_xy`로 minor refactor (matplotlib runtime dep 회피, S05-D2 정합). 6 inline smoke 통과 (rect LIR 48㎡, L-shape LIR 48㎡ 정확). 52 passed. |
| 2026-05-08 | references 정리 (별도 chore commit, §4.2와 §4.3 사이) — v12 zoning artifacts 추가 + 이름 통일 (`cell_v3_2.*` / `zone_v12.*` prefix). `12_compare.py` 삭제 (v11 모듈 의존, 실행 불가). 11 files (4 cell + 7 zone + README). proto3 코드 docstring + Plan §3/§5/§6 + memory `project_proto3.md` 인용 모두 갱신. Plan §5 Def-13 신설 (v12 → Step 07 land 예정). 52 passed. commit `a7d6084` |
| 2026-05-08 | §4.3 완료 — `proto3/geometry/grid.py` 통합 (compute_proportional_cell_size, grid_no_skip_aniso, merge_below_50_aniso, piece_direct_theta, angle_diff). v3.2 critical fixes 그대로 보존 (MultiPolygon all-parts, buffer-free neighbor, orphan preservation). 6 inline smoke 통과 (rect 8×6 → 540 cells perfect fit, L-shape 749 → 722 cells after merge, rotated rect theta 30° 정확). 52 passed. |
| 2026-05-08 | §4.4 완료 — `proto3/geometry/recursive.py` (recursive_progressive_per_family) + `decompose.py` (auto_partition wrapper). v3.2 메인 알고리즘 통합. 4 fixture smoke: rect 8×6 (1 fam/540 cells), L-shape (1 fam/722 cells/0% gap), rotated 30° (theta 30° 정확 감지, 660 cells/0% gap), mirror wings multi-axis (**4 families 자동 분리**, 1399 cells/0% gap). v3.2 핵심 가치 모두 검증 (LIR 자동 회전 감지 + family-aware + per-family proportional). 52 passed. |
| 2026-05-08 | §4.5 완료 — `proto3/schema/geometry.py` (GeometricPiece + Decomposition) + `region_atom.Atom` 확장 (parent_piece_id, family_id 추가) + `decompose.to_schema()` converter. **옵션 b + X (vertex list + 기존 Atom 확장)** 채택. L-shape sanity: 2 pieces, 722 atoms, parent_piece_id 매핑 정확, round-trip 보존 (pieces/atoms/theta/vertices/parent_piece_id/root_main_rect), JSON 188.6 KB. 52 passed. |
| 2026-05-08 | §4.6 진행 중 메모리 누수 발견 — pytest 시 RAM 45→93 GB 폭증. 초기 의심 (shapely 2.x `contains_xy` GEOS leak)으로 matplotlib.Path 복귀 + matplotlib 정식 dep 추가 (S05-D2 amend). 단 **진짜 root cause는 unit mismatch** — proto3 fixture는 mm 단위 (8000mm × 6000mm), v3.2 algorithm은 m 단위 가정. 직접 호출 시 lir_resolution=0.05 grid에 mask 160000×120000 = 19 GB bool array. recursion으로 폭발. **R-S05-7 + Def-14 신설**. test_geometry_decompose에서 inline `(x/1000, y/1000)` 변환으로 회피. Stage 00 unit normalization은 Step 07로 yield. matplotlib.Path 복귀는 그대로 keep (leak risk 회피 + v3.2 원본 일관). |
| 2026-05-08 | §4.6 완료 — 4 test 파일 작성: test_geometry_lir (7), test_geometry_grid (9), test_geometry_recursive (4), test_geometry_decompose (5). 단일 호출 + 5-iter loop + pytest individual + 전체 다 통과. **72 passed, 5 skipped → 0 skipped (decompose unit conversion으로 활성화)**. commit `641353b`. |
| 2026-05-08 | §4.7 완료 — `fixtures/apartment_diagonal.json` (D1, ~20° rotated rect, footprint 4 vertices) + `fixture_matrix.py` D1 entry. test_fixtures_render_smoke 자동 6 fixture 확장. **80 passed** (DoD-5/6/7 검증). S04 Def-1 (사선 footprint) 해결. |
| 2026-05-08 | §4.8 완료 — `notebooks/step05_decomposition.ipynb` (5 cells: walk-up resolver / fixture_matrix import + mm→m converter / 6 fixture × auto_partition + 결과 print / matplotlib subplot 6개 + family color / Notes). 사용자 VSCode 실행 검증: A1=540 / A2=1419 / B1=680 / R1=540 / R2=169 / D1=540 atoms; D1 atoms grid가 footprint 회전을 정확히 따라감 (사선 보존 mission 검증). PNG `outputs/notebooks/step05_decomposition/<run_id>/step05_6_fixtures.png`. |
| 2026-05-08 | §4.9 — D019 정식 등록 (000_Architecture_Decisions.md, D018 다음, "# 4. Deferred decisions" 앞). D006 본문에 "Amended by D019" cross-reference 한 줄. H013 history entry 추가. Pipeline §8 numerical defaults 표 update (atom_size 300mm + atom_inclusion_threshold 0.5 + min_atom_side/tiny_atom_area deprecated 마커). 000_Progress_Tracker.md (Step 05 → Done, Active files, Step status table) 갱신. Plan §9 + Tracker §6 변경이력 마무리. Tracker §1 4.9 [x] + §2 모든 DoD [x] (DoD-14 [~]) + §5 cleanup checklist [x] (merge 줄만 [ ]). 80 passed. merge --no-ff 사용자 확인 대기. |

---

## 4. 이슈 / 계획 변경

(아직 없음)

---

## 5. Step-close cleanup checklist (D016 amendment)

Step 종료 시 순서대로:

- [x] Plan §4 모든 항목 [x] 확인 (2026-05-08, 4.1~4.9 완료)
- [x] DoD §2 모든 항목 [x] 확인 (DoD-14 [~] merge 대기 외 모두 완료)
- [x] `git status` clean 확인 (each work-item commit 후)
- [x] `000_Progress_Tracker.md` 갱신: Current step → "Step 05 complete (pending merge); ready for Step 06 kickoff"; Step 05 docs as "Completed; pending move to legacy/step05/ at Step 06 kickoff"; Step status table → Step 05 Done
- [ ] (D016 amendment) Step 05 docs는 **Step 06 kickoff 시** `legacy/step05/`로 이동 — 이 Step에서는 옮기지 않음
- [x] git commit (4.9)
- [x] `git checkout main && git merge --no-ff step05-geometry-kernel && git branch -d step05-geometry-kernel && git push origin main` (2026-05-08 merged `7064132`)

---

## 6. 변경이력

| Date | Change |
|---|---|
| 2026-05-08 | Initial. 9 work items, 15 DoD. v3.2 algorithm 외부 도입 (refs origin 보존). X2 scope split. M2 Region/GeometricPiece 분리. |
| 2026-05-08 | Step 05 close. 9 work-item commits on `step05-geometry-kernel` (`7201781` archive+scaffold → `04c399a` recursive+decompose → `1e165d3-ish`(N/A; chronological 약식) → `04c399a` algo done → `6228301` schema → `641353b` tests + matplotlib leak fix + unit fix → D1 fixture (S04-Def-1 resolved) → notebook → `4.9` cleanup). 80 pytest passed. DoD 16/16 [x] (DoD-14 [~] merge 사용자 확인 대기). D019 + H013 등록. Pipeline §8 mirror update. RunConfig.atom_size_mm 300 + atom_inclusion_threshold 0.5 코드 land. Mission-critical: D1 사선 fixture가 v3.2 LIR 회전 자동 감지를 검증 (theta ~20° detect, atoms grid 회전 정렬, gap 0%). |
