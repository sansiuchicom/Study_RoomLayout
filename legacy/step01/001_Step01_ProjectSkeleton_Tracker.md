# 001 Step 01 — Project Skeleton / Global Docs Tracker

Status: In progress
Started: 2026-05-03
Last updated: 2026-05-03
Companion plan: [001_Step01_ProjectSkeleton_Plan.md](001_Step01_ProjectSkeleton_Plan.md)

---

## 0. Purpose

이 문서는 **진행 로그 / 체크리스트**. [Plan](001_Step01_ProjectSkeleton_Plan.md)과 1:1 매칭되며, 작업하면서 수시로 갱신한다.

역할 구분:

| | Plan | Tracker |
|---|---|---|
| 무엇 | 결정·사양·인라인 자료 | 진행 상태·로그·이슈 |
| 갱신 | 의논 중에는 자주, 결정 후 동결 | 작업하며 수시 |

---

## 1. 작업 체크리스트

Plan §4의 항목과 **동일한 번호**를 유지한다.

| # | 작업 | 상태 | 완료일 | 비고 |
|---|---|:---:|---|---|
| 4.7 | 이 Tracker 생성 | [x] | 2026-05-03 | self-referential — 작성과 동시에 완료 |
| 4.1 | 디렉토리 생성 (`src/proto3/`, `fixtures/`, `tests/`, `outputs/debug_runs/`, `experiments/runs/`, `legacy/`) | [x] | 2026-05-03 | 6개 모두 생성 확인 |
| 4.2 | `.gitkeep` 4개 배치 | [x] | 2026-05-03 | `outputs/debug_runs/`, `experiments/runs/`, `fixtures/`, `legacy/` |
| 4.3 | `.gitignore` 작성 (Plan §A.1) | [x] | 2026-05-03 | Plan §A.1과 일치. negation 작동 확인 |
| 4.4 | `pyproject.toml` 작성 (Plan §A.2) | [x] | 2026-05-03 | `pip install -e .` 통과 |
| 4.5 | `src/proto3/__init__.py` 작성 (Plan §A.3) | [x] | 2026-05-03 | placeholder docstring (S01-D7) |
| 4.6 | `tests/__init__.py` + `tests/test_smoke.py` 작성 (Plan §A.4) | [x] | 2026-05-03 | `pytest -q` → 1 passed |
| 4.8 | `000_Progress_Tracker.md` 갱신 | [x] | 2026-05-03 | §1 status, §2 active files, §4 next actions, §6 table 갱신 |

실행 순서: 4.7 → 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 → (검증) → 4.8

---

## 2. DoD 검증 결과

[Plan §1](001_Step01_ProjectSkeleton_Plan.md)의 DoD-1 ~ DoD-8.

| # | 조건 | 결과 | 검증 시각 |
|---|---|:---:|---|
| DoD-1 | 디렉토리 트리 모두 존재 | [x] | 2026-05-03 |
| DoD-2 | `.gitignore` 일치 | [x] | 2026-05-03 |
| DoD-3 | `pyproject.toml` 일치 | [x] | 2026-05-03 |
| DoD-4 | `pip install -e .` 통과 | [x] | 2026-05-03 (Successfully installed proto3-0.0.0) |
| DoD-5 | `pytest -q` → 1 passed | [x] | 2026-05-03 (1 passed in 0.00s) |
| DoD-6 | `git status`에 두 `.gitkeep` 보임 | [x] | 2026-05-03 (4개 모두 untracked로 보임) |
| DoD-7 | `000_Progress_Tracker.md` Step 01 완료로 갱신 | [x] | 2026-05-03 |
| DoD-8 | 이 Tracker 모든 작업 ✅ | [x] | 2026-05-03 |

---

## 3. 진행 로그 (시간순)

| 시각 | 이벤트 |
|---|---|
| 2026-05-03 | Plan 작성 완료. 결정 S01-D1 ~ S01-D10 합의 |
| 2026-05-03 | 이 Tracker 생성 |
| 2026-05-03 | §4.1 디렉토리 6개 생성, §4.2 `.gitkeep` 4개 배치, §4.3 `.gitignore` 작성. 검증 통과 |
| 2026-05-03 | 이슈 발견 — `.claude/` 디렉토리가 untracked. Plan에 미정의 (§4 참조) |
| 2026-05-03 | I-1 해결 — 옵션 (a) 채택. `.gitignore` + Plan §A.1 + Plan §2 (S01-D11) 갱신 |
| 2026-05-03 | §4.4 `pyproject.toml`, §4.5 `__init__.py`, §4.6 smoke test 작성. 검증 통과 |
| 2026-05-03 | 이슈 발견 I-2 — `conda run -n IfcOpenHouse pip ...`이 base 환경 호출. S01-D5 보완, Plan §4.4/§4.6 검증 명령 갱신 |
| 2026-05-03 | 워크플로우 결정 — Step 단위 branch + per-작업 commit + no-squash merge. Step 01은 예외(이미 main 작업). 메모리 `feedback_branch_commit_workflow` 저장 |
| 2026-05-03 | Step 01 cleanup. Plan §A 제거. `000_Progress_Tracker.md` 갱신. DoD-1~8 모두 ✅ |
| 2026-05-03 | commit 직전 발견 I-3 — `src/proto3.egg-info/`가 staged됨. `.gitignore`에 `*.egg-info/` 추가, S01-D12로 결정 기록, unstage |
| 2026-05-03 | Step 01 commit (`6475f7c feat: step01 project skeleton`) |
| 2026-05-03 | 워크플로우 결정 글로벌화 — D015/D016 + H010을 [000_Architecture_Decisions.md](000_Architecture_Decisions.md)에 추가. 별도 docs commit 예정 |

---

## 4. 발견 이슈 / Plan 변경

작업 중 Plan 갱신을 유발한 사항을 기록한다.

### I-1. `.claude/` 디렉토리 처리 (2026-05-03) — **해결**

`git status`에 `.claude/` 가 untracked로 잡힘. Claude Code/IDE가 만든 작업 디렉토리.

처리 옵션:

- (a) `.gitignore`에 `.claude/` 추가 → repo-local 명시
- (b) tracked로 둠 → 세션 데이터가 git에 들어감 (비추천)
- (c) `~/.gitignore_global`에 추가 → 이 repo만의 결정 아님

**결정 (2026-05-03)**: 옵션 (a). Plan §2에 S01-D11로 기록. Plan §A.1과 `.gitignore` 모두 갱신.

D014/Pipeline Overview §17의 글로벌 .gitignore 정책 갱신은 **유예** — 다른 IDE(`.vscode/`, `.idea/`) 사용자 합류 시 일괄 검토.

### I-2. `conda run -n IfcOpenHouse` 가 일부 명령에서 base 환경 호출 (2026-05-03) — **해결**

§4.4 검증 중 `conda run -n IfcOpenHouse pip install -e .` 실행 시 다음 에러 발생:

```
ERROR: Package 'proto3' requires a different Python: 3.10.12 not in '>=3.11'
Defaulting to user installation because normal site-packages is not writeable
```

즉 `conda run -n IfcOpenHouse pip ...`이 IfcOpenHouse(Python 3.11.15)의 pip이 아니라 base 환경(Python 3.10.12)의 pip을 호출. 같은 이름의 명령으로 `conda run -n IfcOpenHouse python --version`은 정상적으로 3.11.15 반환했었음 → `conda run`의 동작이 호출 명령(`python` vs `pip`)에 따라 일관되지 않음.

근본 원인 추정: shebang 또는 `conda run`의 PATH 처리 차이.

**대응 (2026-05-03)**: 환경 binary 절대경로 직접 사용으로 회피.

- `/opt/conda/envs/IfcOpenHouse/bin/python -m pip install ...`
- `/opt/conda/envs/IfcOpenHouse/bin/python -m pytest ...`

S01-D5 보완. Plan §4.4 / §4.6 검증 명령 갱신. 자동화도 절대경로 호출 사용.

근본 원인 디버깅은 **유예** — workaround로 충분. 다른 환경에서 같은 문제 재발 시 재조사.

### I-3. `*.egg-info/` 가 staged됨 (2026-05-03) — **해결**

commit 직전 `git add` 후 `src/proto3.egg-info/` 4개 파일이 staged 목록에 잡힘. `pip install -e .`이 만든 setuptools build artifact.

처리 옵션:

- (a) `*.egg-info/` 만 `.gitignore`에 추가 (발생한 패턴만)
- (b) `*.egg-info/`, `build/`, `dist/` 묶음 추가 (Python build artifact 일반)

**결정 (2026-05-03)**: 옵션 (a). Plan §2에 S01-D12로 기록. `.gitignore`에 `# Python build / packaging artifacts` 그룹 + `*.egg-info/` 추가. unstage. `build/`, `dist/`는 미발생이라 유예.

D014 글로벌 정책 갱신은 **유예** — S01-D11과 같은 흐름으로 일괄 검토.

---

## 5. Step 종료 시 cleanup 체크리스트

Step 01 종료 직전에 순서대로 확인.

- [x] §1의 모든 작업이 [x] (4.1–4.8)
- [x] §2의 모든 DoD가 [x] (DoD-1–8)
- [x] `git status`로 의도하지 않은 untracked/dirty 없음 확인 (commit 직전 검증)
- [x] [`000_Progress_Tracker.md`](000_Progress_Tracker.md) 갱신 (Plan §4.8 절차)
- [x] **Plan §A (Appendix 인라인 자료) 제거** — 첫 Step에서만 필요. 사용자 결정(2026-05-03)
- [ ] 이 두 파일(`001_Step01_ProjectSkeleton_Plan.md`, `001_Step01_ProjectSkeleton_Tracker.md`)을 [`legacy/step01/`](legacy/) 로 이동 — **Step 02 kickoff 시점**으로 이연 (사용자 결정 2026-05-03)
- [x] git commit — 옵션 X (한 번에). 컨벤션 합의: `git commit -m "feat: 제목, 간단한 내용"` 1~2줄 (메모리 `feedback_branch_commit_workflow` 참조)

---

## 6. 변경 이력 (이 Tracker 자체)

| 날짜 | 변경 |
|---|---|
| 2026-05-03 | 초기 생성. §1 4.7 체크 완료, 나머지 pending |
