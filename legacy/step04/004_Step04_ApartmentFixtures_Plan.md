# 004 Step 04 — Apartment Fixtures / Target Adapter Plan

Status: Completed (pending merge)
Started: 2026-05-07
Completed: 2026-05-07
Branch: `step04-apartment-fixtures`
Companion tracker: [004_Step04_ApartmentFixtures_Tracker.md](004_Step04_ApartmentFixtures_Tracker.md)

---

## 0. Purpose

Step 04 = "Apartment Fixtures / Target Adapter" per [Pipeline Overview §15](000_Pipeline_Overview.md). 산출물 3가지:

1. **5-fixture matrix** — apartment 다양성 + 회귀 검증 입력 데이터 (A1, A2, B1, R1, R2).
2. **Target adapter framework** — `TargetAdapter` Protocol + `ApartmentAdapter` 구현. fixture JSON → `BuildingInput` 변환과 target 별 룰 진입점.
3. **Stage 00 + Stage 01 와꾸** — Stage 00 (input load + normalize) 완성 + Stage 01 (program_request → ProgramInstance + cardinality fail) 골격. Stage 02 area gate + 본격 게이트 엔진은 [Step 06](000_Pipeline_Overview.md#L964) 책임.

DH-004 (bathroom-0 regression) 회귀 검증 회로는 Step 04 시점에 **R1 fixture + Stage 01 cardinality fail**로 작동. R2 (area gate) 검증 회로는 Step 06 대기.

---

## 1. Definition of Done

| # | 조건 | 검증 방법 |
|---|---|---|
| DoD-1 | `src/proto3/target/` (Protocol + ApartmentAdapter) 모듈 트리 존재, import OK | `python -c "from proto3.target import TargetAdapter, ApartmentAdapter"` |
| DoD-2 | `src/proto3/stages/` (stage00_load, stage01_program) 모듈 트리 존재, import OK | `python -c "from proto3.stages import stage00_load, stage01_program"` |
| DoD-3 | `ApartmentAdapter.load_fixture(path)` returns valid `BuildingInput` | unit test |
| DoD-4 | Stage 00 module — fixture path → `BuildingInput` + `target_type` consistency check (S02-D14의 `assert_target_consistent` 호출) | unit test |
| DoD-5 | Stage 01 module — `program_request` → `ProgramInstance` 변환 + cardinality 게이트 (D004 적용: required wet count==0 → `ProgramInstantiationFailure`) | unit test |
| DoD-6 | 5 fixture 파일 존재 (`fixtures/apartment_*.json`) + 각 round-trip OK via Step 02 schema | round-trip test |
| DoD-7 | `tests/fixture_matrix.py` (또는 동등물)에 5 fixture ID → 파일 매핑 + matrix metadata + R1/R2 expected_failure 정보 | import test |
| DoD-8 | R1 fixture가 Stage 01에서 `ProgramInstantiationFailure` 발생 — Step 04에서 검증 회로 작동 | regression test |
| DoD-9 | `pytest -q` 통과 (Step 03의 19 + Step 04 신규 테스트 합산) | pytest |
| DoD-10 | `python -m pip install -e .` 회귀 없음 — 신규 runtime deps 0개 (system `pip` alias may target wrong Python; use `python -m pip`) | install check |
| DoD-11 | Step 03 docs (`003_Step03_*.md`) → `legacy/step03/` via `git mv` | git ls-files |
| DoD-12 | `000_Progress_Tracker.md`가 Step 04 close 시점에 "Step 04 → Done" 갱신 (Active files, Step status table 포함) | manual |
| DoD-13 | `notebooks/step04_fixture_overview.ipynb` 실행 시 `outputs/notebooks/step04_fixture_overview/<run_id>/`에 5개 SVG 생성 | notebook 실행 |
| DoD-14 | §4 commits 모두 `step04-apartment-fixtures` branch에 land + `git merge --no-ff` to main + branch 삭제 | git log |
| DoD-15 | `000_Progress_Tracker.md`가 4.1 commit에서 "Step 04 In progress"로 갱신 + 4.8 commit에서 "Done"으로 갱신 (kickoff/close 두 시점) | git diff |
| DoD-16 | `ProgramInstantiationFailure` exception class가 `proto3.schema.validation`에 정의됨, import OK | `python -c "from proto3.schema.validation import ProgramInstantiationFailure"` |

---

## 2. 결정 기록

| ID | 결정 | 근거 |
|---|---|---|
| **S04-D1** | Fixture 5-matrix 채택: A1 (rect 8×6m, 1bed/1bath), A2 (rect 13×10m, 4bed/2bath), B1 (L자 ~9×8m, 2bed/1bath), R1 (rect 8×6m, 1bed/0bath = DH-004), R2 (rect 4×4m, 2bed/1bath = area-too-small) | typology 다양성 + DH-004 + area gate fail 두 회귀 케이스 확보 |
| **S04-D2** | 사선(non-Manhattan)·곡선 footprint은 Step 04에선 **deferred**. atom-grid fitting 알고리즘이 Step 05 Geometry Kernel에서 결정된 후 fixture 추가. 정식 D-decision 등록도 Step 05 시점 | atom = 600mm cubic grid (D006) 가정. 지금 사선/곡선 fixture 만들면 Step 07 decomposition 진입 전엔 stranded. 곡선은 추가로 Stage 00 normalization → 평면 polygon + 곡선 metadata, Stage 13 output에서만 복원하는 전략 잠정 합의 (정식 D는 Step 05) |
| **S04-D3** | Target adapter = `TargetAdapter` Protocol + `ApartmentAdapter` 구현만. B/C/D/E는 코드에 placeholder class 만들지 않음 | Targets C/D/E premature 우려. Protocol 추상화로 확장 표준은 잡히고 placeholder cargo-cult 회피. `TargetType` Literal alias는 Step 02에서 이미 5종 정의돼 있어 framework 일관성은 보존됨 |
| **S04-D4** | Stage 00 (load + normalize) 완성 + Stage 01 (program_request → ProgramInstance + cardinality 게이트) **와꾸까지** 구현. Stage 02 area gate + 본격 게이트 엔진(min dimension, access policy 등)은 Step 06으로 yield | DH-004 회귀를 Step 06까지 미루지 않고 Step 04에서 회로 작동시키기 위함. Step 06과 일부 churn은 의도된 trade-off — Plan §6 Risks 및 코드 docstring에 "Step 04 frame; Step 06 will replace/extend" 마커 명시 |
| **S04-D5** | `program_request` schema는 Step 02 결정(`dict`) 그대로 유지. `ProgramRequest` dataclass 정형화는 Step 06 | Step 02 결정 존중 + Step 04 책임 lean. dict는 fixture 도메인-specific 키(예: balcony, walk-in-closet) 추가에 유연 |
| **S04-D6** | R1은 Step 04에서 Stage 01 cardinality fail로 회로 작동 검증. R2는 fixture data만 land + 검증 회로는 Step 06 (Stage 02 area gate land 시) | Stage 02가 Step 06 책임이므로 분리 |
| **S04-D7** | palette mapping 정형화 (R-S03-2: ProgramInstance.category → palette key)는 Step 04에서 다루지 않음 → Step 06 (Program & Domain Constraint Engine)으로 yield | ProgramInstance.category 자체가 Step 06에서 정의됨. Step 03의 fallback (`role_to_palette_key` + private 기본)이 Step 04 fixture로 충분 작동 |
| **S04-D8** | A1 = `fixtures/apartment_minimal.json` **재사용** (Step 03 산출물 그대로). matrix ID 추적은 fixture JSON 안에 metadata 필드 추가 대신 `tests/fixture_matrix.py` 코드 매핑(`MATRIX = {"A1": {"file": "apartment_minimal.json", ...}, ...}`)으로 분리 | BuildingInput schema (D017 strict Literal validation) 유지. fixture JSON은 schema-clean, matrix metadata는 코드에서. R1/R2 expected_failure metadata도 동일하게 `tests/fixture_matrix.py`에만 |
| **S04-D9** | `notebooks/step04_fixture_overview.ipynb` 추가 — 5 fixture를 `proto3.viz.render`로 일괄 SVG 출력해서 비교 (Step 03 notebook 패턴 재사용) | 시각화 default 원칙. 5 fixture 다양성을 시각으로 확인 |
| **S04-D10** | `fixtures/` 디렉토리 구조는 평탄 유지 (`apartment_*.json` 5개 직접). `fixtures/apartment/` 하위 디렉토리 도입은 Target B 진입 시 결정 | 5개에 폴더 분리는 over-engineering. Target adapter Protocol 도입으로 향후 분리 부담은 작음 |
| **S04-D11** | `ProgramInstantiationFailure`는 **Exception class**로 정의. import path: `proto3.schema.validation.ProgramInstantiationFailure`. 내부에 `FailureRecord` 인스턴스 보관 (`failure: FailureRecord` 속성). Stage 01 cardinality 게이트가 raise | D004 "regression rule"은 silent fall-through 금지가 핵심 — 못 잡으면 crash가 가장 강한 escalate. 기존 `FailureRecord`/`ValidationResult` 와는 단순 result-dataclass 흐름이라 exception이 single-purpose. 둘 다 schema/validation에 두면 import 일관성 |
| **S04-D12** | R1 fixture의 "0 bath"는 `program_request.spaces` 리스트에서 **wet role 항목을 빠뜨려** 표현 (counts dict 같은 구조 추가 안 함). cardinality 검증은 `ApartmentAdapter.target_rules()` 가 반환하는 `{"min_cardinality": {"wet": 1, "private": 1, "public": 1}}` 와 ProgramInstance를 비교해서 수행 | program_request raw shape 보존 (S04-D5). 카디널리티 spec은 Target rule에 있음이 자연스러움 (apartment-specific 룰). DH-004의 silent fall-through trauma도 동일 구조: instantiation 결과가 wet=0이면 fail |
| **S04-D13** | Stage 00 `run()` signature: `run(path: Path, *, run_config: RunConfig \| None = None, adapter: TargetAdapter \| None = None) -> BuildingInput`. `adapter` None이면 RunConfig.target_type으로 추론 (apartment → ApartmentAdapter). `run_config` None이면 target consistency check 생략 | keyword-only로 명시적 호출 강제 (S03-D6 패턴). adapter/run_config optional이라 unit test 단순. assert_target_consistent는 둘 다 있을 때만 호출 |
| **S04-D14** | Legacy 문서 (`legacy/stepNN/*.md`)의 상대 링크는 archive 후 maintained 안 함 정책. legacy는 frozen historical record로 취급 | Step 02/03 archive 후 상대 링크가 깨진 상태로 발견됨. fix 자동화 가능하지만 legacy 참조 빈도가 거의 0. 정책으로 명시해서 audit 명료. Pipeline §16 + Architecture Decisions에 mirror |

---

## 3. Directory structure (Step 04 완료 시)

```text
src/proto3/
├── __init__.py
├── config.py
├── debug.py
├── schema/
│   ├── (Step 02 그대로)
│   └── validation.py            # +ProgramInstantiationFailure (S04-D11)
├── viz/                         # (Step 03 그대로)
├── target/                      # 신규
│   ├── __init__.py
│   ├── base.py                  # TargetAdapter Protocol
│   └── apartment.py             # ApartmentAdapter (target_rules 포함)
└── stages/                      # 신규
    ├── __init__.py
    ├── stage00_load.py          # input load + normalize + target consistency (S04-D13)
    └── stage01_program.py       # program_request → ProgramInstance + cardinality gate (frame)

fixtures/
├── apartment_minimal.json         # A1 (Step 03 산출물 재사용)
├── apartment_4bed_2bath.json      # A2
├── apartment_l_shape.json         # B1
├── apartment_no_bath.json         # R1 (DH-004 regression)
└── apartment_too_small.json       # R2

notebooks/
├── step03_viz_demo.ipynb          # (Step 03 그대로)
└── step04_fixture_overview.ipynb  # 신규

tests/
├── (기존)
├── fixture_matrix.py              # MATRIX dict + helpers
├── test_target_adapter.py         # 신규
├── test_stage00_load.py           # 신규
├── test_stage01_program.py        # 신규 (R1 cardinality fail 포함)
└── test_fixtures_roundtrip.py     # 신규

legacy/step03/
├── 003_Step03_Visualization_Plan.md
└── 003_Step03_Visualization_Tracker.md
```

### 3.1 Fixture 명세 (자동화 입력 표)

S04-D1 5개 fixture의 구체 shape. 좌표 단위 = mm, role enum = SpaceUnitSpec.role.

| ID | 파일 | footprint vertices (mm) | floor_root | program_request.spaces (name / role) | 의도 / expected behavior |
|---|---|---|---|---|---|
| A1 | `apartment_minimal.json` (existing) | `[[0,0],[8000,0],[8000,6000],[0,6000]]` | `(4000, 0)` | living/public, bedroom_1/private, bathroom_1/wet | baseline, Stage 00/01 OK |
| A2 | `apartment_4bed_2bath.json` | `[[0,0],[13000,0],[13000,10000],[0,10000]]` | `(6500, 0)` | living/public, kitchen/service, bedroom_1~4/private (4개), bathroom_1~2/wet (2개) | multi-cardinality, Stage 00/01 OK |
| B1 | `apartment_l_shape.json` | `[[0,0],[9000,0],[9000,5000],[5000,5000],[5000,8000],[0,8000]]` | `(4500, 0)` | living/public, bedroom_1~2/private, bathroom_1/wet, kitchen/service | reflex 1개, Stage 00/01 OK |
| R1 | `apartment_no_bath.json` | `[[0,0],[8000,0],[8000,6000],[0,6000]]` (A1과 동일) | `(4000, 0)` | living/public, bedroom_1/private (wet 항목 **없음**) | Stage 01 → `ProgramInstantiationFailure` (DH-004) |
| R2 | `apartment_too_small.json` | `[[0,0],[4000,0],[4000,4000],[0,4000]]` | `(2000, 0)` | living/public, bedroom_1~2/private, bathroom_1/wet, kitchen/service | Stage 02 area-gate fail (검증 회로는 Step 06) |

`tests/fixture_matrix.py`의 `MATRIX` 형태:

```python
MATRIX = {
    "A1": {"file": "apartment_minimal.json", "expected_failure": None},
    "A2": {"file": "apartment_4bed_2bath.json", "expected_failure": None},
    "B1": {"file": "apartment_l_shape.json", "expected_failure": None},
    "R1": {"file": "apartment_no_bath.json", "expected_failure": "ProgramInstantiationFailure", "verified_at": "Step 04"},
    "R2": {"file": "apartment_too_small.json", "expected_failure": "AreaGateFailure", "verified_at": "Step 06"},
}
```

모든 fixture에 공통: `target_type="apartment"`, `floors`는 1개, `floor_program=null`, `anchor_projections=[]`, `persistent_anchors=[]`.

---

## 4. Work items

[Tracker §1](004_Step04_ApartmentFixtures_Tracker.md)와 1:1 매칭. **각 항목 = 1 commit**.

| # | 작업 | commit msg |
|---|---|---|
| 4.1 | Step 03 docs `legacy/step03/` archive + `src/proto3/target/` & `src/proto3/stages/` 모듈 scaffold (placeholder + `__init__.py`) + Plan/Tracker 추가 + drift fix (palette.py, debug.py 주석) + Progress Tracker §1/§6 "Step 04 In progress" 갱신 + D016 amendment(H012) + Pipeline §16 mirror | `chore: archive step03 docs + scaffold step04 module structure` |
| 4.2 | `TargetAdapter` Protocol (`target/base.py`) + `ApartmentAdapter` (`target/apartment.py`) 구현. 메서드: `load_fixture(path) -> BuildingInput`, `target_rules() -> dict` (apartment min_cardinality 보유) | `feat: target adapter protocol + apartment adapter (S04-D3, D12)` |
| 4.3 | `stages/stage00_load.py` — `run(path, *, run_config=None, adapter=None) -> BuildingInput` (S04-D13). adapter None시 RunConfig.target_type으로 추론. run_config 있으면 `assert_target_consistent` 호출 | `feat: stage 00 input load + normalization (S04-D4, D13)` |
| 4.4 | `schema/validation.py`에 `ProgramInstantiationFailure(Exception)` 추가 (S04-D11). `stages/stage01_program.py` — `program_request: dict` → `ProgramInstance` 변환 + cardinality 게이트 (target_rules와 비교, 미충족 시 raise). docstring "Step 04 frame; Step 06 will replace/extend" 마커 | `feat: stage 01 program resolution frame + cardinality gate (S04-D4, D11, D12)` |
| 4.5 | Fixture 4개 신규 작성 (A2, B1, R1, R2) per §3.1 명세 + `tests/fixture_matrix.py` MATRIX dict | `feat: 5-fixture matrix (A2/B1/R1/R2 new + A1 reuse, S04-D1)` |
| 4.6 | Tests: target adapter / stage00 load / stage01 program (R1 cardinality fail 포함) / fixture roundtrip 5개 | `feat: step04 tests (target adapter + stage 00/01 + R1 regression)` |
| 4.7 | `notebooks/step04_fixture_overview.ipynb` — 5 fixture 일괄 렌더링. Step 03 cwd resolver 패턴 재사용 | `feat: step04 fixture overview notebook (5-fixture compare, S04-D9)` |
| 4.8 | Step 04 cleanup: Plan/Tracker 마무리, `000_Progress_Tracker.md` "Step 04 → Done" 갱신, merge --no-ff 후 branch 삭제 | `docs: step04 cleanup (Plan/Tracker, Progress Tracker)` |

실행 순서: 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 → 4.7 → 4.8 → (Step 종료) merge --no-ff to main.

---

## 5. Deferred (명시적 비-목표)

| # | 항목 | 이유 | 처리 시점 |
|---|---|---|---|
| Def-1 | 사선(non-Manhattan) footprint fixture | atom-grid fitting 알고리즘 Step 05/07에서 결정 (S04-D2) | Step 05/07 |
| Def-2 | 곡선 footprint fixture | Stage 00 normalization 전략 결정 (S04-D2). 정식 D-decision도 Step 05 | Step 05 |
| Def-3 | B2 (L자 3bed/2bath), C1 (U자), C2 (T자) 추가 typology fixture | branched spine / courtyard / T-junction은 Step 09 (spine candidate) / Step 07 (decomposition) 진입 시 의미 | Step 07~09 |
| Def-4 | Stage 02 area gate + Stage 02 본격 게이트 엔진 (min dimension, access policy) | Step 06 책임 (S04-D4) | Step 06 |
| Def-5 | R2 fixture 회귀 회로 작동 (area-too-small fail) | Stage 02 area gate가 Step 06에서 land (S04-D6) | Step 06 |
| Def-6 | `ProgramRequest` dataclass 정형화 | Step 06 책임 (S04-D5) | Step 06 |
| Def-7 | palette mapping (`ProgramInstance.category` → palette key) — R-S03-2 | Step 06 (Program Engine)에서 category 정의 시 (S04-D7) | Step 06 |
| Def-8 | Target B/C/D/E adapter 구현 / placeholder class | premature (S04-D3) | 각 Target 본격 진입 시 |
| Def-9 | `fixtures/apartment/` 하위 디렉토리 분리 | 5개에 over-engineering (S04-D10) | Target B 진입 시 |
| Def-10 | `proto3.schema.serialize.from_dict()` multi-arm Union 명시적 raise | 현재 schema에선 trigger 케이스 없음. 미래 schema 진화 시 안전화 | Step 05+ |
| Def-11 | `TargetRules` dataclass/TypedDict 정형화 (현재 `target_rules() -> dict`는 loose) | Step 06에서 ProgramRequest dataclass와 함께 정형화하면 자연스러움. 지금은 Stage 01이 `min_cardinality` shape를 그대로 신뢰 | Step 06 |

---

## 6. Risks

| ID | Risk | 완화책 |
|---|---|---|
| R-S04-1 | Stage 01의 cardinality 게이트 로직이 Step 06에서 재작성됨 → 코드 churn | S04-D4 명시: 코드 docstring "Step 04 frame; Step 06 will replace/extend" 마커. Plan §2 명시. Step 06 진입 시 의도된 작업으로 인식 |
| R-S04-2 | R2 fixture가 Step 06까지 회로 안 돔 → "dead fixture" 인상 | Plan §5 Def-5에 명시. expected_failure metadata는 **`tests/fixture_matrix.py`에만** (S04-D8: fixture JSON에는 metadata 안 넣음, BuildingInput strict validation 깨짐 방지) |
| R-S04-3 | L자 footprint (B1) polygon 표현이 Step 02 schema (`list[tuple[float, float]]`)와 호환 불일치 가능 | Step 02의 `FloorInput.footprint`는 polygon vertices라 L자도 6+ vertices로 표현 가능. round-trip test (DoD-6)가 catch |
| R-S04-4 | `TargetAdapter` Protocol 인터페이스가 Step 06+에서 유지 안 될 수 있음 | Protocol minimal만 정의 (`load_fixture`, `target_rules`). 향후 메서드 추가는 self-extending. Breaking change risk 낮음 |
| R-S04-5 | `apartment_minimal.json`을 A1으로 재사용 → 의미 dual: viz smoke + matrix A1. 한 fixture가 여러 역할 = drift 위험 | `tests/fixture_matrix.py`에 명시적 매핑 + Step 03 viz smoke test도 같은 fixture 참조. 두 역할이 명시적으로 추적되면 OK |
| R-S04-6 | `ProgramInstantiationFailure` Exception이 Step 06에서 ValidationResult 흐름과 맞물릴 때 충돌 가능 | S04-D11에 exception 내부 `FailureRecord` 보관 명시 — Step 06이 catch 후 ValidationResult로 변환 가능. exception 자체는 single-purpose라 호환성 유지 |

---

## 7. Next-Step linkage

Step 04 산출물:
- `proto3.target.TargetAdapter` Protocol — 모든 향후 Target 구현이 따를 인터페이스.
- `proto3.target.ApartmentAdapter` — Target A 구현 (다른 Target은 각 Target 진입 시 추가).
- `proto3.stages.stage00_load.run(...)` — 모든 Stage 파이프라인의 진입점.
- `proto3.stages.stage01_program.run(...)` — Stage 01 와꾸. Step 06이 이 자리를 본격 엔진으로 교체/확장.
- `proto3.schema.validation.ProgramInstantiationFailure` — D004 회귀를 raise하는 exception.
- `tests/fixture_matrix.py` — Step 05+의 모든 회귀/smoke 테스트가 이 매핑을 참조.
- 5-fixture matrix — Step 05~09에서 알고리즘 검증 입력으로 사용.

[Step 05 Geometry Kernel](000_Pipeline_Overview.md#L963):
- atom = 600mm grid에 어떻게 footprint를 fit할지 결정 → 이 시점에 사선 fixture 추가 가능.
- 곡선 normalization 전략 정식 D-decision 등록.

[Step 06 Program & Domain Constraint Engine](000_Pipeline_Overview.md#L964):
- `ProgramRequest` dataclass 정형화.
- Stage 01 본격 cardinality 엔진 (Step 04 와꾸 교체/확장).
- Stage 02 area gate + min dimension + access policy 게이트.
- ProgramInstance.category 정의 → R-S03-2 palette mapping 정형화.
- R2 fixture 회로 작동.

---

## 8. Branch / Commit strategy

- **Branch**: `step04-apartment-fixtures` (이미 checkout됨, 2026-05-07).
- **Commits**: §4 work items 1:1 = 8 commits (4.1 ~ 4.8).
- **Close**: `git checkout main && git merge --no-ff step04-apartment-fixtures && git branch -d step04-apartment-fixtures && git push origin main` (D015).

---

## 9. 변경이력

| Date | Change |
|---|---|
| 2026-05-07 | Initial draft. §0~§8. 10 decisions (S04-D1 ~ S04-D10). 8 work items. 14 DoD. Fixture matrix 5개 (다른 세션 합의 8→5 축소). |
| 2026-05-07 | 리뷰 반영 #1. S04-D11 (ProgramInstantiationFailure exception), D12 (R1 표현 + target_rules min_cardinality), D13 (Stage 00 run signature), D14 (legacy link 정책). DoD-15/16 추가. §3.1 fixture 명세 표 신설. §4.1에 drift fix + Progress Tracker kickoff 갱신 + D016 amendment + Pipeline §16 mirror 추가. §5 Def-10 추가. §6 R-S04-2 텍스트 fix (fixture JSON metadata 금지 명시), R-S04-6 신설. |
| 2026-05-07 | Step 04 close. 8 commits on `step04-apartment-fixtures` (7ce53f4 archive+scaffold → d92edb5 notebook → cleanup). 39 passed. 14/16 DoD [x], DoD-14 [~] (merge --no-ff + branch 삭제 사용자 확인 대기). |
| 2026-05-07 | 리뷰 반영 #1 — DoD-10 명령 `python -m pip install -e .`로 변경 (#1). Def-11 추가 (TargetRules TypedDict, #5). |
