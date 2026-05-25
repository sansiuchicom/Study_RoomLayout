# 001 Step 01 — Project Skeleton Plan

Status: Closed (2026-05-25)
Type: Step plan
Last updated: 2026-05-25

---

## 0. Purpose

Step 01 lands the minimum project scaffold so that subsequent Steps
have a working build, test runner, lint, CI, and a place to plug in
algorithm code. **No algorithm code in Step 01 itself.**

Cross-references:

- `docs/000_Pipeline_Overview.md` §5.1 Step 01 entry (active Step map).
- `docs/000_Architecture_Decisions.md`:
  - **D005** — Solo-mode workflow (Step 01 proceeds on `main`).
  - **D013** carry — SVG-first viz roadmap (canonical viz lands at Step 07).
  - **D014** carry — debug outputs out of version control.
- `docs/000_Progress_Tracker.md` — current status; Step 01 close
  updates §1 + §2.
- Companion tracker: `001_Step01_Skeleton_Tracker.md`.

---

## 1. Definition of Done

| Item | Verification |
|---|---|
| `python -m pip install -e .` succeeds locally | `python -m pip install -e . && echo ok` |
| `python -c "import room_layout"` works | local + CI |
| `python -c "import room_layout.viz"` works (placeholder package) | local + CI |
| `pytest` passes (≥ 1 smoke test) | `pytest` exit 0 |
| `ruff check .` passes | `ruff check .` exit 0 |
| `ruff format --check .` passes | `ruff format --check .` exit 0 |
| GitHub Actions CI green on push to `main` | GitHub UI / `gh run list` |
| `.gitignore` excludes pycache / `.venv` / outputs / caches | `git status` clean after dev session |
| Output directory scaffold present (`outputs/{debug_runs,viz}/`, `experiments/{notebooks,runs}/`, `tests/golden/`) with `.gitkeep` markers per D006 | `find outputs experiments tests/golden -name .gitkeep` shows 7 entries |
| `legacy/` directory scaffolded with `.gitkeep` (`proto3:D016` archive convention) | `ls legacy/.gitkeep` exists |
| Progress Tracker §1 + §2 updated to reflect Step 01 close | docs review |
| All Plan §4 work items checked in companion Tracker §1 | tracker review |
| All §1 DoD items checked in Tracker §2 | tracker review |

---

## 2. 결정 기록

| ID | Title | Decision |
|---|---|---|
| **S01-D1** | Package name | `room_layout` — short, snake_case, repo-identity match, no detected PyPI conflict (private repo regardless). |
| **S01-D2** | Plan / Tracker location | Repo root (`001_Step01_*_Plan.md` + Tracker), per `proto3:D016` convention. `docs/000_*` reserved for canonical global docs. |
| **S01-D3** | Branch policy | `main` direct, per D005 — none of the four triggers fire (≤ 8 small commits, no regression risk, single-module scope, no design pivot expected). |
| **S01-D4** | pyproject build backend | `setuptools>=68` — carried from `archive/proto3/pyproject.toml`. No reason to switch. |
| **S01-D5** | Python version | `>=3.10`. proto3 carried `>=3.11`; lowered to `>=3.10` (2026-05-25) after `pip install -e .` rejected the dev environment's Python 3.10.12. Nothing in our scope requires 3.11-only features (union `X \| Y`, dataclass, NetworkX, shapely all run on 3.10). Re-tighten to 3.11 only if a concrete 3.11-only feature lands. |
| **S01-D6** | Linter / formatter | `ruff` (lint + format) — Python standard, single tool. proto3 had no lint config; this fills the gap. |
| **S01-D7** | CI provider | GitHub Actions, single workflow `.github/workflows/ci.yml`. |
| **S01-D8** | Runtime deps | `shapely>=2.0`, `numpy>=1.24`, `networkx>=3.0` (Cell's atom_graph / region_graph). `matplotlib` is NOT a runtime dep — moved to `viz` extra (see S01-D9). |
| **S01-D9** | Optional dep groups | `dev = [pytest, ruff]`; `viz = [matplotlib>=3.7]`. Separating `viz` signals it as a per-Step concern that can be installed independently. |
| **S01-D10** | Viz preparation | `src/room_layout/viz/__init__.py` scaffolded as a placeholder package with a convention docstring. Each subsequent Step's Plan / Tracker includes a viz item (output type + render fn + acceptance criterion, OR explicit "no viz this Step" note). Step 01 itself has no viz output — scaffold-only. |
| **S01-D11** | Output directory convention | Follows D006. Directory scaffolds (`outputs/{debug_runs,viz}/`, `experiments/{notebooks,runs}/`, `tests/golden/`) plus `legacy/` land as `.gitkeep` placeholders this Step. `legacy/.gitkeep` lands in work item 4.1; the rest land in work item 4.5 alongside `.gitignore`. Per-stage output *writers* (NN-prefixed JSON/PNG, `manifest.json`, `pipeline.gif`) are deferred to Steps 03 / 06 / 07 per D006. |

---

## 3. Directory structure (target state after Step 01)

```text
Study_RoomLayout/
├── README.md                              (existing)
├── MIGRATION_LOG.md                       (existing)
├── pyproject.toml                         (new)
├── .gitignore                             (new — D014 carry)
├── .github/
│   └── workflows/
│       └── ci.yml                         (new)
├── 001_Step01_Skeleton_Plan.md            (this file)
├── 001_Step01_Skeleton_Tracker.md         (companion)
├── docs/                                  (existing)
│   ├── 000_Architecture_Decisions.md
│   ├── 000_Pipeline_Overview.md
│   └── 000_Progress_Tracker.md
├── archive/                               (existing, read-only)
│   ├── proto3/
│   └── celllayout/
├── legacy/
│   └── .gitkeep                           (new — D016 archive convention)
├── outputs/                               (new — D006)
│   ├── .gitkeep
│   ├── debug_runs/
│   │   └── .gitkeep
│   └── viz/
│       └── .gitkeep
├── experiments/                           (new — D006)
│   ├── .gitkeep
│   ├── notebooks/
│   │   └── .gitkeep
│   └── runs/
│       └── .gitkeep
├── src/
│   └── room_layout/
│       ├── __init__.py                    (new — empty package init)
│       └── viz/
│           └── __init__.py                (new — placeholder + convention docstring)
└── tests/
    ├── golden/                            (new — D006)
    │   └── .gitkeep
    └── test_smoke.py                      (new — import smoke test)
```

---

## 4. Work items

Each item = one atomic commit. Order:

### 4.1 Plan + Tracker + `legacy/` scaffold

Files: `001_Step01_Skeleton_Plan.md`, `001_Step01_Skeleton_Tracker.md`,
`legacy/.gitkeep`.
Commit: `docs(step01): plan + tracker + legacy scaffold`.
Verification: both Step docs present at repo root; `legacy/.gitkeep`
exists (`proto3:D016` H011 deferred-archive target).

### 4.2 pyproject + `room_layout` package skeleton

Files: `pyproject.toml`, `src/room_layout/__init__.py`.
Commit: `feat(step01): scaffold pyproject + room_layout package`.
Verification: `python -m pip install -e .` succeeds; `python -c "import room_layout"` works.

### 4.3 viz package skeleton + `viz` optional dep group

Files: `src/room_layout/viz/__init__.py` (with convention docstring),
plus update to `pyproject.toml`'s `[project.optional-dependencies]`.
Commit: `feat(step01): viz package skeleton + viz optional dep group`.
Verification: `python -c "import room_layout.viz"` works;
`python -m pip install -e .[viz]` adds matplotlib.

### 4.4 Smoke test + pytest config

Files: `tests/test_smoke.py`, pyproject `[tool.pytest.ini_options]`.
Commit: `test(step01): smoke import test`.
Verification: `pytest` exits 0; one test passes.

### 4.5 `.gitignore` + output directory scaffold (D006 + D014 carry)

Files:

- `.gitignore` (`proto3:D014` carry — pycache, `.venv`, `outputs/*`,
  `experiments/*`, caches).
- `outputs/.gitkeep`, `outputs/debug_runs/.gitkeep`,
  `outputs/viz/.gitkeep`.
- `experiments/.gitkeep`, `experiments/notebooks/.gitkeep`,
  `experiments/runs/.gitkeep`.
- `tests/golden/.gitkeep`.

Commit: `chore(step01): gitignore + output dir scaffold (D006 / D014)`.

Verification: after a `pytest` run, `git status` shows no
`__pycache__/` or `.pytest_cache/` clutter; `find outputs experiments
tests/golden -name .gitkeep` returns the 7 placeholder paths.

### 4.6 ruff config + initial lint clean

Files: `pyproject.toml` `[tool.ruff]` block.
Commit: `chore(step01): ruff config`.
Verification: `ruff check .` exit 0; `ruff format --check .` exit 0.

### 4.7 GitHub Actions CI

File: `.github/workflows/ci.yml`.
Commit: `ci(step01): minimal pytest + ruff workflow`.
Verification: `gh run list --limit 1` shows green status on the
triggering push.

### 4.8 Step close

Files: `docs/000_Progress_Tracker.md` (§1 status + §2 completed table +
§3 next actions = Step 02 kickoff), this Plan's §A (strip if present).
Commit: `chore(step01): close — update progress tracker`.
Verification: Tracker §1 reads "Step 01 done"; all checklists in
companion Tracker checked.

---

## 5. 의도적으로 하지 않는 것

- **Algorithm port** — Cell Phase 3–8 modules stay in `archive/`
  through Step 01. They move to `src/` at Step 03.
- **Schema dataclass implementation** — `ShapeInput` / `ProgramRequest`
  / etc. are written in Step 02, not now. Step 01's `room_layout/`
  package is intentionally empty.
- **Real viz code** — `room_layout/viz/` is placeholder only. First
  actual render fn arrives in Step 03 alongside the algorithm port.
- **Type-checker setup** (mypy / pyright) — deferred. May land in a
  later Step when type complexity warrants.
- **Coverage thresholds** — deferred. pytest runs smoke test only at
  Step 01.
- **Pre-commit hooks** — deferred. ruff in CI is enforcement enough
  at this stage.
- **PyPI release plumbing** — out of scope (private repo).
- **`docs/` Step references** — Pipeline Overview already references
  Step 01; no new doc cross-links from Step 01 itself.

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| `room_layout` name conflicts with a hypothetical future PyPI install | Repo is private; no publishing planned. Rename is a 1-commit change if needed. |
| `matplotlib` as runtime dep bloats install | Moved to `viz` extra (S01-D9). `pip install -e .` alone is lean. |
| `ruff` default ruleset too strict, breaks empty package | Step 01 starts with `ruff` defaults; add per-rule ignores in `pyproject` only when an actual file triggers them. |
| CI runtime grows past acceptable | Step 01 uses single Python 3.10 matrix entry (matches `requires-python = ">=3.10"` per S01-D5). Multi-version matrix is a future concern. |
| GitHub Actions auth / runner availability | Public-runner free minutes are ample for a single repo. |

---

## 7. Next-Step linkage

Step 01 close → **Step 02 (Core schema port)** kickoff.

At Step 02's §4.1 commit (per `proto3:D016` H011 deferred-archive
pattern), the following bundles together:

- `git mv 001_Step01_Skeleton_*.md legacy/step01/`
- `002_Step02_CoreSchema_Plan.md` + Tracker land at repo root
- `src/room_layout/schema/` module scaffold

Step 01's `room_layout` + `room_layout.viz` packages remain at
`src/room_layout/` — they are the empty parents that Step 02 fills.

---

## A. (Reserved) Appendix — inline file contents

_Not used this Step._ Work items 4.2 / 4.5 / 4.6 / 4.7 each produce
short, well-known config files (pyproject, .gitignore, ci.yml). They
are written directly during the work item; no need for a single-use
inline appendix.
