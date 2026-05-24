# 001 Step 01 — Project Skeleton / Global Docs Plan

Status: Completed / Archived
Scope: Step 01에서 만들 폴더/파일/설정의 구체 작업 목록과 결정 기록. 자동화 실행 단위까지 포함.
Last updated: 2026-05-03

---

## 0. Purpose

이 문서는 **Plan(결정 living doc)**이다. 작업하면서 합의한 결정이 누적되는 곳이며, 자동화/실행 주체가 이 문서만 보고 작업할 수 있도록 충분히 구체적이어야 한다.

역할 분리:

| 문서 | 역할 | 업데이트 주기 |
|---|---|---|
| **이 Plan** | 결정 기록, 작업 사양, 인라인 자료 | 의논 중에는 자주, 결정 후엔 동결 |
| **Step Tracker** | 진행 로그, 체크리스트 | 작업하며 수시 |
| **000_Progress_Tracker** | Step 단위 마일스톤 | Step 시작/종료 시 |

Cross-reference:

- Framework / Step map: [000_Pipeline_Overview.md §15](../../000_Pipeline_Overview.md)
- Repo file policy: [000_Pipeline_Overview.md §16](../../000_Pipeline_Overview.md)
- .gitignore policy: [000_Pipeline_Overview.md §17](../../000_Pipeline_Overview.md)
- Decisions referenced: D002, D012, D014 in [000_Architecture_Decisions.md](../../000_Architecture_Decisions.md)
- 작업 스타일: [000_User_Profile.md](../../000_User_Profile.md)

---

## 1. Definition of Done

Step 01은 다음이 모두 만족되면 종료된다.

| # | 조건 | 검증 방법 |
|---|---|---|
| DoD-1 | 아래 §3의 디렉토리 트리가 모두 존재 | `ls`로 확인 |
| DoD-2 | `.gitignore`가 §A.1 내용과 일치 | `diff` |
| DoD-3 | `pyproject.toml`이 §A.2 내용과 일치 | `diff` |
| DoD-4 | `IfcOpenHouse` 환경에서 `pip install -e .` 통과 | exit 0 |
| DoD-5 | `pytest -q` 실행 시 smoke test 1개 통과 | `1 passed` |
| DoD-6 | `git status`에서 두 `.gitkeep`이 staged 가능 상태 | `git status`에 보임 |
| DoD-7 | `000_Progress_Tracker.md`가 Step 01 완료 상태로 갱신됨 | `grep` 또는 수동 확인 |
| DoD-8 | `001_Step01_ProjectSkeleton_Tracker.md`에 모든 작업이 ✅ | 수동 확인 |

---

## 2. 결정 기록

이 Step 진행 중 합의된 결정. 추후 변경할 때는 이 표를 갱신하고 reason을 갱신한다.

| ID | 항목 | 결정 | 이유 |
|---|---|---|---|
| S01-D1 | `src/` 패키지 이름 | `proto3` | 글로벌 문서가 자기 자신을 proto3로 부름 ([Pipeline Overview §0](../../000_Pipeline_Overview.md)) |
| S01-D2 | Python 프로젝트 setup 도구 | `pyproject.toml`만 | 단일 파일에 build/test/meta 통합. requirements.txt는 유예 |
| S01-D3 | 빌드 백엔드 | `setuptools` (>=68) | 가장 보편적, 외부 deps 적음 |
| S01-D4 | Python 최소 버전 | `>=3.11` | 작업 환경 `IfcOpenHouse` conda env 기준 (Python 3.11.15) |
| S01-D5 | 작업 환경 | `conda activate IfcOpenHouse`. **자동화/스크립트 호출 시에는 환경 binary 절대경로 사용** (`/opt/conda/envs/IfcOpenHouse/bin/python`) | 기존 환경 재사용. pytest 9.0.3 이미 포함. `conda run -n IfcOpenHouse <cmd>`가 일부 명령(`pip` 등)에서 base 환경으로 fallback하는 현상 관찰 (Tracker I-2) |
| S01-D6 | 테스트 프레임워크 | pytest | `.gitignore`의 `.pytest_cache` 항목과 자연스럽게 일치 |
| S01-D7 | `src/proto3/__init__.py` 내용 | placeholder 주석 (C3) — 모듈 docstring + 추후 export 예정 항목들을 주석으로 | 향후 Step 02~의 schema export 위치를 미리 명시. 코드는 아직 없음 |
| S01-D8 | `pyproject.toml` `[project] name` | `proto3` | 패키지명과 동일하게 단순화 |
| S01-D9 | README 작성 | **유예** | 글로벌 문서 4개로 충분. 외부 공개/협업자 시점에 결정 |
| S01-D10 | `outputs/`, `experiments/`, `legacy/` 미리 생성 | 모두 지금 생성 | 빈 폴더라도 .gitkeep으로 의도 명시. 추후 사용 시점에 디렉토리 생성 잊지 않도록 |
| S01-D11 | IDE/툴 작업 디렉토리(`.claude/` 등) 처리 | repo-local `.gitignore`에 추가 | 작업 중 `.claude/`가 untracked로 잡힘 (Tracker I-1). 옵션 (a) 채택: repo-local 명시 → 다른 옵션(전역 gitignore, tracked) 대비 의도가 repo에 같이 보존됨. **D014 글로벌 정책 갱신은 유예** — 다른 IDE(`.vscode/`, `.idea/`) 사용자가 합류할 때 함께 결정 |
| S01-D12 | Python build/packaging artifact 처리 (`*.egg-info/`) | repo-local `.gitignore`에 `*.egg-info/` 추가 | commit 직전 `pip install -e .`이 만든 `src/proto3.egg-info/`가 staged됨 (Tracker I-3). 옵션 (a) 채택: 발생한 패턴만 추가. `build/`, `dist/`는 미발생 → 유예. **D014 글로벌 정책 갱신은 유예** — S01-D11과 같은 흐름으로 일괄 검토 |

---

## 3. 디렉토리 구조 (목표 상태)

Step 01 종료 시점의 repo 트리.

```text
Study_RoomLayout_proto3/
├── .gitignore                                    [신규]
├── pyproject.toml                                [신규]
│
├── 000_Pipeline_Overview.md                      [기존]
├── 000_Architecture_Decisions.md                 [기존]
├── 000_Progress_Tracker.md                       [기존, §7에서 갱신]
├── 000_User_Profile.md                           [기존]
│
├── 001_Step01_ProjectSkeleton_Plan.md            [신규 — 이 문서]
├── 001_Step01_ProjectSkeleton_Tracker.md         [신규]
│
├── src/                                          [신규]
│   └── proto3/                                   [신규]
│       └── __init__.py                           [신규]
│
├── fixtures/                                     [신규, 비어있음]
│   └── .gitkeep                                  [신규]
│
├── tests/                                        [신규]
│   ├── __init__.py                               [신규]
│   └── test_smoke.py                             [신규]
│
├── outputs/                                      [신규]
│   └── debug_runs/                               [신규]
│       └── .gitkeep                              [신규, .gitignore negation]
│
├── experiments/                                  [신규]
│   └── runs/                                     [신규]
│       └── .gitkeep                              [신규, .gitignore negation]
│
└── legacy/                                       [신규, 비어있음]
    └── .gitkeep                                  [신규]
```

각 폴더의 책임:

| 폴더 | 책임 | tracked 정책 |
|---|---|---|
| `src/proto3/` | 패키지 코드. 모든 import의 출발점 | 전부 tracked |
| `fixtures/` | 도메인 자산 (apartment footprints, programs 등 hand-authored data) | 전부 tracked |
| `tests/` | pytest 테스트 코드 | 전부 tracked |
| `outputs/debug_runs/` | 단일 candidate 1회 run의 결과 ([Pipeline Overview §12.2](../../000_Pipeline_Overview.md)) | 폴더 tracked, 내용 ignored |
| `experiments/runs/` | 여러 run 묶음, 파라미터 스윕, 비교 실험 | 폴더 tracked, 내용 ignored |
| `legacy/` | 완료된 Step의 plan/tracker archive (`legacy/stepXX/`) | 전부 tracked |

설계 원칙: **각 폴더는 변경 주기, 추적 정책, 사용처가 서로 다르기 때문에 분리한다.**

---

## 4. 작업 목록 (자동화 실행 단위)

각 작업은 (a) 명령/내용 (b) 검증을 포함한다. Tracker에서 같은 번호로 진행 상태를 추적한다.

### 4.1 디렉토리 생성

명령:

```bash
mkdir -p src/proto3 fixtures tests outputs/debug_runs experiments/runs legacy
```

검증:

```bash
ls -d src/proto3 fixtures tests outputs/debug_runs experiments/runs legacy
# → 6개 모두 존재해야 함
```

### 4.2 `.gitkeep` 배치

대상:

| 경로 | 이유 |
|---|---|
| `outputs/debug_runs/.gitkeep` | `.gitignore`가 내용물 ignore + `.gitkeep` negation |
| `experiments/runs/.gitkeep` | 동일 |
| `fixtures/.gitkeep` | 빈 폴더가 git에 들어가도록 |
| `legacy/.gitkeep` | 동일 |

명령:

```bash
touch outputs/debug_runs/.gitkeep experiments/runs/.gitkeep fixtures/.gitkeep legacy/.gitkeep
```

검증: `git status` 시 4개 파일이 untracked로 보임.

### 4.3 `.gitignore` 작성

내용: §A.1을 그대로 작성.

검증:

```bash
git check-ignore outputs/debug_runs/foo.json
# → "outputs/debug_runs/foo.json" 출력되면 ignore 매치
git check-ignore outputs/debug_runs/.gitkeep
# → 매치 없음 (negation 정상 작동)
```

### 4.4 `pyproject.toml` 작성

내용: §A.2를 그대로 작성.

검증 (S01-D5에 따라 환경 binary 절대경로 사용):

```bash
/opt/conda/envs/IfcOpenHouse/bin/python -m pip install -e /workspace/Study_RoomLayout_proto3
# → "Successfully installed proto3-0.0.0"
/opt/conda/envs/IfcOpenHouse/bin/python -c "import proto3; print(proto3.__file__)"
# → src/proto3/__init__.py 경로가 출력되어야 함
```

### 4.5 `src/proto3/__init__.py` 작성

내용: §A.3을 그대로 작성. 결정 S01-D7(placeholder 주석)에 따름.

### 4.6 `tests/__init__.py` + `tests/test_smoke.py` 작성

`tests/__init__.py`: 빈 파일.

`tests/test_smoke.py` 내용: §A.4를 그대로 작성.

검증 (S01-D5에 따라 환경 binary 절대경로 사용):

```bash
/opt/conda/envs/IfcOpenHouse/bin/python -m pytest -q /workspace/Study_RoomLayout_proto3/tests
# → "1 passed" 한 줄 포함
```

### 4.7 `001_Step01_ProjectSkeleton_Tracker.md` 생성

내용: §A.5의 템플릿을 그대로 작성. 작업 진행 시 체크박스 갱신.

### 4.8 `000_Progress_Tracker.md` 갱신 (Step 종료 시점)

수정 위치:

| 섹션 | 변경 |
|---|---|
| §1 Current status → Current Step status | `Ready to begin.` → `Completed.` |
| §1 Current status → Current Step | `Step 01. ...` → `Step 02. Core Schema / Run Config / Debug Output Contract` (또는 다음에 시작할 Step) |
| §2 Active files → Active Step files | `None yet.` → 새 Step의 파일들로 갱신 또는 `None yet.` 유지 |
| §6 Step status table | 01 행 Status를 `Done` 으로 |

이 갱신은 **Step 01 마지막 작업**이다. 이전 작업이 모두 끝나야 한다.

---

## 5. 의도적으로 하지 않는 것 (유예)

User Profile의 *"실제 필요해질 때까지 유예"* 원칙을 명시적으로 적용한 항목들. 나중에 "왜 안 했지?"의 답이 됨.

| 항목 | 유예 이유 | 만들 시점 |
|---|---|---|
| `README.md` | 글로벌 docs로 충분 (S01-D9) | 외부 공개/협업자 합류 시 |
| `docs/` 폴더 | 글로벌 문서가 root에 있고 Step 문서도 root에 있음 | 외부 공개용 문서 생기면 |
| `scripts/` 폴더 | 아직 CLI/스크립트 없음 | 첫 스크립트 생성 시 |
| `notebooks/` 폴더 | 아직 노트북 안 씀 | 실제 사용 시 |
| `configs/` 폴더 | RunConfig는 dataclass([D012](../../000_Architecture_Decisions.md))로 코드 내 정의 | 외부 config 파일 필요 시 |
| `.github/workflows/` (CI) | 협업자/배포 없음 | CI 필요 시 |
| `requirements.txt` | `pyproject.toml`로 충분 (S01-D2) | 별도로 만들지 않음 |
| `src/proto3/` 하위 모듈 트리 | Step 02의 결정 영역 | Step 02에서 |
| lint/format 도구 (ruff 등) 설정 | 아직 코드가 없음 | 첫 실제 모듈 작성 시 |

---

## 6. 위험 / 불확실성

| 위험 | 평가 | 대응 |
|---|---|---|
| `pip install -e .`가 IfcOpenHouse 환경의 pinned 버전과 충돌 | 낮음. proto3 자체에 의존성 없음 (§A.2 deps 비어있음) | 충돌 시 deps 추가 시점에 다시 검토 |
| pytest 9.x의 새 동작이 smoke test를 깨뜨림 | 매우 낮음. smoke test는 단순 import | 발생 시 pytest 버전 핀 추가 |
| `.gitignore` negation 패턴이 OS/git 버전에 따라 다르게 동작 | 매우 낮음. 표준 git 기능 | DoD-6의 `git status` 검증 |
| 한자/한글 파일명 (`000_User_Profile.md`)이 mac/linux/windows에서 다르게 보임 | 발생 안 함 (모두 ASCII) | — |

Step 01은 mechanical한 작업이라 위험은 거의 없음.

---

## 7. 다음 Step과의 연결

Step 02 (Core Schema / Run Config / Debug Output Contract)에서 다룰 것:

- `src/proto3/` 하위 모듈 트리 결정 (`schema/`, `runtime/`, `debug/` 등)
- 기본 dataclass stubs ([D012](../../000_Architecture_Decisions.md)의 minimum schema 목록)
- RunConfig
- Debug output 디렉토리 명명 규칙
- `__init__.py`의 주석 placeholder를 실제 export로 전환

이 Plan에서는 위 항목을 결정하지 않는다. `src/proto3/__init__.py`는 placeholder 주석만 포함한다.

---

## 변경 이력 (이 Plan 자체)

| 날짜 | 변경 |
|---|---|
| 2026-05-03 | 초기 작성. §0–§7 + Appendix A 채움. 결정 S01-D1~D10 합의. |
| 2026-05-03 | 작업 중 발견 이슈 반영. S01-D11 (`.claude/` ignore 처리) + S01-D5 보완 (환경 binary 절대경로). Plan §A.1, §4.4, §4.6 갱신. |
| 2026-05-03 | Step 01 cleanup. **Appendix A 제거** (워크플로우 결정: 단발성 scaffolding). DoD-1~8 모두 통과. |
| 2026-05-03 | commit 직전 발견 I-3 — `*.egg-info/`가 staged됨. S01-D12 추가. .gitignore 갱신. |
| 2026-05-03 | Step 01 commit 후 워크플로우 결정 글로벌화 — D015 (branch+commit), D016 (Plan/Tracker structure), H010 추가 ([000_Architecture_Decisions.md](../../000_Architecture_Decisions.md)) |
