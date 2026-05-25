# 001 Step 01 — Project Skeleton Tracker

Status: Active
Type: Step tracker
Last updated: 2026-05-25

Mirrors Plan §4 work items 1:1 in §1 checklist (per `proto3:D016`).

---

## 1. Plan §4 work items

- [ ] **4.1** Plan + Tracker land
- [ ] **4.2** pyproject + `room_layout` package skeleton
- [ ] **4.3** viz package skeleton + `viz` optional dep group
- [ ] **4.4** Smoke test + pytest config
- [ ] **4.5** `.gitignore` (D014 carry)
- [ ] **4.6** ruff config + initial lint clean
- [ ] **4.7** GitHub Actions CI workflow
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

_Populated as Step proceeds. Per-work-item notes go here when a choice
made during execution differs from or refines Plan §2._

---

## 4. Close summary

_Populated at Step close (work item 4.8). One-paragraph retro: what
was actually built, any surprises, any items pushed forward to a later
Step._
