# 001 Step 01 — Project Skeleton Tracker

Status: Closed (2026-05-25)
Type: Step tracker
Last updated: 2026-05-25

Mirrors Plan §4 work items 1:1 in §1 checklist (per `proto3:D016`).

---

## 1. Plan §4 work items

- [x] **4.1** Plan + Tracker + `legacy/` scaffold (2026-05-25)
- [x] **4.2** pyproject + `room_layout` package skeleton (committed 2026-05-25, `feat(step01): scaffold pyproject + room_layout package`)
- [x] **4.3** viz package skeleton + `viz` optional dep group (committed 2026-05-25, `d6e68dc`)
- [x] **4.4** Smoke test + pytest config (committed 2026-05-25; 3 tests pass)
- [x] **4.5** `.gitignore` + output directory scaffold (committed 2026-05-25, `c8aa06b`) — *executed ahead of 4.4*
- [x] **4.6** ruff config + initial lint clean (committed 2026-05-25 after adding `archive/`/`outputs/`/`experiments/`/`legacy/` to `extend-exclude`)
- [x] **4.7** GitHub Actions CI workflow (committed 2026-05-25; first CI run `26391806249` green in 16 s on `main`)
- [x] **4.8** Step close — Progress Tracker §1 / §2 / §3 updated, DoD checklist below complete

---

## 2. Definition of Done checklist

- [x] `pip install -e .` succeeds locally
- [x] `python -c "import room_layout"` works
- [x] `python -c "import room_layout.viz"` works (placeholder)
- [x] `pytest` passes (≥ 1 test)
- [x] `ruff check .` passes
- [x] `ruff format --check .` passes
- [x] GitHub Actions CI green on `main`
- [x] `.gitignore` excludes pycache / `.venv` / outputs / caches
- [x] Output directory scaffold present (D006) — `outputs/{debug_runs,viz}/`,
      `experiments/{notebooks,runs}/`, `tests/golden/` each with `.gitkeep`
- [x] `legacy/.gitkeep` exists (`proto3:D016` archive target)
- [x] `docs/000_Progress_Tracker.md` §1 + §2 updated
- [x] All Plan §4 items checked above
- [x] Visualization status documented (Step 01: no viz output —
      scaffold-only; placeholder `room_layout.viz` package created)

---

## 3. Notes / decisions during execution

**All entries below are RESOLVED as of Step 01 close (2026-05-25).**
Kept as a chronological record of decisions made during execution;
each issue was addressed before Step close.

- **2026-05-25 — 4.1 committed manually**: Bash classifier was
  temporarily unavailable during the commit step. User ran the two
  commits (D006 lock + Step 01 plan/tracker/legacy) by hand.
- **2026-05-25 — 4.2 files written, awaiting manual verify**: same
  classifier outage extended into 4.2. Files (`pyproject.toml`,
  `src/room_layout/__init__.py`) are on disk; verification (`pip
  install -e .`) and commit need to run manually.
- **2026-05-25 — S01-D5 Python version lowered**: `pip install -e .`
  initially rejected the dev environment's Python 3.10.12 against
  the proto3-carried `>=3.11`. Lowered to `>=3.10` (no 3.11-only
  feature in scope). Pyproject + Plan §2 updated.
- **2026-05-25 — `python -m pip` required in this dev env**: bare
  `pip` resolved to system pip (Python 3.10) while `python` was the
  IfcOpenHouse conda env's Python 3.11. `pip install -e .` installed
  to system user-local; the conda Python could not see it →
  `ModuleNotFoundError`. Fix: `python -m pip install -e .` pairs pip
  to the active interpreter. Install then landed in
  `/opt/conda/envs/IfcOpenHouse/lib/python3.11/site-packages/`.
  Subsequent `python -c "import room_layout"` returned `0.1.0`.
  Lesson for later Steps: use `python -m pip` consistently.
- **2026-05-25 — 4.2 verified**: `python -c "import room_layout;
  print(room_layout.__version__)"` returned `0.1.0`. Pending only
  the manual `git commit`.
- **2026-05-25 — 4.5 moved before 4.4**: user noticed `__pycache__/`
  and `room_layout.egg-info/` in `git status` after `4.3` install.
  Doing `.gitignore` + output-dir scaffold first keeps the working
  tree clean before `pytest` adds `.pytest_cache/` in 4.4. Plan §4
  ordering left as canonical; Tracker §1 reflects the actual
  execution order.
- **2026-05-25 — side-fix `828d40b`**: 4.2 commit (`45d3390`)
  accidentally tracked `src/room_layout.egg-info/*` (5 files) and
  `src/room_layout/__pycache__/__init__.cpython-311.pyc` because the
  user did `git add .` during manual commit (Bash classifier was
  down). Followed up `c8aa06b` (`.gitignore` landed) with `828d40b`:
  `git rm -r --cached` on both build-artifact dirs. gitignore now
  prevents recurrence. Not a Plan §4 item — side-fix commit.
- **2026-05-25 — ruff scanned `archive/`**: first `ruff check .` ran
  on `archive/proto3/` + `archive/celllayout/` and reported 291
  errors in the predecessor codebases (mostly I001 import-sort).
  Fix: added `extend-exclude = ["archive", "outputs", "experiments",
  "legacy"]` to `[tool.ruff]`. archive is read-only; we never lint it.
- **2026-05-25 — 4.7 CI green on first push**: `gh run list`
  showed `26391806249` succeed in 16 s. Single Python 3.10 matrix
  per Plan §6; no caching, no parallelism.

---

## 4. Close summary

**Built (8 commits on `main` per D005, plus 1 side-fix chore)**:

- `pyproject.toml` — setuptools, Python `>=3.10`, runtime deps
  (`shapely`/`numpy`/`networkx`), dev + viz optional extras,
  pytest + ruff config.
- `src/room_layout/` — empty top-level package with version 0.1.0 +
  canonical docstring pointing at `docs/000_*`.
- `src/room_layout/viz/` — placeholder subpackage with the per-stage
  render-fn convention docstring (D006 + S01-D10).
- `tests/test_smoke.py` — 3 smoke tests (top-level import, version
  match, viz import without matplotlib).
- `.gitignore` — `proto3:D014` carry + D006 output-dir rules.
- 7 `.gitkeep` placeholders for `outputs/{debug_runs,viz}/`,
  `experiments/{notebooks,runs}/`, `tests/golden/`, plus
  `legacy/.gitkeep` from work item 4.1 (D016 archive target).
- `.github/workflows/ci.yml` — minimal pytest + ruff CI on Python
  3.10, green in 16 s on first push.

**Surprises**:

- Conda env (IfcOpenHouse) was actually Python 3.11, but system
  `pip` defaulted to system Python 3.10 → mismatch on first
  `pip install -e .`. Resolved by always using `python -m pip`
  (recorded in §3). S01-D5 lowered `>=3.11` to `>=3.10` as a
  side-effect; staying as the new floor unless a 3.11-only feature
  arrives.
- 4.2 commit accidentally tracked `src/room_layout.egg-info/*` and
  `src/room_layout/__pycache__/__init__.cpython-311.pyc` via
  `git add .`. Side-fix `828d40b` (`git rm -r --cached`) cleaned it
  up after `.gitignore` landed. Lesson: avoid `git add .`.
- Ruff initially scanned `archive/` and surfaced 291 errors in the
  predecessor codebases. Added `extend-exclude = ["archive",
  "outputs", "experiments", "legacy"]` to lock ruff to our code only.

**Plan §4 ordering vs execution**: 4.5 (`.gitignore` + output dir
scaffold) executed before 4.4 (smoke test) to keep the working tree
clean before `pytest` generated `.pytest_cache/`. Plan §4 numbering
left as canonical; Tracker §1 reflects the actual execution order.

**Pushed to a later Step**:

- Per-stage JSON serializers + `manifest.json` writer → Step 06.
- Matplotlib renderers (Cell port) → Step 03.
- SVG canonical renderer + `make_gif()` helper → Step 07.
- ResearchBIM `Building` / `Storey` adapter → Step 08 (post-v1).
- Multi-floor orchestrator → Step 09 (post-v1).

**Next**: Step 02 (Core schema port). D005 triggers fire
(regression risk + integration work touching the whole downstream
chain), so Step 02 starts on a `step02-coreschema` branch. Branch
kickoff §4.1 commit moves `001_Step01_Skeleton_*.md` to
`legacy/step01/` per `proto3:D016` H011.
