# 006 Step 06 — Program & Domain Constraint Engine Plan

Status: Completed (pending merge)
Started: 2026-05-09
Completed: 2026-05-09
Branch: `step06-program-constraint-engine`
Companion tracker: [006_Step06_ProgramConstraintEngine_Tracker.md](006_Step06_ProgramConstraintEngine_Tracker.md)

---

## 0. Purpose

Step 06 = "Program & Domain Constraint Engine" per [Pipeline Overview §15](000_Pipeline_Overview.md#L967). 산출물 7가지:

1. **`ProgramRequest` dataclass 정형화** — `BuildingInput.program_request: dict` 를 typed dataclass 로. `spaces: list[SpaceUnitSpec]` 만 typed (슬림). Step 04 Def-6 결산.
2. **`TargetRules` dataclass + 외부 JSON config + `rules_loader` + 단일 generic `TargetAdapter`** — Stage 02 게이트가 사용할 모든 도메인 default 값을 proto3 패키지 *내* `src/proto3/data/target_rules/apartment.json` 으로 분리. **단일 concrete `TargetAdapter` 클래스가 모든 typology 처리** (S06-D22, §4.3a) — typology 정체성은 JSON `target_type` 필드. `ApartmentAdapter` 같은 per-typology 클래스 없음. `rules_path: Path` required argument + `DEFAULT_APARTMENT_RULES_PATH` 상수 export. 외부 scan-to-BIM 파이프라인은 자기 json 만들어 path swap. 새 typology = JSON + dispatch 한 줄. Step 04 Def-11 결산.
3. **Role Literal + 미지값 hard fail** — `SpaceUnitSpec.role: Role` strict Literal. 미지값은 `from_dict` deserialize / Stage 01 / `viz.palette` 세 곳에서 fail-loud. R-S03-2 / Step 04 Def-7 / review #12 결산.
4. **Stage 01 본격화 — program 정보 full 보존** — Stage 01 이 `SpaceUnitSpec` 의 모든 필드 (`name`, `role`, `required`, `min_area_m2`, `min_dimension_mm`) 를 보존, None min_area_m2 → role default fill, duplicate `name` / unknown `role` / 잘못된 type → ProgramInstantiationFailure. Step 04 frame 교체.
5. **Stage 02 Domain Feasibility Gate 본격화** — **fail-only** gate (D020 amendment, repair → Stage 12). active gates 3개 (area + dim + multi-floor placeholder); `check_access_schema` 함수는 land 하지만 Stage 02 호출 X (dormant scaffold, Step 09-10 활성화). `proto3.constraints.gates` 모듈 (4 pure functions). area gate = `total_required_area ≤ gross_footprint × density_factor` (D024 — anchor-aware 정밀 검증은 Stage 11/Step 12). **required-only** 합산 (D023). dim = bbox-level. **single-floor 가정** (D024, multi-floor = Step 14/Def-8). `DomainGateFailure` 부모 + `AreaGateFailure` / `DimGateFailure` / `AccessSchemaFailure` 자식. R2 fixture 회로 작동 (review #2). Pipeline §9.10 갱신: cardinality check 제거 (Stage 01 책임 D004), repair 출력 제거, single-floor 가정 명시.
6. **`RunConfig` value-range validation + dead-config wiring** — `atom_size_mm > 0`, `0 < atom_inclusion_threshold ≤ 1`, `door_min_boundary_mm ≥ 0`, `min_atom_side_mm > 0` 를 `__post_init__` 에서 검증 (review #11). 더불어 `atom_inclusion_threshold` 는 현재 `recursive.py` 에 0.5 hardcoded — `decompose.run()` 시그니처에 threshold 전파해서 wiring 살림 (외부 review #3).
7. **Fail-loud 정책 일관 적용** — `viz.palette.role_to_palette_key` 미지 role → ValueError (review #12), `viz.svg.render(...)` 의 unsupported kwarg (atoms/regions/spine) → ValueError (Step 07 본격 territory 진입 전 strict; 외부 review #11), `TargetAdapter.load_fixture` 가 fixture target_type 불일치 시 fail (외부 review #8).

Step 06 종료 시점에 Stage 01 + Stage 02 가 D004 / D005 / D012 정신을 완전히 만족, proto3 도메인 정보가 *engine ↔ data* 4-layer 분리 (S06-D17), fail-loud 정책 일관 적용된 상태.

---

## 1. Definition of Done

| # | 조건 | 검증 방법 |
|---|---|---|
| DoD-1 | `proto3.schema.program.ProgramRequest` dataclass + `BuildingInput.program_request: ProgramRequest` 타입 변경 + `from_dict` deserialize OK + 잘못된 spaces type (예: `"not_a_list"`) → ValueError | unit test |
| DoD-2 | `proto3.schema.program.Role = Literal["public","private","service","wet","hub","corridor"]` + `SpaceUnitSpec.role: Role` 좁힘 + 미지값 deserialize 시 fail | unit test |
| DoD-3 | `proto3.target.TargetRules` dataclass — 모든 필드 required (default 없음, S06-D5 정신 일관) | import test |
| DoD-4 | `src/proto3/data/target_rules/apartment.json` 신규 + `src/proto3/data/target_rules/README.md` (출처 + Future work) + `src/proto3/data/__init__.py` + `src/proto3/data/target_rules/__init__.py` (namespace package) | inspection |
| DoD-5 | `pyproject.toml` 에 `include-package-data = true` 또는 `[tool.setuptools.package-data]` 추가 — `proto3.data.target_rules` json/md 가 wheel/sdist 에 포함 | install check (wheel 빌드 후 archive 안에 json 존재) |
| DoD-6 | `proto3.target.rules_loader.load_target_rules(path) -> TargetRules` — json 로드 + 필드 누락 / 타입 mismatch / unknown role / 음수 / threshold 범위 외 시 ValueError | unit test |
| DoD-7 | `TargetAdapter(rules_path: Path)` — `rules_path` required argument + `DEFAULT_APARTMENT_RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "target_rules" / "apartment.json"` 상수 export. §4.3a 이후 `target_type` property = JSON `target_type` 필드 (S06-D22) | unit test |
| DoD-8 | `TargetAdapter.load_fixture(path)` — fixture 의 `target_type` 이 adapter 자기 `target_type` 과 다르면 ValueError (review #8, S06-D15) | unit test |
| DoD-9 | `stages/stage00_load._DEFAULT_ADAPTERS` 가 default path 사용 (`{"apartment": TargetAdapter(DEFAULT_APARTMENT_RULES_PATH)}`); 모든 다른 호출 site 는 명시적 path | regression test |
| DoD-10 | `proto3.constraints.gates` 모듈 — `check_min_area`, `check_min_dim`, `check_access_schema`, `check_multi_floor_feasibility` (4 pure functions) | import test |
| DoD-11 | `proto3.schema.validation.DomainGateFailure` 부모 + `AreaGateFailure` / `DimGateFailure` / `AccessSchemaFailure` 자식 (모두 `failure: FailureRecord` 보유, S04-D11 패턴) | import test |
| DoD-12 | `proto3.stages.stage02_gate.run(...)` — gates 호출 + DomainGateFailure 계열 raise | unit test |
| DoD-13 | Stage 01 본격화: ProgramRequest 입력 + `SpaceUnitSpec` 모든 필드 보존 (`required`, `min_area_m2`, `min_dimension_mm`) + None min_area_m2 → role default fill + duplicate `name` / unknown `role` / type mismatch → `ProgramInstantiationFailure` (외부 review #4) | unit test |
| DoD-14 | `RunConfig.__post_init__` value-range validation 추가 (review #11) | unit test |
| DoD-15 | `decompose.run(footprint_mm, target_cell_size_m=..., atom_inclusion_threshold=...)` 시그니처 확장 + `recursive.py` 의 0.5 hardcoded 를 인자로 전파 (review #3) | unit test |
| DoD-16 | `proto3.viz.palette.role_to_palette_key` — 미지 role 시 ValueError (review #12) | unit test |
| DoD-17 | `proto3.viz.svg.render(...)` — 미지원 kwarg (atoms / regions / spine) 받으면 ValueError (Step 07 territory 침범 전 strict, 외부 review #11) | unit test |
| DoD-18 | R2 fixture (`apartment_too_small`)가 Stage 02 에서 `AreaGateFailure` 발생 — 회로 작동 | regression test |
| DoD-19 | A1/A2/B1/D1 fixture는 Stage 02 통과 (false-reject 없음) | regression test |
| DoD-20 | `notebooks/step06_program_gate_overview.ipynb` — fixture × gate matrix 표 + area budget bar chart, 실행 시 `outputs/notebooks/step06_program_gate_overview/<run_id>/` 산출 | notebook 실행 |
| DoD-21 | `pytest -q` 통과 (현재 82 + Step 06 신규) | pytest |
| DoD-22 | `python -m pip install -e .` 회귀 없음 — 신규 runtime deps 0개 (json, importlib.resources 모두 stdlib) | install check |
| DoD-23 | `000_Pipeline_Overview.md §9.10` Stage 02 outputs 항목 갱신 — `ProgramInstantiationFailure` 단일 → `DomainGateFailure(AreaGateFailure / DimGateFailure / AccessSchemaFailure)` (외부 review #7) | git diff |
| DoD-24 | `proto3.schema.__init__` re-export 갱신 — `GeometricPiece`, `Decomposition` 추가 (Step 05 잔여, 외부 review #12) + `tests/test_smoke.py` 22 → 24 갱신 | git diff |
| DoD-25 | Step 05 docs (`005_Step05_*.md`) → `legacy/step05/` via `git mv` + `005_Step05_GeometryKernel_Plan.md` header `Completed (pending merge)` → `Completed (merged 7064132)` (외부 review #15) | git ls-files |
| DoD-26 | `000_Progress_Tracker.md` 4.1 commit 에서 "Step 06 In progress" 갱신 + Tracker stale §4 ("Step 04 close...") + Last updated 2026-05-07 → 2026-05-09 cleanup (review #14 잔여) | git diff |
| DoD-27 | §4 commits 모두 `step06-program-constraint-engine` branch + `git merge --no-ff` to main + branch 삭제 (D015) | git log |
| DoD-28 | Architecture Decisions 에 D020 (Stage 02 design + 4-layer rules 분리) + D021 (TargetRules + 외부 JSON config) 추가 + D006 cross-link 보존 | inspection |

---

## 2. 결정 기록

| ID | 결정 | 근거 |
|---|---|---|
| **S06-D1** | Step 06 scope = "정상" 폭. ProgramRequest dataclass + TargetRules + 외부 JSON config + Role Literal + Stage 01 본격화 + Stage 02 gate 4개 + RunConfig validation + viz/render fail-loud + adapter mismatch 검사 + Pipeline §9.10 갱신 + schema __init__/test_smoke 잔여 한 묶음. 9 work item | review #2/#11/#12 + Step 04 Def-6/7/11 + R-S03-2 + 외부 review 16 항목이 자연스럽게 한 묶음 |
| **S06-D2** | density factor = **0.85** (apartment 세대 내부 효율: 벽 + 세대내 동선 ≈ 15% 깎음) | proto3 footprint = 한 세대 외곽선이라 코어/공용복도는 footprint 밖. 한국 아파트 전용률 0.7 그대로 쓰면 over-discount. 0.85 = architectural rule of thumb. R2 는 어느 값에서도 fail (sensitive 하지 않음). 논문 framing: "minimum infeasibility 차단, 현실적 다양성 보존" (D005 + 학습데이터 정합성) |
| **S06-D3** | role 별 default min_area_m2 = 중간안 (B). public 12 / service 5 / private 7 / wet 3 / hub 2 / corridor 0 | 한국「최저주거기준」(legal floor) + Neufert *Architects' Data* (인체공학 derivation) + 한국 LH/SH 표준 평면 (empirical lower-quartile) 절충 |
| **S06-D4** | **proto3 도메인 default 값 위치 = `src/proto3/data/target_rules/apartment.json`** (proto3 패키지 *내* 데이터 디렉토리). importlib.resources / `Path(__file__)` 친화. `src/proto3/data/__init__.py` + `src/proto3/data/target_rules/__init__.py` namespace package. 출처는 `src/proto3/data/target_rules/README.md` 에 (json 주석 미지원). pyproject.toml 에 `package-data` 추가해서 wheel/sdist 에 포함 | (1) "코드 ↔ 데이터" 분리 가치관 보존 — `data/` 별 디렉토리. (2) editable install + wheel 둘 다 안전 — `Path(__file__).resolve().parent.parent / "data" / "target_rules" / "apartment.json"` 으로 절대 경로 resolve. (3) repo root `config/` 안 함 — pyproject `[tool.setuptools]` 에 src 만 packaging 잡혀 있어 wheel 시 깨짐 (외부 review #6). (4) 외부 파이프라인은 여전히 자기 path 던짐. (5) JSON = stdlib → 0 dep |
| **S06-D5** | `TargetAdapter(rules_path: Path)` — **rules_path required argument**. `None` 허용 안 함. `proto3.target.DEFAULT_APARTMENT_RULES_PATH` 상수만 export. 한 가지 예외: `stage00_load._DEFAULT_ADAPTERS` 가 default path 사용 (DoD-9). §4.3a 에서 `ApartmentAdapter` → `TargetAdapter` (단일 generic, S06-D22) | 사용자 가치관 (대화 2026-05-09): "default 자동 깔림 지양". 모든 호출 site 가 어떤 rules path 쓰는지 코드에 박힘. silent fallback 없음 (D004/D005 fail-loud 정신과 일관) |
| **S06-D6** | Failure 계층: `DomainGateFailure(Exception)` 부모 + `AreaGateFailure` / `DimGateFailure` / `AccessSchemaFailure` 자식. 모두 내부에 `FailureRecord` 보관 (S04-D11 패턴). Pipeline §9.10 Stage 02 outputs 항목도 동시 갱신 — **fail-only 로 변경** (repair 출력 제거; D020 amendment). repair 는 Stage 12 territory. Stage 02 cardinality check 항목도 제거 (Stage 01 책임, D004) | R2 fixture metadata `expected_failure: "AreaGateFailure"` 와 일치. 게이트별/공통 catch 둘 다 가능. 기존 `ProgramInstantiationFailure` 는 Stage 01 cardinality / role-validity 전용 유지. Pipeline §9.10 갱신은 외부 review #7 + 두 번째 review (#2/#3) |
| **S06-D7** | `SpaceUnitSpec.min_area_m2` 가 None 인 경우 default fill 시점 = **Stage 01 instantiation**. ProgramInstance 는 concrete 상태로 produce. fill 값 source = `TargetRules.default_min_area_m2[role]` (외부 JSON 에서 옴; rules_loader 가 6 role full map 보장 — D023 cross-link). Stage 01 은 추가로 `required` / `min_dimension_mm` / `preferred_area_m2` 도 보존하고, duplicate `name` / unknown `role` / type mismatch 시 ProgramInstantiationFailure (외부 review #4). **cardinality 비교는 `required=True` 만** (D023) — optional spaces 는 cardinality 충족 못시킴 | D004 ("ProgramInstance is the source of cardinality") 정신과 일관. Step 04 Stage 01 frame 은 dict→`{name, role}` 만 추출했음 (외부 review #4). 두 번째 review (#1) 의 required/optional 정책 결함 — D023 으로 명시 |
| **S06-D8** | `ProgramRequest` dataclass = 슬림. `spaces: list[SpaceUnitSpec]` 만 typed. ClusterSpec / AccessPolicy / area_budget 미포함 (Step 09-10 territory, Def-9) | Cluster/AccessPolicy 본격 인스턴스화 layer 는 Step 09–10. Step 06 책임 lean. AccessPolicy schema 검증 회로 (`check_access_schema` gate) 는 unit test 까지만 — 실제 fixture 사용은 Step 09-10 |
| **S06-D9** | `TargetRules` dataclass 정형화. 필드: `min_cardinality: dict[Role, int]`, `default_min_area_m2: dict[Role, float]`, `density_factor: float`, `requires_single_floor: bool`. 모든 필드 required (default 없음) | Stage 02 게이트가 dict shape 을 silent 신뢰하던 Step 04 frame 을 typed contract 로 교체. JSON 누락 시 silent fallback 발생 → S06-D5 fail-loud 정신과 충돌 → default 두지 않음 |
| **S06-D10** | `Role = Literal["public","private","service","wet","hub","corridor"]` strict. 미지 role hard fail 위치: (a) `from_dict` deserialize 시 D017 Literal validation, (b) Stage 01 instantiation, (c) `viz.palette.role_to_palette_key` ValueError | D004 / D005 ("constraints as gates, fail loud") 정신. 새 role 필요 시 Literal 확장 = 명시적 schema diff |
| **S06-D11** | viz / render fail-loud 통일 정책: `palette.role_to_palette_key` 미지 role → ValueError (review #12), `svg.render(...)` 미지원 kwarg (atoms/regions/spine) → ValueError (외부 review #11). 실제 atoms/regions/spine render 는 Step 07 territory | Step 06 내내 fail-loud 정신을 일관 박는 작업. `render()` 가 atoms 받았는데 무시하는 건 D005 silent-fail 위반. Step 07 본격 atoms render 시점에 ValueError 제거 후 정상 처리 추가 |
| **S06-D12** | min-dimension gate 깊이 = bbox-level 만 ("footprint bounding box 의 짧은 변 < 가장 큰 룸 min_dimension_mm" 일 때만 fail). LIR 활용 정밀 검증은 Step 12 (Stage 11 post-growth validation) 으로 deferred | Stage 02 는 Stage 04 (decomposition) 이전이라 LIR 결과 없음. Stage 02 정의 ("obvious impossibility 만 차단", Pipeline §9.10) 와 일관 |
| **S06-D13** | 게이트 함수는 `proto3.constraints.gates` 모듈에 pure function 으로 분리. Stage 02 만 호출. Stage 11/13 binding 은 **Step 12** territory | `proto3.schema.validation` 은 exception/dataclass 흐름 전용 유지. gates = pure transformation. Pipeline §15 Step 06 row "Stage 11/13 validation" = 함수 시그니처 까지, 호출 자체는 Step 12 |
| **S06-D14** | `RunConfig.__post_init__` value-range validation (`atom_size_mm > 0`, `0 < atom_inclusion_threshold ≤ 1`, `door_min_boundary_mm ≥ 0`, `min_atom_side_mm > 0`). 더불어 `atom_inclusion_threshold` dead config wiring — `decompose.run()` 시그니처에 threshold 인자 추가 + `recursive.py` 0.5 hardcoded 제거 (외부 review #3) | review #11 결산 + 외부 review #3 흡수. config 값 ↔ 알고리즘 동작 일관 (ablation/외부 override 시 효과). dataclass-first (D012) 일관 |
| **S06-D15** | `TargetAdapter.load_fixture(path)` — fixture `target_type != self._rules.target_type` 일 때 ValueError (외부 review #8). 기존 `stage00_load` 의 target_consistency 는 RunConfig 있을 때만 작동했음 | adapter 가 자기 영역 fixture 만 받도록 자체 검사. RunConfig 없는 경로 (직접 adapter 호출) 에서도 mismatch 잡힘. fail-loud 일관 |
| **S06-D16** | Demo notebook = `step06_program_gate_overview.ipynb`. fixture × gate matrix 표 (각 fixture 의 어느 게이트에서 fail/pass) + per-fixture area budget bar chart (Σ min_area vs footprint × density). matplotlib + tabular | 메모리 visualization default. R2 가 빨갛게 빠지는 영상이 Step 06 의 가장 큰 가시적 변화 |
| **S06-D17** | **proto3 도메인 정보의 4-layer 분리.** L1 invariant (Role enum, D004/D005) + L2 baseline (apartment.json) 은 proto3 영역, L3 프로젝트 override 는 외부 파이프라인이 자기 json 만들어 `rules_path=...` 로 전달, L4 외부 own metadata (학습 데이터셋 통계 등) 는 proto3 무관. **부분 override merge 미지원** (Def-1) — 외부가 base json 통째 복사 후 수정 | proto3 = engine, 외부 데이터 분리. 외부 통합 시 코드 변경 0. 부분 merge 회피 = drift 없음 + debugging 단순 + edge case 회피 |
| **S06-D22** | **Single generic `TargetAdapter` + 3-layer typology extensibility** (§4.3a). Per-typology adapter 클래스 (ApartmentAdapter, HotelAdapter, ...) deliberately absent. typology 정체성 = JSON `target_type` 필드 (자기 식별). `TargetRules` 에 `target_type: TargetType` 필드 추가. 새 typology 추가 = JSON + `_DEFAULT_ADAPTERS` 한 줄. 미래 logic-different typology = strategy registry (L2 plugin, Step 09 도입 예정). README (`src/proto3/data/target_rules/README.md`) 에 3-layer model + mission scope (enclosed building only) 명시. **"새 typology = JSON + 한 줄" boundary** — 기존 5 TargetType + 6 Role grid 안에서만. grid 밖 typology (예: dormitory) 또는 새 role (예: warehouse 의 `storage`/`loading_dock`) 필요 시 Python schema diff 1-2줄 함께. "data-only" 약속이 무한 generic 의미가 아님 (두 번째 review #5) | typology 4개 (B/C/D/E) 본격 진입 확정 (사용자 답 2026-05-09) → per-typology 클래스 boilerplate (4 × ~25줄) 회피. proto3 = engine, 외부 데이터 분리. typology별 다른 logic 은 typology 분기 아닌 strategy registry 로 (typology-agnostic 함수, hotel/large-office 같은 strategy 공유). Stage 코드는 `if target_type == "hotel"` 같은 분기 절대 가지지 않음. 교량/지하철 같은 다른 도메인은 proto3 mission scope 밖 (별도 engine) |
| **S06-D23** | **Required-only cardinality / area summation** (D023). Stage 01 cardinality `Counter(u.role for u in space_units if u.required)`; Stage 02 area sum `sum(u.min_area_m2 for u in space_units if u.required)`. optional spaces 는 cardinality 충족 안 시키고 area 합산에 안 들어감. optional repair (drop) policy = Stage 12 영역 (D020 fail-only 와 일관) | 두 번째 review #1 — optional bedroom 이 required bedroom count 충족시키는 silent bug + optional 합산으로 area gate false-reject 위험. D004/D005 fail-loud 정신 |
| **S06-D24** | **Stage 02 area gate boundary** (두 번째 review #7/#8) — area gate = `total_required_area ≤ gross_footprint_area × density_factor`. **gross** footprint (anchor/void/core 빠짐 검증 X — Stage 03 이전 단계). anchor-aware 정밀 검증은 Step 12 (Stage 11 post-growth). **single-floor 가정** — `len(building.floors) == 1` (apartment). multi-floor 일반화 = Step 14 (Def-8) | 솔직한 boundary 명시. 미래 anchor 진입 / multi-floor 진입 시 정직한 path. 현재 apartment fixture 는 anchor empty + single floor 라 OK |
| **S06-D18** | **Future work 명시**: (a) 부분 override merge 지원, (b) 법규/논거 maintenance, (c) density factor + min_area sensitivity ablation (논문 supplementary) | AiC 논문 framing: "first-pass commitments per Target type, sensitivity reportable". 사용자 요청 (2026-05-09) |

D-record cross-link: Architecture Decisions 에 D020 (Stage 02 design + 4-layer rules 분리) + D021 (TargetRules + 외부 JSON config) 신설. D006 (region/atom dual layer) cross-reference.

---

## 3. Directory structure (Step 06 완료 시)

```text
src/proto3/
├── __init__.py
├── config.py                          # +__post_init__ value validation (S06-D14)
├── debug.py
├── data/                              ← 신규 (proto3 패키지 내 데이터 디렉토리, S06-D4)
│   ├── __init__.py                    # 빈 (namespace package)
│   └── target_rules/
│       ├── __init__.py                # 빈
│       ├── apartment.json             # 모든 도메인 default 값 (S06-D2, D3)
│       └── README.md                  # 출처 (Layer A/B/D references) + Future work
├── schema/
│   ├── __init__.py                    # +GeometricPiece, +Decomposition (DoD-24, 외부 review #12)
│   ├── input.py                       # BuildingInput.program_request: dict → ProgramRequest (S06-D8)
│   ├── program.py                     # +Role Literal, +ProgramRequest dataclass, SpaceUnitSpec.role: Role
│   ├── validation.py                  # +DomainGateFailure / Area / Dim / AccessSchema (S06-D6)
│   ├── serialize.py                   # (Literal validation 강화 — D017 자연 결과)
│   └── (나머지 그대로)
├── target/
│   ├── __init__.py
│   ├── base.py                        # +TargetRules dataclass (S06-D9)
│   ├── adapter.py                     # 신규 (§4.3a) — 단일 generic TargetAdapter + DEFAULT_APARTMENT_RULES_PATH + load_fixture target_type 검사 (S06-D5, D15, D22)
│   └── rules_loader.py                # 신규 — load_target_rules(path) -> TargetRules (S06-D4)
├── stages/
│   ├── stage00_load.py                # 변경 — adapter=None 분기에서 DEFAULT_APARTMENT_RULES_PATH (DoD-9)
│   ├── stage01_program.py             # 본격화 — ProgramRequest 입력 + 모든 SpaceUnitSpec 필드 보존 + role default fill + dup name / unknown role / type mismatch fail (S06-D7, D10)
│   └── stage02_gate.py                # 신규 (S06-D6, D12)
├── constraints/                       # 신규 모듈
│   ├── __init__.py
│   └── gates.py                       # 4 pure functions (S06-D13)
├── viz/
│   ├── palette.py                     # 미지 role ValueError (S06-D11)
│   ├── svg.py                         # render(...) 미지원 kwarg ValueError (S06-D11)
│   └── (나머지 그대로)
└── geometry/
    ├── decompose.py                   # run() 시그니처에 atom_inclusion_threshold 추가 (DoD-15)
    ├── recursive.py                   # 0.5 hardcoded → 인자 (DoD-15)
    └── (나머지 그대로)

pyproject.toml                          # +include-package-data 또는 [tool.setuptools.package-data] (DoD-5)

fixtures/                               # 변경 없음

tests/
├── test_smoke.py                      # 22 → 24 (DoD-24)
├── test_program_request.py            # 신규
├── test_target_rules.py               # 신규
├── test_run_config.py                 # 신규
├── test_constraints_gates.py          # 신규
├── test_stage01_program.py            # 변경 — 모든 필드 보존 / dup name / unknown role / type mismatch
├── test_stage02_gate.py               # 신규 — 4 게이트 + R2 fail
├── test_palette.py                    # 신규 또는 변경 — unknown role ValueError
├── test_render_strict.py              # 신규 — render() unsupported kwarg ValueError
├── test_apartment_adapter.py          # 변경 — load_fixture target_type 검사
├── test_decompose_threshold.py        # 신규 — atom_inclusion_threshold wiring
└── test_fixtures_roundtrip.py         # 변경 — ProgramRequest deserialize 확인

notebooks/
└── step06_program_gate_overview.ipynb # 신규 (S06-D16)

legacy/step05/
├── 005_Step05_GeometryKernel_Plan.md  # header `Completed (pending merge)` → `Completed (merged 7064132)` (DoD-25)
└── 005_Step05_GeometryKernel_Tracker.md
```

### 3.1 `src/proto3/data/target_rules/apartment.json` 명세

```json
{
  "density_factor": 0.85,
  "requires_single_floor": true,
  "min_cardinality": {
    "public": 1,
    "private": 1,
    "wet": 1
  },
  "default_min_area_m2": {
    "public":   12.0,
    "service":   5.0,
    "private":   7.0,
    "wet":       3.0,
    "hub":       2.0,
    "corridor":  0.0
  }
}
```

JSON 주석 미지원 → 출처는 `src/proto3/data/target_rules/README.md` 별도. Sources: Neufert *Architects' Data* / 「최저주거기준」/ LH-SH 표준평면 / proto3 D005 — Layer A/B/D 명시 + Future work (외부 config 외부화는 already done, 부분 merge / 법규 maintenance / sensitivity ablation 만 deferred).

### 3.2 `proto3.target.rules_loader` 시그니처

```python
def load_target_rules(path: Path) -> TargetRules:
    """JSON 파일 로드 + 검증 + TargetRules 반환.
    
    검증:
    - 모든 필드 존재
    - density_factor: 0 < x ≤ 1
    - default_min_area_m2 / min_cardinality 의 모든 키 ∈ Role Literal
    - 모든 area / cardinality ≥ 0
    
    실패 시 ValueError(상세 메시지).
    """
```

### 3.3 `DEFAULT_APARTMENT_RULES_PATH` 명세

```python
# src/proto3/target/apartment.py
from pathlib import Path

DEFAULT_APARTMENT_RULES_PATH: Path = (
    Path(__file__).resolve().parent.parent / "data" / "target_rules" / "apartment.json"
)
```

editable install 시 즉시 작동. wheel 시 setuptools 가 `package-data` 로 json 포함 → site-packages 경로에 풀려 `Path(__file__)` resolve 정상.

---

## 4. Work items

[Tracker §1](006_Step06_ProgramConstraintEngine_Tracker.md) 와 1:1 매칭. **각 항목 = 1 commit**.

| # | 작업 | commit msg |
|---|---|---|
| 4.1 | Step 05 docs `legacy/step05/` archive (header `Completed (merged 7064132)` 갱신) + Plan/Tracker 추가 + `src/proto3/constraints/` & `src/proto3/data/target_rules/` 모듈 scaffold + `proto3.schema.__init__` 에 `GeometricPiece`/`Decomposition` 추가 + `tests/test_smoke.py` 22→24 + Progress Tracker §1/§4/§6 "Step 06 In progress" + Tracker stale §4 + Last updated 2026-05-07 → 2026-05-09 (review #14 잔여) + Architecture Decisions D020/D021 placeholder | `chore: archive step05 + scaffold step06 module + step05 schema export cleanup` |
| 4.2 | `proto3.schema.program` — `Role` Literal, `ProgramRequest` dataclass (spaces only), `SpaceUnitSpec.role: Role`. `BuildingInput.program_request: dict → ProgramRequest` 타입 교체. `proto3.schema.serialize` 에서 `list[T]` 타입 검증 강화 (ProgramRequest.spaces 영역 한정 — 일반화는 Def-7 Step 08). unit tests | `feat: ProgramRequest dataclass + Role literal + spaces strict deserialize (S06-D8, D10)` |
| 4.3 | `src/proto3/data/target_rules/apartment.json` + README.md 신규 (S06-D2, D3, D4). `pyproject.toml` 에 package-data 추가 (DoD-5). `proto3.target.base.TargetRules` dataclass (S06-D9). `proto3.target.rules_loader.load_target_rules` (S06-D4). `proto3.target.apartment.ApartmentAdapter(rules_path)` required + `DEFAULT_APARTMENT_RULES_PATH` (S06-D5) + `load_fixture` target_type 검사 (S06-D15). `stage00_load.run` adapter=None 분기 갱신 (DoD-9). unit tests. **§4.3a 에서 `ApartmentAdapter` → 단일 generic `TargetAdapter` 로 일반화 (S06-D22)** | `feat: TargetRules + apartment.json data package + adapter target check (S06-D4, D5, D9, D15, D17)` |
| 4.3a | **Generic adapter reform** (S06-D22): `proto3.target.apartment.py` 폐기 (git rm), `proto3.target.adapter.py` 신규 (단일 `TargetAdapter` concrete class), `TargetRules` 에 `target_type: TargetType` 필드 추가, `apartment.json` 에 `"target_type": "apartment"` 추가, `rules_loader` target_type 검증 추가, `stage00_load._ADAPTERS` → `_DEFAULT_ADAPTERS` (instance dict, single generic class). README 대폭 강화 (3-layer model + mission scope). D021/D022 본문 갱신. tests 갱신 (TargetAdapter 단일 class). `.gitignore` 에 `build/` + `dist/` 추가 | `refactor: generic TargetAdapter + JSON self-describing typology + 3-layer extensibility (S06-D5, D17, D22 + .gitignore build/dist)` |
| 4.4 | `proto3.schema.validation` — `DomainGateFailure` 부모 + 3 자식 (S06-D6). `proto3.constraints.gates` 모듈 — 4 pure functions: `check_min_area`, `check_min_dim`, `check_access_schema`, `check_multi_floor_feasibility` (S06-D12, D13). 각 게이트 unit tests | `feat: DomainGateFailure hierarchy + gates module (S06-D6, D12, D13)` |
| 4.5 | `proto3.stages.stage01_program` 본격화 — ProgramRequest 입력 + `SpaceUnitSpec` 모든 필드 보존 (`required`/`min_area_m2`/`min_dimension_mm`/`preferred_area_m2`) + None min_area_m2 → role default fill + duplicate `name` / unknown `role` / type mismatch → ProgramInstantiationFailure (S06-D7, D10, 외부 review #4). test_stage01_program 갱신 | `feat: stage 01 full program preservation + dup/unknown/type guards (S06-D7, D10)` |
| 4.6 | `proto3.stages.stage02_gate` 신규 — 4 게이트 호출 + DomainGateFailure 계열 raise. `000_Pipeline_Overview.md §9.10` Stage 02 outputs 갱신 (외부 review #7). R2 → AreaGateFailure 회로 + A1/A2/B1/D1 통과 확인 | `feat: stage 02 gate + Pipeline §9.10 update + R2 regression (S06-D6, review #2, #7)` |
| 4.7 | `proto3.config.RunConfig.__post_init__` value-range validation (S06-D14). `decompose.run()` 시그니처에 `atom_inclusion_threshold` 추가 + `recursive.py` 0.5 hardcoded 제거 (외부 review #3). `proto3.viz.palette.role_to_palette_key` 미지 role ValueError (S06-D11). `proto3.viz.svg.render` 미지원 kwarg ValueError (S06-D11, 외부 review #11). 각 영역 unit tests | `feat: fail-loud sweep — RunConfig + threshold wiring + palette + render strict (S06-D11, D14, review #3, #11, #12)` |
| 4.8 | `notebooks/step06_program_gate_overview.ipynb` — fixture × gate matrix + area budget bar chart (S06-D16) | `feat: step06 program gate overview notebook (S06-D16)` |
| 4.9 | Step 06 cleanup: Plan/Tracker close 갱신, `000_Progress_Tracker.md` "Step 06 → Done", D020/D021 본문 finalize, merge --no-ff 후 branch 삭제 | `docs: step06 cleanup (Plan/Tracker, Progress Tracker, D020/D021)` |

실행 순서: 4.1 → 4.2 → 4.3 → **4.3a** → 4.4 → 4.5 → 4.6 → 4.7 → 4.8 → 4.9 → (Step 종료) merge --no-ff to main.

---

## 5. Deferred (명시적 비-목표)

| # | 항목 | 이유 | 처리 시점 |
|---|---|---|---|
| Def-1 | **부분 override merge** 지원 (S06-D17, D18) | 통째 swap 의 drift / 재현성 / debugging 장점 우선. 부분 merge 의 nested dict edge case 회피 | 외부 파이프라인 통합 후 실수요 시 |
| Def-2 | **법규/논거 maintenance** — 한국 「최저주거기준」 개정 / 다른 국가 typology / fixture 다양화 시 default 재검토 (S06-D18) | first-pass commitments | fixtures 다양화 시 (Target B/C/D/E) |
| Def-3 | **density factor + min_area sensitivity ablation** (논문 supplementary) (S06-D18) | 논문 작성 시점의 별 작업 | 논문 작성 단계 |
| Def-4 | **min-dimension gate 정밀화** (LIR 활용) (S06-D12) | Stage 02 는 Stage 04 이전 → LIR 결과 없음 | Step 12 (Stage 11) |
| Def-5 | **gates 모듈을 Stage 11/13 에 binding** (S06-D13) | Step 06 = 함수 시그니처. 호출 layer = Step 12 | Step 12 |
| Def-6 | **Stage 00 normalize 책임 확장** (review #4) | Stage 04 decomposition 진입 직전 단계 | Step 07 |
| Def-7 | **`from_dict()` 일반 list[T] / multi-arm Union 명시적 raise** (Step 04 Def-10, review #5, 외부 review #2 일반화) | Step 06 에선 ProgramRequest.spaces 영역만 strict (4.2). 일반화는 Step 08 schema 진화 시 | Step 08 |
| Def-8 | **`FloorInput.floor_program: dict` typed** | apartment 단일 floor라 floor_program null. multi-floor 진입 시 의미 | Step 14 |
| Def-9 | **ClusterSpec / AccessPolicy 본격 인스턴스화** (S06-D8) | Step 09–10 (Hub/Spine/Slot) territory. Step 06 에선 `check_access_schema` gate 의 함수 시그니처만, fixture 사용 X | Step 09–10 |
| Def-10 | **Target B/C/D/E rules json + (필요시) strategy plugins** (S06-D22) | apartment 외 typology 추가 시: parameter-only면 JSON + `_DEFAULT_ADAPTERS` 한 줄. logic-different면 추가로 strategy registry (L2) 도입 — Step 09 (Spine Generation) 에서 첫 strategy 표 만들고 그 이후 typology가 enum 으로 dispatch. 어떤 경우에도 per-typology 클래스 새로 만들지 않음 | 각 Target 진입 시 |
| Def-11 | **Hole-aware decompose / schema** (외부 review #1, 메모리 review #10) — `decompose.run()`이 footprint exterior 만 mm→m 변환, `to_schema()` 도 exterior vertices, `geometry.py` schema 도 single-ring 전제. 10×10 - 2×2 hole footprint 면적 96㎡ 기대인데 100㎡ 산출 | Stage 03 anchor (void/core) 진입 직전 단계. Step 05 v3.2 import 시 LIR 도 holes 무시 가정 | Step 07 (Region/Atom Decomposition) |
| Def-12 | **`viz.svg.render(...)` 의 atoms/regions/spine 실제 렌더링** | Step 06 에선 fail-loud 만 (S06-D11). 본격 렌더는 Stage 04 산출물이 들어오는 시점 | Step 07 |
| Def-13 | **`references/cell_v3_2.py` / `zone_v12.py` 외부 의존 docstring 명시** (`/home/claude/work` 경로 + 누락 모듈) — "보존용 reference, 자체 실행 불가" 표시. broad except / post-hoc gap merge 정리 (Step 05 §5 Def-13 + 메모리 review #13) | references/ 는 보존 원본. 포팅 시점에 fix | Step 07 |
| Def-14 | **Decomposition 단위 일관성** (두 번째 review #7) — `proto3.schema.geometry.GeometricPiece.cell_w/cell_h` docstring 은 m, 그러나 `proto3.geometry.decompose.run()` 결과를 `to_schema()` 로 넣으면 mm 가 들어감. Stage 00 normalize 책임 확장 (Def-6) 와 함께 mm↔m 경계 명시. 현재 Step 05 callers (test, notebook) 가 inline 처리 (R-S05-7 mitigation) | Stage 00 normalize 가 mm↔m 경계 통합. graph/door boundary 계산 시 단위 버그 회피 | Step 07 (Stage 00 normalize) |

---

## 6. Risks

| ID | Risk | 완화책 |
|---|---|---|
| R-S06-1 | density factor 0.85 가 미래 fixture 다양화 시 false-pass / over-reject | apartment.json README 출처 명시 + Plan §5 Def-3 sensitivity ablation. R2 는 어느 값에서도 fail (sensitive 하지 않음) |
| R-S06-2 | role 별 default min_area 중간안이 임의 값 — 논문 reviewer 정당화 요구 시 | README 에 Layer A/B/D references. AiC framing: first-pass + sensitivity reportable. Plan §5 Def-3 |
| R-S06-3 | `SpaceUnitSpec.role: str → Role Literal` 좁히면 기존 fixture/test 호환성 | 모든 fixture/test 는 6 role 만 사용 (Step 03 viz 검증). round-trip test catch |
| R-S06-4 | Stage 01 에서 None → role default fill 하면 fixture roundtrip 깨짐 | round-trip 정의 = "JSON ↔ BuildingInput.program_request" 까지만. ProgramInstance 는 derived/concrete (S06-D7) |
| R-S06-5 | `proto3.constraints.gates` vs `proto3.schema.validation` 모듈 책임 모호 | gates = pure function input → bool/raise, validation = exception/dataclass. import 단방향 (gates → validation) |
| R-S06-6 | `DomainGateFailure` 계층이 Step 12 ValidationResult 흐름과 충돌 | S04-D11 패턴 답습 — exception 내부 `FailureRecord`. Step 12 가 catch 후 LayoutCandidate(valid=False) 변환 |
| R-S06-7 | `TargetAdapter(rules_path)` required 변경이 Step 04 호출 site 깨짐 | 영향 범위: `stages/stage00_load._DEFAULT_ADAPTERS` 단일 (§4.3a 이후 `_ADAPTERS` 에서 rename). 변경 = `ApartmentAdapter()` → `TargetAdapter(DEFAULT_APARTMENT_RULES_PATH)` (DoD-9) |
| R-S06-8 | `BuildingInput.program_request: dict → ProgramRequest` 타입 교체가 fixture/test 깨뜨림 | 6 fixture JSON 만 영향 (모두 동일 shape). `from_dict` deserialize 자동 변환. round-trip test catch |
| R-S06-9 | `decompose.run()` 시그니처 변경 (atom_inclusion_threshold 추가) 이 Step 05 산출물 호환성 깸 | `atom_inclusion_threshold` 는 default 인자 (Step 05 동작 그대로 유지) — 명시 호출 시만 동작 변경. `recursive.py` 의 0.5 hardcoded 제거 = 동일 동작 (default 0.5). 회귀 없음 검증 = 기존 test pass |
| R-S06-10 | `viz.svg.render` 미지원 kwarg ValueError 가 기존 호출 site 깸 | grep 결과 현재 호출자는 fixture overview notebook 등 atoms/regions/spine 안 넘김. unit test 로 catch |
| R-S06-11 | `pyproject.toml` package-data 설정 누락 시 wheel 에 json 포함 안 됨 | DoD-5 = `pip wheel . && unzip -l dist/*.whl | grep apartment.json` 로 직접 검증 |

---

## 7. Next-Step linkage

Step 06 산출물:

- `proto3.schema.program.ProgramRequest` (typed dataclass) — 모든 향후 Stage 가 dict 대신 사용.
- `proto3.schema.program.Role` (Literal) — viz / palette / 미래 게이트 / 향후 fixture 검증.
- `proto3.target.TargetRules` + `proto3.data.target_rules/apartment.json` + `rules_loader` — Target B/C/D/E 추가 시 동일 패턴 (Def-10).
- `proto3.target.apartment.DEFAULT_APARTMENT_RULES_PATH` — 모든 호출자 명시적 import.
- `proto3.constraints.gates` — Step 12 binding (Def-5).
- `proto3.stages.stage02_gate.run(...)` — Stage 02 본체.
- `proto3.schema.validation.DomainGateFailure` 계층 — Step 12 ValidationResult 변환 layer.
- 6 fixture matrix — R1 cardinality + R2 area 회로 완성.

[Step 07 Region/Atom Decomposition](000_Pipeline_Overview.md#L968):

- ProgramInstance 가 concrete 상태 진입 → RegionSet area budget 사용.
- Stage 00 normalize 책임 확장 (Def-6 / review #4).
- v3.2 Decomposition → RegionSet/AtomSet 매핑 (Step 05 §5 Def-13).
- v12 zoning broad except / gap merge 정리 (Def-13, review #13).
- **Hole-aware decompose / schema** (Def-11, 외부 review #1) — anchor/void/core 진입 직전.
- `viz.svg.render` 의 atoms/regions 실제 렌더 (Def-12).
- `references/` 외부 의존 docstring (Def-13).

[Step 08 Graph Construction](000_Pipeline_Overview.md#L969):

- gates.py 함수들이 contact graph 도메인 검증에 호출 가능.
- `from_dict()` 일반 strict deserialize (Def-7, review #5, 외부 review #2 일반화).

[Step 12 Validation/Repair](000_Pipeline_Overview.md#L973):

- gates.py Stage 11/13 binding (Def-5).
- DomainGateFailure 계열 catch → LayoutCandidate(valid=False) 변환 (review #6).
- min-dim gate 정밀화 (LIR, Def-4).

**외부 scan-to-BIM 파이프라인 통합 시점**:

- proto3 코드 변경 없음 — 외부가 자기 json 만들어 `TargetAdapter(rules_path=external_path)` 주입 (§4.3a 이후 단일 generic class).
- 외부가 base 통째 복사 후 수정 (S06-D17, 부분 override 미지원).

---

## 8. Branch / Commit strategy

- **Branch**: `step06-program-constraint-engine` (이미 checkout, 2026-05-09).
- **Commits**: §4 work items 1:1 = 9 commits (4.1 ~ 4.9).
- **Close**: `git checkout main && git merge --no-ff step06-program-constraint-engine && git branch -d step06-program-constraint-engine && git push origin main` (D015).

---

## 9. 변경이력

| Date | Change |
|---|---|
| 2026-05-09 | Initial draft (v1). §0~§8. 16 decisions (S06-D1 ~ S06-D16). 9 work items. 23 DoD. Future work 명시 (Def-1~3). |
| 2026-05-09 | v5 — Step 06 close. 10 work items 모두 land (4.1 `3f09cbe` archive+scaffold, 4.2 `f241d58` ProgramRequest+Role, 4.3 `0da364b` TargetRules+JSON, 4.3a `372090b` generic adapter reform, cleanup `be906b4` review followups, design `01e42d3` 모델링 결함 8 항목, 4.4 `8c1903d` DomainGateFailure+gates, 4.5 `bb6a32a` Stage 01 본격, 4.6 `c920c4e` Stage 02 + R2 회로, 4.7 `bd27fa5` fail-loud sweep, 4.8 `17c852f` notebook). DoD 28/28 [x]. 221 passed (Step 05 80 + Step 06 신규 141). D020/D021/D022/D023 Status Accepted. R2 `verified_at: Step 06` 약속 실현 (`AreaGateFailure` live trigger). 다음 = Step 07 Region/Atom Decomposition. |
| 2026-05-09 | v4 — 두 번째 외부 review (또 다른 Claude 인스턴스) 의 모델링 결함 8 항목 정리. (1) D023 신설 — required-only cardinality / area summation (Stage 01/02 가 `required=True` 만 본다). (2) D020 본문 강화 — Stage 02 fail-only (repair → Stage 12) + 3 active gates (area/dim/multi-floor) + access dormant scaffold. (3) D022 본문 강화 — "JSON + 한 줄" boundary (기존 5×6 grid 안에서만; 새 TargetType/Role 은 schema diff). (4) Pipeline §9.10 갱신 — cardinality check 제거 (Stage 01 책임), repair 출력 제거, single-floor 가정 명시. (5) Plan §0 산출물 5번 fail-only / required-only / gross / single-floor 명시. (6) S06-D6/D7/D12/D22 보강 + S06-D23/D24 신설. (7) §5 Def-14 추가 (Decomposition 단위 일관성, Step 07 entry). 21 decisions (S06-D1~D18 + D22~D24) / 10 work items (4.1~4.3 + 4.3a + 4.4~4.9). 또한 README + Architecture Decisions 일치. |
| 2026-05-09 | v3 — §4.3a generic adapter reform (S06-D22 신설). per-typology Adapter 클래스 폐기 → 단일 `TargetAdapter` concrete class. typology 식별자 JSON `target_type` 필드로 이전. README 대폭 강화 (3-layer model + mission scope). D021/D022 본문 갱신. `.gitignore` 에 `build/`, `dist/` 추가. 이유: typology 4개 (B/C/D/E) 본격 진입 확정 (사용자 답 2026-05-09) → per-typology 클래스 boilerplate 4 × ~25줄 회피. proto3 = engine, 외부 데이터 분리. 19 decisions (S06-D1~D18 + D22) / 10 work items (4.1~4.3 + 4.3a + 4.4~4.9). |
| 2026-05-09 | v2 — 외부 review (다른 Claude 인스턴스) 16 항목 반영. 주요 변경: (1) `config/` repo root → `src/proto3/data/target_rules/` 패키지 내 (외부 review #6, S06-D4). (2) Stage 01 본격화 — `SpaceUnitSpec` 모든 필드 보존 + dup name / unknown role / type mismatch (외부 review #4, S06-D7 보강). (3) `atom_inclusion_threshold` dead config wiring — `decompose.run()` 시그니처 + `recursive.py` 0.5 hardcoded 제거 (외부 review #3, S06-D14 보강). (4) `viz.svg.render` 미지원 kwarg ValueError + `palette` 통일 (외부 review #11/#12, S06-D11 신설). (5) `ApartmentAdapter.load_fixture` target_type 검사 (외부 review #8, S06-D15 신설). (6) Pipeline §9.10 Stage 02 outputs 갱신 (외부 review #7, DoD-23 추가). (7) `schema.__init__` + test_smoke 22→24 (외부 review #12, DoD-24, 4.1 흡수). (8) Step 05 Plan header `Completed (merged 7064132)` 갱신 (외부 review #15, DoD-25, 4.1 흡수). (9) S06-D13 (AccessPolicy `__post_init__` 검증) 제거 — Def-9 (Step 09-10) 그대로 (외부 review #5). (10) `serialize.py` `list[T]` 강화 — ProgramRequest.spaces 영역 한정 (외부 review #2, 일반화는 Def-7 Step 08). (11) Hole-aware decompose Def-11 신설 (외부 review #1, Step 07). (12) `references/` docstring Def-13 신설 (외부 review #16, Step 07). 18 decisions / 9 work items / 28 DoD / 13 deferred / 11 risks. |
