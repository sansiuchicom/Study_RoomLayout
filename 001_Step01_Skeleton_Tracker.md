# 001 Step 01 — Project Skeleton Tracker

Status: Active
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
- [ ] **4.7** GitHub Actions CI workflow (`.github/workflows/ci.yml` written; pending push + CI green)
- [ ] **4.8** Step close — update Progress Tracker

---

## 2. Definition of Done checklist

- [ ] `pip install -e .` succeeds locally
- [ ] `python -c "import room_layout"` works
- [ ] `python -c "import room_layout.viz"` works (placeholder)
- [ ] `pytest` passes (≥ 1 test)
- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
- [ ] GitHub Actions CI green on `main`
- [ ] `.gitignore` excludes pycache / `.venv` / outputs / caches
- [ ] Output directory scaffold present (D006) — `outputs/{debug_runs,viz}/`,
      `experiments/{notebooks,runs}/`, `tests/golden/` each with `.gitkeep`
- [ ] `legacy/.gitkeep` exists (`proto3:D016` archive target)
- [ ] `docs/000_Progress_Tracker.md` §1 + §2 updated
- [ ] All Plan §4 items checked above
- [ ] Visualization status documented (Step 01: no viz output —
      scaffold-only; placeholder `room_layout.viz` package created)

---

## 3. Notes / decisions during execution

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

---

## 4. Close summary

_Populated at Step close (work item 4.8). One-paragraph retro: what
was actually built, any surprises, any items pushed forward to a later
Step._
