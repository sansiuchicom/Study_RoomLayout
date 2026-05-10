# 005 Step 05 — Geometry Kernel Plan

Status: Completed (merged 7064132)
Started: 2026-05-08
Completed: 2026-05-08
Branch: `step05-geometry-kernel`
Companion tracker: [005_Step05_GeometryKernel_Tracker.md](005_Step05_GeometryKernel_Tracker.md)

---

## 0. Purpose

Step 05 = "Geometry Kernel / Atom Resolution Commitments" per [Pipeline §15](000_Pipeline_Overview.md#L963). 산출물 4가지:

1. **`proto3.geometry` 패키지** — LIR (Largest Inscribed Rectangle) + per-family recursive decomposition + anisotropic grid + 50% merge rule. 외부 사용자 작업 ([references/cell_v3_2.py](references/cell_v3_2.py))를 Option A (그대로 + minor wrapper)로 import.
2. **`GeometricPiece` + `Decomposition` schema 신설** — v3.2 algorithm output을 받는 proto3 schema. D006 `Region/RegionSet` (architectural territory)과는 **별도 layer** (M2 결정). Region 매핑은 Step 07로 yield.
3. **D006 amendment (D019 정식 등록)** — atom = "fixed 600mm cube" → "target 근처에서 family별 proportional"로 의미 정제. target_cell_size = 0.3m.
4. **사선 fixture 추가** — 회전된 apartment 1개 (D1). v3.2 algorithm이 사선 boundary 처리하는지 fixture로 검증.

**X2 scope split**: Step 05는 algorithm import + standalone 검증 + 사선 fixture까지. proto3 schema 통합 (Stage 04 본격, RegionSet ↔ GeometricPiece 매핑)은 [Step 07](000_Pipeline_Overview.md#L965)로 yield.

**shapely + numpy 정식 의존성 추가** — Q1 초기 결정 (pure stdlib) 뒤집음. mission (scan-to-BIM 학습 데이터, 사선/곡선 footprint robust 처리) 정합성 + v3.2 algorithm 의존성 정당화.

---

## 1. Definition of Done

| # | 조건 | 검증 방법 |
|---|---|---|
| DoD-1 | `src/proto3/geometry/` 모듈 트리 존재 + import OK (`lir`, `grid`, `recursive`, `decompose`) | unit test |
| DoD-2 | `src/proto3/schema/geometry.py` — `GeometricPiece` + `Decomposition` dataclass 정의 + import OK | unit test |
| DoD-3 | `shapely>=2.0` + `numpy>=1.24` 정식 runtime 의존성 (pyproject `[project] dependencies`) | install check |
| DoD-4 | `proto3.geometry.decompose.auto_partition(footprint)` 작동 — 5 fixture (A1, A2, B1, R1, R2) + 1 신규 사선 fixture (D1) 모두 decomposition (gap < 1%) | integration test |
| DoD-5 | 사선 fixture (D1 = `apartment_diagonal.json`) 추가 — 회전된 apartment, footprint round-trip OK + decomposition 100% coverage | round-trip + decompose test |
| DoD-6 | Algorithm 핵심 stress test 재현 — 한글 자모 1-2개 (예: ㄱ자, ㄴ자) + edge case 1-2개 (예: triangle, circle) | algorithm test |
| DoD-7 | `python -m pip install -e .` 회귀 없음 — shapely, numpy 새 의존성 정상 설치 | install check |
| DoD-8 | `pytest -q` 통과 (Step 04의 52 + Step 05 신규) | pytest |
| DoD-9 | Step 04 docs → `legacy/step04/` via `git mv` | git ls-files |
| DoD-10 | `000_Progress_Tracker.md` 갱신: Step 05 → Done (close 시) + In progress (kickoff §4.1) | manual |
| DoD-11 | `notebooks/step05_decomposition.ipynb` 실행 시 `outputs/notebooks/step05_decomposition/<run_id>/`에 6 SVG 생성 (5 기존 + 1 사선) — decomposition 시각화 (cell coloring by family_id) | notebook 실행 |
| DoD-12 | `D019` (D006 amendment — per-family proportional atom sizing) 정식 등록 in `000_Architecture_Decisions.md` | grep |
| DoD-13 | references/ 디렉토리 origin 보존 — `cell_v3_2.{py,md}` + 2 cell stress PNG + `zone_v12.{py,md}` + 4 zone PNG + `README.md` (총 11 files) | git ls-files |
| DoD-14 | §4 commits 모두 `step05-geometry-kernel` branch + `git merge --no-ff` to main + branch 삭제 | git log |
| DoD-15 | 4.1 commit에 Progress Tracker §1/§6 "In progress" 갱신 포함 | git diff |
| DoD-16 | RunConfig.atom_size_mm = 300 + atom_inclusion_threshold = 0.5 + min_atom_side_mm/tiny_atom_area deprecation 마커 (4.1에서 코드 + 4.9에서 D006/Pipeline §8 텍스트) | grep + test_smoke |

---

## 2. 결정 기록

| ID | 결정 | 근거 |
|---|---|---|
| **S05-D1** | v3.2 algorithm을 **Option A (그대로 + minor wrapper)**로 import. `references/cell_v3_2.py`의 함수들을 `src/proto3/geometry/{lir,grid,recursive,decompose}.py`로 분할. proto3 컨벤션 맞춰 minor refactor (한국어 주석은 영어로, import path 정리). | 검증된 30 stress test 재현 (29/30 100% coverage). 재작성 churn 회피. |
| **S05-D2** | **shapely>=2.0 + numpy>=1.24 정식 runtime 의존성** (`[project] dependencies`). Step 05 초기 Q1 (pure stdlib) 결정 뒤집음. | scan-to-BIM mission (사선/곡선 footprint robust 처리) 정당화 + v3.2 algorithm 의존성. shapely는 polygon ops, numpy는 rasterize. |
| **S05-D3** | **atom_size_mm = 300mm로 통일** (was 600mm; D006 amendment via D019). v3.2 algorithm default와 일치. RunConfig.atom_size_mm 600→300 + `atom_inclusion_threshold = 0.5` 신설 (v3.2 50% rule). `min_atom_side_mm`, `tiny_atom_area_m2`은 **deprecated 명시** — v3.2가 area-fraction threshold로 대체. door defaults는 그대로 (도메인 가정). 4.1에서 RunConfig + tests 코드 변경, 4.9에서 D006/Pipeline §8 텍스트 amendment + D019 정식 등록. | v3.2 algorithm 기준 일관성. mission resolution (욕실 1.5×2m → 5×7 atoms) 충분. min_atom_side / tiny_area는 v3.2가 안 쓰는 개념이라 deprecate가 정직. |
| **S05-D4** | **D006 amendment (D019 정식 등록)** — atom = "고정 600mm cube" → "target 근처 family별 proportional fit". Same-theta family = same cell size + phase chain (seamless), different-theta family = self-computed cell size. Boundary cells = polygon clipped by region edge (50% merge rule). | mission (사선 보존) + 알고리즘 단순성 (interior grid) 둘 다 만족. v3.2 검증으로 정합성 입증. |
| **S05-D5** | **`GeometricPiece` + `Decomposition` schema 신설** (`src/proto3/schema/geometry.py`). D006 `Region/RegionSet`은 **건드리지 않음** — architectural territory layer 그대로. **M2 결정**: GeometricPiece (algorithm output, no architectural label) → Region (architectural label) 매핑은 [Step 07/09](000_Pipeline_Overview.md#L965)로 yield. | piece = geometric, region = architectural. 의미 분리 정직. proto3 design intent (D006 lobe/bay/public-candidate) 보존. |
| **S05-D6** | **Step 05 scope = X2 (algorithm only + standalone validation)**. proto3 schema integration (Stage 04 통합, RegionSet ↔ Decomposition 매핑)은 Step 07. Stage 03 anchor projection은 no-op (Step 04에서 stub만 만들었던 그대로 keep). | Pipeline §15 책임 분할 존중. Step 05 lean 유지 (~9 work items). |
| **S05-D7** | **사선 fixture 1개 추가** (`apartment_diagonal.json`, matrix ID = D1). 회전 ~20° apartment (v3.2 stress test의 "회전 7자" 변형). 매트릭스 ID 할당 — Step 04의 A/B/R 시리즈에 D 추가 ("D"iagonal). | atom-grid fitter 검증 + S04 Def-1 해소. Step 04 5-matrix → 6-matrix로 확장. |
| **S05-D8** | **v3.2 한계 6개를 §5 Deferred로 명시** — fragmentation, 45° floating-point, cell adjacency graph 미구축, junction irregular, LIR hole 무시, same-theta separation. 모두 cosmetic 또는 future Step 책임. | v3.2 docs §7에 정직히 명시된 한계. proto3에서도 동일 처리. |
| **S05-D9** | `notebooks/step05_decomposition.ipynb` 추가 — 6 fixture × decomposition 시각화 (cell coloring by family_id). Step 03 notebook 패턴 (walk-up cwd resolver, run_id 디렉토리, nbstripout) 재사용. | 시각화 default 원칙 + 사용자 직접 검증 가능. |
| **S05-D10** | `references/` 디렉토리 origin 보존 — 외부 사용자 작업물 직접 수정 금지 (README.md에 명시). proto3 코드 변경은 `src/proto3/geometry/` 쪽에서만. | provenance 추적 + 외부 algorithm 진화 시 swap 가능. |

---

## 3. Directory structure (Step 05 완료 시)

```text
src/proto3/
├── geometry/                       # 신설
│   ├── __init__.py
│   ├── lir.py                      # rasterize + max_rect + LIR search
│   ├── grid.py                     # anisotropic grid + 50% merge
│   ├── recursive.py                # per-family recursive decompose
│   └── decompose.py                # high-level wrapper (auto_partition)
├── schema/
│   └── geometry.py                 # 신설: GeometricPiece + Decomposition
├── (기존: config, debug, schema/{input,program,...,validation}, viz/, target/, stages/)

references/                         # 신설 (외부 작업물 origin 보존)
├── README.md
├── cell_v3_2.py                    # v3.2 cell partition algorithm
├── cell_v3_2.md
├── cell_v3_2_stress.png            # v3.2 stress test 일반 15
├── cell_v3_2_edges.png             # v3.2 edge case 15
├── zone_v12.py                     # v12 zoning algorithm (Step 07 land 예정)
├── zone_v12.md
├── zone_v12_evolution_g1.png       # v11 → v12 evolution 시각 1
├── zone_v12_evolution_g2.png
├── zone_v12_evolution_g3.png
└── zone_v12_showcase.png           # v12 33 cases showcase

fixtures/
├── apartment_minimal.json          # A1 (Step 03)
├── apartment_4bed_2bath.json       # A2 (Step 04)
├── apartment_l_shape.json          # B1 (Step 04)
├── apartment_no_bath.json          # R1 (Step 04)
├── apartment_too_small.json        # R2 (Step 04)
└── apartment_diagonal.json         # D1 (Step 05 신규, 회전 ~20°)

notebooks/
├── step03_viz_demo.ipynb           # (Step 03)
├── step04_fixture_overview.ipynb   # (Step 04)
└── step05_decomposition.ipynb      # 신설 — 6 fixture × decomposition 시각화

tests/
├── (기존)
├── test_geometry_lir.py            # 신설 — LIR + max_rect 검증
├── test_geometry_grid.py           # 신설 — anisotropic grid + 50% merge
├── test_geometry_recursive.py      # 신설 — per-family recursive
├── test_geometry_decompose.py      # 신설 — high-level integration (6 fixture × auto_partition)
└── test_fixtures_render_smoke.py   # 갱신 — 6 fixture로 확장

legacy/step04/                      # 신설 (archive)
├── 004_Step04_ApartmentFixtures_Plan.md
└── 004_Step04_ApartmentFixtures_Tracker.md
```

---

## 4. Work items

[Tracker §1](005_Step05_GeometryKernel_Tracker.md)와 1:1 매칭. 각 항목 = 1 commit.

| # | 작업 | commit msg |
|---|---|---|
| 4.1 | Step 04 docs archive + `src/proto3/geometry/` & `src/proto3/schema/geometry.py` scaffold + `references/` 정리 (rename + README) + pyproject `shapely + numpy` 의존성 + **RunConfig.atom_size_mm 600→300 + atom_inclusion_threshold=0.5 신설 + 관련 tests 갱신** + Plan/Tracker 추가 + Progress Tracker kickoff | `chore: archive step04 docs + scaffold step05 geometry module + references + atom default 300mm` |
| 4.2 | `proto3/geometry/lir.py` 통합 — `rasterize_polygon`, `max_rect_in_histogram`, `max_rect_in_mask`, `lir_at_angle`, `candidate_angles_from_boundary`, `find_main_rect_refined` (영어 주석으로 정리) | `feat: geometry lir module — LIR search + max_rect (S05-D1)` |
| 4.3 | `proto3/geometry/grid.py` 통합 — `compute_proportional_cell_size`, `grid_no_skip_aniso`, `merge_below_50_aniso`, `piece_direct_theta`, `angle_diff` | `feat: geometry grid module — anisotropic grid + 50% merge (S05-D1, D4)` |
| 4.4 | `proto3/geometry/recursive.py` + `decompose.py` 통합 — `recursive_progressive_per_family` + `auto_partition` high-level wrapper | `feat: geometry recursive + decompose wrapper (S05-D1, D4)` |
| 4.5 | `proto3/schema/geometry.py` — `GeometricPiece` + `Decomposition` dataclass + `to_dict/from_dict` 호환 | `feat: GeometricPiece + Decomposition schema (S05-D5)` |
| 4.6 | Algorithm tests — `test_geometry_lir/grid/recursive/decompose`. 핵심 stress test 1-2개 재현 (한글 자모 ㄱ + edge case triangle 정도) + 5 기존 fixture × auto_partition smoke | `feat: geometry tests (lir + grid + recursive + 6-fixture integration)` |
| 4.7 | 사선 fixture 추가 — `apartment_diagonal.json` (D1, 회전 ~20°) + `tests/fixture_matrix.py` 갱신 + `test_fixtures_render_smoke` 6 fixture 확장 | `feat: diagonal fixture (D1, S04 Def-1 resolved, S05-D7)` |
| 4.8 | `notebooks/step05_decomposition.ipynb` — 6 fixture × decomposition 시각화 (cell coloring by family_id) | `feat: step05 decomposition notebook (S05-D9)` |
| 4.9 | `D019` 정식 등록 (`000_Architecture_Decisions.md`) + **D006 amendment 텍스트 (atom_size 300mm + atom_inclusion_threshold 0.5 + min_atom_side/tiny_atom_area deprecated 명시)** + **Pipeline §8 numerical defaults 표 update** + Step 05 cleanup (Plan/Tracker 마무리, Progress Tracker close, merge --no-ff) | `docs: step05 cleanup + D019 D006 amendment (per-family proportional atom + 300mm)` |

실행 순서: 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 → 4.7 → 4.8 → 4.9 → merge --no-ff to main.

---

## 5. Deferred (명시적 비-목표)

| # | 항목 | 이유 | 처리 시점 |
|---|---|---|---|
| Def-1 | Stage 04 본격 통합 (`Stage 04 Region/Atom Decomposition` runtime stage as `proto3.stages.stage04_decompose.run()`) — RegionSet ↔ Decomposition 매핑 포함 | X2 scope split (S05-D6) | Step 07 |
| Def-2 | Stage 05 Graph Construction — cell adjacency graph (RegionGraph + AtomGraph) | Step 08 책임 (Pipeline §15) | Step 08 |
| Def-3 | Door-edge helper (door capability granularity, Pipeline §8 open issue) | cell adjacency graph 위에서 의미 있음 | Step 08 |
| Def-4 | v3.2 한계 A: family fragmentation dedupe | cosmetic only, coverage 영향 없음 | future (낮은 우선순위) |
| Def-5 | v3.2 한계 B: 45° floating-point edge case fix | rare (~0.17% gap), refactor 필요 | Step 07/08+ |
| Def-6 | v3.2 한계 D: junction cell irregular shape | cosmetic, adjacency graph 위에서 무관 | no action |
| Def-7 | v3.2 한계 E: LIR이 hole 무시 | apartment fixture는 hole 없음. mission 영향 미미 | future (`include_holes=True` 옵션) |
| Def-8 | v3.2 한계 F: same-theta region 분리 | room placement 단계 책임 | Step 09+ (room placement) |
| Def-9 | 곡선 footprint fixture | Stage 00 곡선 normalize 정식 D-decision은 Stage 13 output 시점에 의미 있음 | Step 07/13 |
| Def-10 | `from_dict()` multi-arm Union 명시적 raise | Step 04 §5 Def-10 그대로 | Step 05+ minor |
| Def-11 | Variable atom_size per region (F4 reconsider) | per-family proportional이 충분; 추가 variable size는 graph 복잡도만 늘림 | Step 07+ if fixtures show insufficient resolution |
| Def-12 | Stage 03 anchor projection 본격 구현 | apartment-only는 no-op. multi-floor (Target B+) 진입 시 | Step 14 |
| Def-13 | v12 zoning algorithm (`references/zone_v12.{py,md}`) 통합 — `proto3.zoning.*` 또는 `proto3.stages.stage04_decompose`에 land. v12 zone polygon → proto3 `Region` candidate 매핑. label assign은 Step 09 spine candidate에서. **Port 시 broad `except Exception` (e.g., `split_polygon`, `piece_aspect`) + post-hoc gap merge 디버깅 가독성을 위해 좁은 exception type으로 정리하고 gap merge는 명시적 invariant check로 대체.** | Step 07 (Region/Atom Decomposition 본격) 책임. v12 + v3.2가 짝 맞아 Stage 04 통합이 plug-and-play 수준. | Step 07 |
| **Def-14** | **Unit normalization layer (mm ↔ m) — Stage 00 또는 그 직후에서 BuildingInput (mm) → algorithm-friendly polygon (m) 변환.** atom output을 다시 mm로 복원하는 reverse 변환도 포함. | proto3 internal mm 정책 (D006) vs v3.2 algorithm m 가정 충돌 정형 해결. R-S05-7 ad-hoc 변환을 정식화. | Step 07 |

---

## 6. Risks

| ID | Risk | 완화책 |
|---|---|---|
| R-S05-1 | shapely C dependency (geos) install 시 OS 의존 — CI/dev 환경 설정 영향 | shapely는 wheel binaries로 대부분 OS pip install 즉시 작동. DoD-7로 install check. CI 환경 별도 설정 필요 시 추후 처리 |
| R-S05-2 | v3.2 한국어 주석 인코딩 — references/는 origin 보존, src/proto3/geometry/는 영어로 정리 | 4.2~4.4 commit 시 영어 주석으로 정리. references/는 그대로 |
| R-S05-3 | atom_size 600→300 amendment 시 backward-compat: 기존 fixture (Step 04) 좌표가 600mm 배수인지 확인 — 300mm 배수가 안 되면 boundary cell 더 많이 발생. | Step 04 fixture는 1000mm 단위라 300mm 배수 아니지만 v3.2 area-fraction (50% rule)이 boundary 흡수. Smoke test (DoD-4)로 6 fixture 검증. |
| R-S05-4 | 사선 fixture가 v3.2 algorithm으로 잘 작동 안 할 수도 — vertex 좌표가 mm 단위 정수면 OK | DoD-5에서 round-trip + decompose 검증 |
| R-S05-5 | numpy/shapely 새 deps로 dev install 회귀 — 기존 사용자 환경 영향 | DoD-7 (`python -m pip install -e .` 회귀 없음). shapely 2.0+ 은 stable. README/CHANGELOG 갱신은 Step 06+ |
| R-S05-6 | v3.2 한국어 식별자/주석을 영어로 옮길 때 의미 drift | 4.2~4.4 작업 시 `references/cell_v3_2.md` 영문 docstring로 직접 매핑 |
| **R-S05-7** | **Unit mismatch — proto3 schema (mm, D006) vs v3.2 algorithm (m). Direct fixture → algorithm 호출 시 LIR mask 폭증 (8000mm × 0.05 grid → 160000×120000 bool = 19 GB). 컴퓨터 hang 위험.** | §4.6 test 작업 중 발견. **§4.9 review followup #2**에서 `proto3.geometry.decompose.run()` mm-friendly wrapper 추가 (X3 pattern; v3.2 algorithm 그대로 보존 + on-entry mm→m / on-exit m→mm shapely.affinity.scale). test_geometry_decompose + notebook 모두 `run()` 사용으로 변경, inline `(x/1000, y/1000)` 제거. caller mm 직접 사용 가능. Stage 00 unit normalization layer (broader scope: BuildingInput→run dispatch, ContactGraph mm-aware door checks)는 Step 07 §5 Def-14에서 land. |

---

## 7. Next-Step linkage

Step 05 산출물:
- `proto3.geometry.decompose.auto_partition(footprint)` — Step 07이 호출.
- `proto3.geometry.{lir, grid, recursive}.*` — Step 07 (Decomposition 본격) + Step 08 (Graph) 도구.
- `proto3.schema.geometry.GeometricPiece + Decomposition` — Step 07이 RegionSet에 매핑.
- `apartment_diagonal.json` (D1) — Step 06+의 회귀 fixture.
- D019 (D006 amendment) — atom 정의 정형화.

[Step 06 Program Engine](000_Pipeline_Overview.md#L964): Stage 02 area gate land. R2 fixture 회로 작동. ProgramRequest dataclass 정형화. R-S03-2 palette mapping.

[Step 07 Decomposition](000_Pipeline_Overview.md#L965): `proto3.stages.stage04_decompose.run(building) → Decomposition` 통합. RegionSet ↔ GeometricPiece 매핑 (1:1, N:1, 1:N 가능성 본격 의논).

[Step 08 Graph](000_Pipeline_Overview.md#L966): cell adjacency graph (RegionGraph + AtomGraph). Door-edge capability. v3.2 §9 우선순위 1.

---

## 8. Branch / Commit strategy

- **Branch**: `step05-geometry-kernel` (이미 checkout됨, 2026-05-08)
- **Commits**: §4 work items 1:1 = 9 commits (4.1 ~ 4.9)
- **Close**: `git checkout main && git merge --no-ff step05-geometry-kernel && git branch -d step05-geometry-kernel && git push origin main` (D015)

---

## 9. 변경이력

| Date | Change |
|---|---|
| 2026-05-08 | Initial draft. §0~§8. 10 decisions (S05-D1 ~ S05-D10). 9 work items. 15 DoD. v3.2 algorithm 외부 도입 (refs origin: 사용자 외부 작업, 2026-05-08). X2 scope split (Step 05 algorithm only, Step 07 schema integration). M2 (Region/GeometricPiece 분리). |
| 2026-05-08 | S05-D3 명확화 — atom_size 600→300mm + atom_inclusion_threshold 0.5 신설 + min_atom_side/tiny_atom_area deprecation. R-S05-3 의미 변경 (위험이 아니라 backward-compat 검증). DoD-16 추가. 4.1에 RunConfig 코드 변경, 4.9에 D006/Pipeline §8 텍스트 amendment 분리. |
| 2026-05-08 | references 정리 — v12 zoning artifacts 추가 + 이름 통일 (`cell_v3_2.*` / `zone_v12.*` prefix). `12_compare.py` 삭제 (v11 모듈 의존, 실행 불가). 4 cell + 7 zone = 11 files. Def-13 신설 (v12 → Step 07). DoD-13 갱신 (cell + zone 다 origin 보존). |
| 2026-05-08 | §4.6 메모리 누수 발견 — pytest 시 RAM 45→93GB 이상 폭증 및 서버 꺼짐. Root cause: proto3 schema (mm) ↔ v3.2 algorithm (m) **단위 불일치** + LIR rasterize mask 폭발 (8000mm × 0.05 grid → 19GB bool array). matplotlib.Path 복귀 (v3.2 원본; matplotlib 정식 dep 추가). test_geometry_decompose에 inline mm→m 변환. **R-S05-7 신설** (unit mismatch); **Def-14 추가** (Step 07 unit normalization layer). |
| 2026-05-08 | Step 05 close. 9 work-item commits + 1 chore (refs rename) + 1 review-fix (matplotlib + unit) on `step05-geometry-kernel`. **80 pytest passed**. D019 (D006 amendment) + H013 정식 등록. Pipeline §8 mirror update. RunConfig 코드 land (atom_size 300mm, atom_inclusion_threshold 0.5; deprecated min_atom_side/tiny_atom_area kept for backward-compat). 모든 DoD [x] except DoD-14 [~] (merge 사용자 확인 대기). |
| 2026-05-08 | merged to main (`7064132`). DoD-14 [x]. |
| 2026-05-08 | review followup #1 (post-merge cleanup) — Tracker 헤더 dedupe + "pending merge" → "merged" 표기 / Last updated 2026-05-07 → 2026-05-08 / test_fixtures_roundtrip docstring "5 → 6 fixtures" / D019/H013 tiny_atom_area_m2 deprecated 표기 정확화 (RunConfig에 없던 conceptual default였음 명시) / region_atom.AtomSet 주석 D019 area-fraction 기반으로 redirect / test_geometry_decompose D1 추가. 81 passed. main 직접 commit `24223fa`. |
| 2026-05-08 | review followup #2 — `proto3.geometry.decompose.run()` mm-friendly wrapper 추가 (X3 pattern). v3.2 algorithm `auto_partition()` 그대로 origin 보존 + 새 `run(footprint_mm)`이 mm↔m 변환 책임. R-S05-7 mitigation 갱신: caller (test, notebook) mm 직접 사용, inline `(x/1000)` 제거. test_geometry_decompose + step05_decomposition notebook 모두 `run()` 사용으로 변경. **82 passed** (test_run_output_in_mm 신규). |
