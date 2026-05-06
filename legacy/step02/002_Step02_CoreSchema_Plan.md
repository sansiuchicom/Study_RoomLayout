# 002 Step 02 — Core Schema / Run Config / Debug Output Contract Plan

Status: Completed
Scope: 22개 schema dataclass stub + RunConfig + DebugArtifact (+ 폴더 contract) + serialization helpers + smoke tests. D015/D016 첫 적용 Step. (총 24 dataclass = 22 schema + RunConfig + DebugArtifact)
Last updated: 2026-05-06

---

## 0. Purpose

이 문서는 **Plan(결정 living doc)**이다. 의논으로 합의된 결정이 누적되며, 자동화/실행 주체가 이 문서만으로 작업할 수 있을 만큼 구체적이어야 한다.

역할 분리는 [D016](000_Architecture_Decisions.md)에 정식 정의됨. 요약:

| 문서 | 역할 | 갱신 주기 |
|---|---|---|
| **이 Plan** | 결정·사양·작업 사양 | 의논 중에는 자주, 결정 후 동결 |
| **Step Tracker** | 진행 로그·체크리스트 | 작업하며 수시 |
| **000_Progress_Tracker** | Step 마일스톤 | Step 시작/종료 |

Cross-reference:

- Framework / Step map / Stage 정의: [000_Pipeline_Overview.md §15](000_Pipeline_Overview.md), [§9](000_Pipeline_Overview.md), [§12](000_Pipeline_Overview.md)
- 핵심 결정: [D012](000_Architecture_Decisions.md) (dataclass 24개 minimum), [D013](000_Architecture_Decisions.md) (SVG-first), [D014](000_Architecture_Decisions.md) (.gitignore), [D003](000_Architecture_Decisions.md) (apartment-first + floor-rooted), [D015](000_Architecture_Decisions.md) (branch+commit), [D016](000_Architecture_Decisions.md) (Plan/Tracker structure)
- Debug output 폴더 명세: [Pipeline Overview §12.2](000_Pipeline_Overview.md)
- 작업 환경 / S01-D5: 환경 binary 절대경로 (`/opt/conda/envs/IfcOpenHouse/bin/python`)

---

## 1. Definition of Done

| # | 조건 | 검증 방법 |
|---|---|---|
| DoD-1 | §3 모듈 트리 모두 존재 | `ls src/proto3/schema/` → 8개 .py + `ls src/proto3/{config,debug}.py` |
| DoD-2 | 22개 schema dataclass 모두 정의 (Pipeline Overview에서 추론 가능한 필드 + TBD 주석). RunConfig/DebugArtifact는 DoD-3/DoD-4가 담당 | `from proto3.schema import *` 후 각 클래스 `@dataclass` 확인 |
| DoD-3 | `RunConfig` 정의 (필드 §2/S02-D4 표) | `RunConfig()` instantiation OK |
| DoD-4 | `DebugArtifact` + 17개 파일명 상수 + `run_folder()` 헬퍼 정의 | `from proto3.debug import INPUT_FILENAME, ...` |
| DoD-5 | `to_json` / `from_json` round-trip OK (`BuildingInput` 빈 인스턴스 1개) | round-trip pytest 1개 통과 |
| DoD-6 | `pytest -q` 모두 통과 (smoke + serialize round-trip) | "X passed" |
| DoD-7 | `pip install -e .` 회귀 없음 | exit 0 |
| DoD-8 | Step 01 docs가 `legacy/step01/` 로 이동됨 | `ls legacy/step01/` → 2개 .md |
| DoD-9 | `000_Progress_Tracker.md` Step 02 완료로 갱신 | `grep` 또는 수동 |
| DoD-10 | 5개 commit이 `step02-core-schema` 브랜치에 들어감 (P5 단위) | `git log --oneline step02-core-schema ^main` |
| DoD-11 | merge `--no-ff` 후 main에 들어가고 branch 삭제됨 | `git branch` 확인 |

---

## 2. 결정 기록

| ID | 항목 | 결정 | 이유 |
|---|---|---|---|
| S02-D1 | 모듈 분할 | `src/proto3/schema/` 의미별 분할 (Q1=B) | 변경 시 git diff scope 좁아짐. 24개 한 파일은 부담. Stage별 분할은 한 클래스가 여러 Stage에 걸쳐 모호 |
| S02-D2 | Stub 깊이 | Pipeline Overview §6/§9에 명시된 필드만 정의, 미상은 `# TBD: ...` 주석 (Q2=B) | 클래스 이름만(A)은 다음 Step 작업 가치 0. 전부 정의(C)는 다음 Step 사용 패턴과 충돌 |
| S02-D3 | Serialization | `src/proto3/schema/serialize.py` free function 모듈 (`to_dict`, `from_dict`, `to_json`, `from_json`) (Q3=B) | dataclass=데이터 정의, helper=정책 분리 (SRP). Custom 타입(Polygon/Enum/datetime/numpy) 일괄 관리. Debug-first 설계의 안정성 |
| S02-D4 | RunConfig 범위 | 최소 필드 (Q4=A). 아래 표 | 미정의 필드를 미리 만들면 다음 Step이 또 손봄 |
| S02-D5 | Debug contract | `DebugArtifact` dataclass + 17개 파일명 상수 + `run_folder(run_id)` 헬퍼. **write 함수는 유예** (Step 03과 함께) (Q5=A+일부B) | 파일명 상수는 다음 Step 오타 방지에 즉시 가치. write 함수는 visualization과 묶어서 |
| S02-D6 | 테스트 범위 | smoke (각 모듈 import + 각 dataclass instantiation) + serialize round-trip 1개 (Q6=A) | actual behavior 거의 없음. round-trip은 helper 자체 검증용 1개만 |
| S02-D7 | Plan §A | 생략 (Q8=A) | D016 권장 — 코드는 git에 있으니 인라인 자료 가치 작음. 결정 표(§2)에 default 값 박는 것으로 대체 |
| S02-D8 | commit 단위 | 5개 (P5; Q7) | "3~7개 선" + schema는 의미적 한 묶음 |
| S02-D9 | branch | `step02-core-schema` (D015) | D015의 `stepNN-<kebab-name>` 컨벤션 첫 적용 |
| S02-D10 | apartment-first 호환 | `BuildingInput`은 `floors: list[FloorInput]` 형태로 multi-floor 호환. apartment용은 `len(floors) == 1` 케이스 ([D003](000_Architecture_Decisions.md)) | "core schema must support BuildingInput, FloorInput from beginning" 원칙 충족 |
| S02-D11 | type forward reference | 필요 시 `from __future__ import annotations` 사용 (string-based type hint) | 같은 모듈 내 / 순환 참조 회피 |
| S02-D12 | Step 01 docs 이동 시점 | Step 02의 첫 commit에 포함 (P5 #1) | Step 01 cleanup 절차 ([D016](000_Architecture_Decisions.md))의 마지막 단계. 같은 branch에서 처리하는 게 자연스러움 |
| S02-D13 | `from_dict` 입력 검증 정책 | (a) `data`가 dict 아닌 경우 `TypeError`. (b) 알려지지 않은 key는 기본값 `strict_unknown=True`로 `ValueError`. (c) cls에 있고 data에 없는 missing key는 그대로 dataclass default fallback (S02-D4 backward-compat 유지). `strict_unknown=False`는 *필드 제거* 시점의 escape hatch | (a)/(b)는 backward-compat과 무관 — 정책을 한 if문에 묶어두면 typo·잘못된 호출이 silent하게 빈 객체를 만든다. (c)만 backward-compat 경로 |
| S02-D14 | `target_type` canonical source | `Literal["apartment","house","hotel","warehouse","office"]` 별칭 `TargetType`을 [`schema/input.py`](src/proto3/schema/input.py)에 정의. `BuildingInput.target_type` (데이터 정체성)과 `RunConfig.target_type` (런타임 의도) 둘 다 `TargetType`. 일치 강제는 [`proto3.config.assert_target_consistent`](src/proto3/config.py)가 Stage 00에서 수행 | 둘은 의미가 달라 한쪽만 두면 fixture 로드 *전*에 target을 알 수 없거나, 데이터가 자기 정체성을 못 가짐. 둘 다 두되 typed Literal로 typo 차단 + Stage 00 invariant로 silent mismatch 차단 |

### S02-D4 — RunConfig 필드 (확정)

| 필드 | 타입 | default | 이유 |
|---|---|---|---|
| `target_type` | `str` | `"apartment"` | [D003](000_Architecture_Decisions.md) apartment-first |
| `atom_size_mm` | `int` | `600` | [Pipeline Overview §8](000_Pipeline_Overview.md) D006 default |
| `min_atom_side_mm` | `int` | `300` | 동일 |
| `door_min_boundary_mm` | `int` | `800` | 동일 |
| `random_seed` | `int \| None` | `None` | 재현성. 미지정 시 비결정 |
| `debug_run_id` | `str \| None` | `None` | 미지정 시 자동 생성 |

→ 6개. 각 Stage별 score weight 같은 건 *그 Stage* Step에서 추가.

**확장 정책 (S02-D4 보강)**:

- 새 필드는 **default 값 필수**. 그래야 backward-compatible (기존 `RunConfig(...)` 호출과 기존 `run_config.json` 파일 모두 영향 없음).
- 새 필드는 **추가하는 Step의 Plan §2에 결정 ID로 기록** — 예: `S11-D7 | RunConfig 확장 | growth_algorithm: str = "greedy" 추가 | D011의 첫 구현 알고리즘 명시`. git log + Plan으로 출처 추적 가능.
- schema 변경의 backward-compat은 `S02-D3` helper의 `from_dict` 동작에 의존 — missing key는 default로 채움 (§4.4 코드 보강 참조).
- 예상 확장 시점: Step 04 (fixture 선택), Step 07 (decomposition method), Step 08 (role weights), Step 11 (growth algorithm), **Step 13 (search budget 등 5~10개로 가장 큼)**, Step 14 (multi-floor).

### S02-D5 — 파일명 상수 17개 ([Pipeline Overview §12.2](000_Pipeline_Overview.md))

```python
# src/proto3/debug.py
INPUT_FILENAME                   = "input.json"
RUN_CONFIG_FILENAME              = "run_config.json"
PROGRAM_INSTANCE_FILENAME        = "program_instance.json"
REGIONS_FILENAME                 = "regions.json"
ATOMS_FILENAME                   = "atoms.json"
GRAPHS_FILENAME                  = "graphs.json"
SPINE_CANDIDATES_FILENAME        = "spine_candidates.json"
SEED_CANDIDATES_FILENAME         = "seed_candidates.json"
GROWTH_STEPS_FILENAME            = "growth_steps.json"
PRE_REPAIR_VALIDATION_FILENAME   = "pre_repair_validation.json"
REPAIR_OPERATIONS_FILENAME       = "repair_operations.json"
POST_REPAIR_VALIDATION_FILENAME  = "post_repair_validation.json"
FAILURE_RECORDS_FILENAME         = "failure_records.json"
NO_GOOD_RECORDS_FILENAME         = "no_good_records.json"
FINAL_LAYOUT_FILENAME            = "final_or_invalid_layout.json"
# SVG는 stage별 — 별도 prefix 함수
STAGE_SVG_PREFIX                 = "stage_"
STAGE_SVG_SUFFIX                 = ".svg"
```

→ 15 JSON + 2 SVG prefix/suffix = 17. SVG는 동적 (stage_04_regions.svg 등) 이라 헬퍼 함수로:

```python
def stage_svg_filename(stage_num: int, name: str) -> str:
    return f"{STAGE_SVG_PREFIX}{stage_num:02d}_{name}{STAGE_SVG_SUFFIX}"
```

---

## 3. 모듈 구조 (목표 상태)

Step 02 종료 시점의 `src/proto3/` 트리.

```text
src/proto3/
├── __init__.py            [기존 — placeholder docstring 그대로 유지. schema re-export 추가는 Step 03]
├── config.py              [신규 — RunConfig]
├── debug.py               [신규 — DebugArtifact + 파일명 상수 + 폴더 헬퍼]
└── schema/                [신규 패키지]
    ├── __init__.py        [신규 — sub-module re-export]
    ├── input.py           [신규 — BuildingInput, FloorInput, PersistentAnchor]
    ├── program.py         [신규 — ProgramInstance, SpaceUnitSpec, ClusterSpec, AccessPolicy]
    ├── region_atom.py     [신규 — Region, RegionSet, Atom, AtomSet, ContactGraph]
    ├── candidate.py       [신규 — HubCandidate, TerminalCandidate, SpineCandidate, SlotCandidate, SeedCandidate]
    ├── growth.py          [신규 — GrowthResult, LayoutCandidate]
    ├── validation.py      [신규 — ValidationResult, FailureRecord, NoGoodRecord]
    └── serialize.py       [신규 — to_dict, from_dict, to_json, from_json]
```

### 24개 dataclass 분배

| 파일 | 클래스 수 | 클래스 |
|---|:---:|---|
| `schema/input.py` | 3 | BuildingInput, FloorInput, PersistentAnchor |
| `schema/program.py` | 4 | ProgramInstance, SpaceUnitSpec, ClusterSpec, AccessPolicy |
| `schema/region_atom.py` | 5 | Region, RegionSet, Atom, AtomSet, ContactGraph |
| `schema/candidate.py` | 5 | HubCandidate, TerminalCandidate, SpineCandidate, SlotCandidate, SeedCandidate |
| `schema/growth.py` | 2 | GrowthResult, LayoutCandidate |
| `schema/validation.py` | 3 | ValidationResult, FailureRecord, NoGoodRecord |
| `config.py` | 1 | RunConfig |
| `debug.py` | 1 | DebugArtifact |
| **합계** | **24** | (D012의 minimum schema 전부) |

### 다른 변경

```text
legacy/step01/                    [신규 폴더]
├── 001_Step01_ProjectSkeleton_Plan.md      [git mv from root]
└── 001_Step01_ProjectSkeleton_Tracker.md   [git mv from root]

tests/
├── test_smoke.py                [기존 — 확장: schema 모듈 import + dataclass instantiation]
└── test_serialize.py            [신규 — round-trip 1개]
```

---

## 4. 작업 목록 (자동화 실행 단위 / P5 commit 매칭)

각 항목 — (a) 명령/내용 (b) 검증 (c) commit 메시지.

### 4.1 — Step 01 docs archive + scaffold step02 module structure (commit P5 #1)

**작업 a (Step 01 docs 이동)**:

```bash
git mv 001_Step01_ProjectSkeleton_Plan.md legacy/step01/
git mv 001_Step01_ProjectSkeleton_Tracker.md legacy/step01/
```

**작업 b (모듈 골격 생성)**:

```bash
mkdir -p src/proto3/schema
touch src/proto3/schema/__init__.py
touch src/proto3/schema/input.py
touch src/proto3/schema/program.py
touch src/proto3/schema/region_atom.py
touch src/proto3/schema/candidate.py
touch src/proto3/schema/growth.py
touch src/proto3/schema/validation.py
touch src/proto3/schema/serialize.py
touch src/proto3/config.py
touch src/proto3/debug.py
```

각 빈 파일에 placeholder docstring 추가 (모듈 책임 1줄). `schema/__init__.py`는 비워둠 (re-export는 4.2에서).

**검증**:

```bash
ls legacy/step01/             # 2개 .md
ls src/proto3/schema/          # 8개 .py
/opt/conda/envs/IfcOpenHouse/bin/python -c "import proto3"   # OK (회귀 없음)
```

**commit msg**: `chore: archive step01 docs + scaffold step02 module structure`

---

### 4.2 — Schema dataclasses (commit P5 #2)

**작업**: 6개 schema 파일에 24개 dataclass 정의 (RunConfig, DebugArtifact 제외 — 4.3).

각 클래스의 필드는 [Pipeline Overview §6 vocabulary](000_Pipeline_Overview.md), [§9 Stage outputs](000_Pipeline_Overview.md), [§14 multi-floor](000_Pipeline_Overview.md)에서 추론. 미상은 `# TBD: ...` 주석.

각 파일 상단:

```python
"""<file role one-liner>"""
from __future__ import annotations
from dataclasses import dataclass, field
```

`schema/__init__.py`에 re-export:

```python
from .input import BuildingInput, FloorInput, PersistentAnchor
from .program import ProgramInstance, SpaceUnitSpec, ClusterSpec, AccessPolicy
from .region_atom import Region, RegionSet, Atom, AtomSet, ContactGraph
from .candidate import HubCandidate, TerminalCandidate, SpineCandidate, SlotCandidate, SeedCandidate
from .growth import GrowthResult, LayoutCandidate
from .validation import ValidationResult, FailureRecord, NoGoodRecord

__all__ = [...]
```

**검증**:

```bash
/opt/conda/envs/IfcOpenHouse/bin/python -c "
from proto3.schema import (
    BuildingInput, FloorInput, PersistentAnchor,
    ProgramInstance, SpaceUnitSpec, ClusterSpec, AccessPolicy,
    Region, RegionSet, Atom, AtomSet, ContactGraph,
    HubCandidate, TerminalCandidate, SpineCandidate, SlotCandidate, SeedCandidate,
    GrowthResult, LayoutCandidate,
    ValidationResult, FailureRecord, NoGoodRecord,
)
print('22 schema classes imported OK')
"
```

**commit msg**: `feat: schema dataclasses (input/program/region-atom/candidate/growth/validation)`

---

### 4.3 — RunConfig + DebugArtifact + run folder contract (commit P5 #3)

**작업 a (`src/proto3/config.py`)**: §S02-D4 표 그대로 6개 필드.

**작업 b (`src/proto3/debug.py`)**:

- `DebugArtifact` dataclass (Pipeline Overview에서 명세 미세부 — `kind: str`, `payload: dict`, `provenance: dict` 정도. 정확화는 추후 Step.)
- §S02-D5의 17개 상수 (15 JSON filename + 2 SVG prefix/suffix)
- `run_folder(run_id: str, base: Path = Path("outputs/debug_runs")) -> Path`
- `stage_svg_filename(stage_num: int, name: str) -> str`

**검증**:

```bash
/opt/conda/envs/IfcOpenHouse/bin/python -c "
from proto3.config import RunConfig
from proto3.debug import (
    DebugArtifact, run_folder, stage_svg_filename,
    INPUT_FILENAME, REGIONS_FILENAME, FAILURE_RECORDS_FILENAME,
)
c = RunConfig()
print('RunConfig:', c)
print('run_folder:', run_folder('r42'))
print('stage svg:', stage_svg_filename(8, 'spine'))
"
```

**commit msg**: `feat: RunConfig + DebugArtifact + run folder contract`

---

### 4.4 — Serialization helpers + smoke tests (commit P5 #4)

**작업 a (`src/proto3/schema/serialize.py`)**: ~30~50줄

```python
"""Serialization helpers for proto3 schema dataclasses (D012, S02-D3)."""
from __future__ import annotations
from dataclasses import is_dataclass, fields
from pathlib import Path
from typing import Any
import json

def to_dict(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_dict(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, (list, tuple)):
        return [to_dict(x) for x in obj]
    return obj

def from_dict(cls: type, data: Any) -> Any:
    if is_dataclass(cls):
        kwargs = {}
        for f in fields(cls):
            if f.name in data:
                kwargs[f.name] = from_dict(_resolve(f.type), data[f.name])
            # else: dataclass의 default가 자동 사용됨 — backward-compat 보장 (S02-D4 확장 정책)
        return cls(**kwargs)
    return data

def to_json(obj: Any, path: Path | None = None, *, indent: int = 2) -> str:
    s = json.dumps(to_dict(obj), indent=indent, ensure_ascii=False)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(s, encoding="utf-8")
    return s

def from_json(cls: type, source: str | Path) -> Any:
    if isinstance(source, Path) or (isinstance(source, str) and Path(source).exists()):
        text = Path(source).read_text(encoding="utf-8")
    else:
        text = source
    return from_dict(cls, json.loads(text))
```

`_resolve` 헬퍼는 string type hint 처리용 (S02-D11 forward reference).

**작업 b (`tests/test_smoke.py` 확장)**: 기존 `test_proto3_imports` 유지 + 24개 dataclass instantiation (각 클래스를 모든 필드 None / 빈 list / default로 1번씩).

**작업 c (`tests/test_serialize.py` 신설)**: `BuildingInput` round-trip 1개.

```python
def test_building_input_round_trip() -> None:
    from proto3.schema import BuildingInput
    from proto3.schema.serialize import to_json, from_json
    b1 = BuildingInput(floors=[], target_type="apartment")  # 필드 정확화 후 조정
    s = to_json(b1)
    b2 = from_json(BuildingInput, s)
    assert b1 == b2
```

**검증**:

```bash
/opt/conda/envs/IfcOpenHouse/bin/python -m pytest -q /workspace/Study_RoomLayout_proto3/tests
# → smoke tests + serialize round-trip 모두 pass
```

**commit msg**: `feat: serialization helpers + smoke tests`

---

### 4.5 — Step 02 cleanup (commit P5 #5)

**작업 a — `000_Progress_Tracker.md` 갱신**:

| 섹션 | 변경 |
|---|---|
| §1 phase | "Step 02 complete. Ready for Step 03 kickoff." |
| §1 status | "Completed, awaiting Step 03 kickoff." |
| §1 Current Step | "Step 02. Core Schema / Run Config / Debug Output Contract" |
| §2 Active Step files | `002_Step02_*` 두 파일 (Completed; pending move to legacy/step02/ at Step 03 kickoff) |
| §2 Next Step files to create | "TBD at Step 03 kickoff (e.g., 003_Step03_Visualization_Plan.md ...)" |
| §4 Next actions | Step 03 kickoff (D015/D016 워크플로우 적용) |
| §6 Step status table | 02 → "Done" |

**작업 b — Step 02 Plan/Tracker 마무리**:

- 이 Plan §변경이력 추가
- Tracker §3 진행 로그 + §5 cleanup checklist [x]

**검증**: 수동 확인 + `git status` 클린

**commit msg**: `docs: step02 cleanup (Plan/Tracker, Progress Tracker)`

---

## 5. 의도적으로 하지 않는 것 (유예)

| 항목 | 유예 이유 | 만들 시점 |
|---|---|---|
| Pydantic 도입 | [D012](000_Architecture_Decisions.md) — validation/JSON schema가 painful해질 때까지 dataclass | 실제 painful해지면 |
| Custom 타입 (Polygon, Enum, datetime, numpy) serialization 처리 | 이번 Step schema에 그런 타입 미등장 | 그 타입이 schema에 추가되는 Step (예: Polygon → Step 05) |
| RunConfig 외부 파일 로드 (YAML/TOML) | 코드 내 default로 충분 | 외부 config 필요 시 |
| Debug write 함수 (Stage가 부르는 helper) | Step 03 visualization과 묶음 | Step 03 |
| Schema validation 로직 (cardinality, area 등) | Stage 02 / Step 06 (Domain Constraint Engine) | Step 06 |
| 모든 dataclass의 정확한 필드 | Step에서 사용될 때 정확화 (TBD 표시) | 사용 Step |
| numpy adjacency matrix | 현재 contact는 list of pairs로 충분 | Step 08~ |
| Search Orchestrator state save | Step 13 | Step 13 |
| `__init__.py` re-export to top-level (`from proto3 import BuildingInput`) | Step 03~에서 정착되면 추가 | 사용 패턴 보고 |
| Plan §A | D016 권장 — 코드는 git에 있음 | (이번 Step 영구 생략) |

---

## 6. 위험 / 불확실성

| 위험 | 평가 | 대응 |
|---|---|---|
| Forward reference type hint가 `from_dict`에서 안 풀림 | 중. `_resolve` 헬퍼로 string type hint 처리 필요 | typing.get_type_hints로 fallback. round-trip 테스트로 즉시 발견 |
| Pipeline Overview에 명시 안 된 필드를 추측해서 넣다가 다음 Step과 충돌 | 중. Q2-B 정책 (TBD 주석)으로 완화 | TBD인 필드는 정확화 시점에 변경 자유. 이번 Step에선 *추측* 금지 |
| 24개 dataclass 한 commit이 너무 큼 (P5 #2) | 낮. 의미적으로 한 묶음. P7로 분할 옵션 있음 | review 어려우면 다음 Step 회고에서 P7 검토 |
| `git mv`가 IDE에 의해 untracked 상태로 잡힘 | 낮. Plan §4.1에서 명시적 git mv 사용 | mv 후 `git status` 확인 |
| `from __future__ import annotations` 누락 시 forward ref 깨짐 | 낮. 4.2에서 모든 schema 파일에 명시 | 명시 |

---

## 7. 다음 Step과의 연결

Step 03 (Visualization Renderer / Visual Vocabulary):

- 이 Step의 schema dataclass들을 **입력**으로 사용
- DebugArtifact 폴더 구조에 SVG 추가 (`stage_NN_<name>.svg`)
- 시각화 layer 구현 시 dataclass 필드를 직접 읽음 → 필드 누락 발견 시 이 Plan/Tracker가 아니라 Step 03의 issue로 기록 (Step은 close됨)
- `proto3/__init__.py`의 placeholder 주석을 *실제 export*로 전환할지 결정 (Step 03)
- Debug write 함수 (Stage가 부르는) 구현 — Stage가 fixture에서 시각화로 가는 e2e

Step 02에서는 **schema 정의와 직렬화 인프라까지만**. 시각화/실제 write는 Step 03.

---

## 8. Branch / Commit 전략 (D015 첫 적용)

### Branch

- **이름**: `step02-core-schema`
- **상태**: 이미 checkout됨 (2026-05-04, push 직후)
- **컨벤션**: `stepNN-<kebab-name>` ([D015](000_Architecture_Decisions.md))

### Commit 단위 (P5)

| # | §4 | commit msg |
|---|---|---|
| 1 | 4.1 | `chore: archive step01 docs + scaffold step02 module structure` |
| 2 | 4.2 | `feat: schema dataclasses (input/program/region-atom/candidate/growth/validation)` |
| 3 | 4.3 | `feat: RunConfig + DebugArtifact + run folder contract` |
| 4 | 4.4 | `feat: serialization helpers + smoke tests` |
| 5 | 4.5 | `docs: step02 cleanup (Plan/Tracker, Progress Tracker)` |

각 commit은 이전 commit 위에서 자체 검증 (DoD 일부)이 통과한 상태에서 만듦.

### Step 02 Plan/Tracker 자체의 commit

이 두 파일 ([002_Step02_CoreSchema_Plan.md](002_Step02_CoreSchema_Plan.md), `002_Step02_CoreSchema_Tracker.md`)은 **§4.1 commit (P5 #1)에 같이 포함**한다 — 별도 commit으로 분리하지 않음. 이유: §4.1이 이미 "step02 scaffold" 의미라 Plan/Tracker도 그 일부.

→ **§4.1 실제 commit 내용**: Step 01 docs 이동 + Step 02 Plan/Tracker 추가 + 모듈 골격.

### Step 종료 시 (모든 commit 완료 후)

D015 절차:

```bash
git checkout main
git merge --no-ff step02-core-schema -m "Merge branch 'step02-core-schema' into main"
git branch -d step02-core-schema
git push origin main
```

push 시점은 사용자 확인 후.

---

## 변경 이력 (이 Plan 자체)

| 날짜 | 변경 |
|---|---|
| 2026-05-04 | 초기 작성. §0–§8. 결정 S02-D1~D12 합의. Plan §A 생략 (D016/S02-D7 첫 적용). |
| 2026-05-04 | RunConfig 확장 우려 의논 — S02-D4에 확장 정책 단락 추가. §4.4 `from_dict` 코드를 missing-key default 처리로 보강 (backward-compat 보장). |
| 2026-05-04 | Step 02 cleanup. DoD-1~11 모두 통과. P5 #1~#5 commit (5개) on `step02-core-schema`. branch는 main으로 `--no-ff` merge 후 삭제. |
| 2026-05-06 | 사후 리뷰 후속 #1 (docs only). `Status: Active → Completed`. DoD-2 표기를 "22 schema + RunConfig/DebugArtifact는 DoD-3/4"로 정리(§0/§1 일관). `__init__.py` future export 주석에서 `RunConfig`/`DebugArtifact` 위치를 `.config`/`.debug`로 정정. |
| 2026-05-06 | 사후 리뷰 후속 #2 (코드 + §2 결정). S02-D13 추가 — `from_dict`에 입력 타입/unknown key strict 검증 (missing key는 기존 default fallback 유지). S02-D14 추가 — `TargetType` Literal 별칭, `BuildingInput.target_type`/`RunConfig.target_type` 둘 다 `TargetType`, `assert_target_consistent()` 헬퍼로 Stage 00 invariant 명시. 테스트 5개 추가, 14 passed. |
