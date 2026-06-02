# 007 Step 07 — Entry Point + Labeling Tracker

Status: In progress (on `step07-entrypoint` — D005 triggers fired)
Type: Step tracker
Branch: `step07-entrypoint`
Last updated: 2026-06-02

Mirrors `007_Step07_EntryPoint_Plan.md` §4 work items (proto3:D016).
Plan = the contract; Tracker = execution state + decisions-during-build.

---

## 1. Plan §4 work items

| # | Work item | Status | Commit |
|---|---|---|---|
| 4.1 | Kickoff — Plan/Tracker + `git mv` Step 06 → `legacy/step06/` + `viz/__init__.py` doc fix (S07-D4) + Progress Tracker | In progress | (this) |
| 4.2 | `stages/polygonize.py` (NEW) — region-id sets → room + corridor polygons (S04-D2) | Todo | — |
| 4.3 | Labeling (§3.8) — grown room → `LabeledRoom` (role/usage recovery, `area_m2`) | Todo | — |
| 4.4 | vc anchor re-insertion (S04-D4) — polygon from `VerticalAnchor.footprint` | Todo | — |
| 4.5 | Per-room post-growth area/dim gate (1.5 m² rejection) | Todo | — |
| 4.6 | `run.py` (NEW) — the `run()` join (D001) + `on_stage` hook + failure path | Todo | — |
| 4.7 | Trace infra (D006) — `StageOutput` + JSON + `manifest.json` + `RunConfig` | Todo | — |
| 4.8 | Final-layout matplotlib renderer (S01-D10) | Todo | — |
| 4.9 | Test corpus A — 33 cases through `run()` → golden `LabeledRoomLayout` | Todo | — |
| 4.10 | Test corpus B — realistic apartment fixtures + failure-injection | Todo | — |
| 4.11 | xfail resolution — corridor single-component + K>seedable graceful | Todo | — |
| 4.12 | Close — README/Tracker/Progress sync + `--no-ff` merge | Todo | — |

---

## 2. Definition of Done checklist

(Plan §1 — checked at close.)

- [ ] `run(shape, program, *, seed)` assembled (D001); per-floor loop; `on_stage` hook (default None = pure)
- [ ] Polygonization: `CorridoredLayout` region-sets → room + corridor polygons (S04-D2)
- [ ] Labeling (§3.8): 7-class role/usage recovery + `area_m2`; usage carried through (S06-D3)
- [ ] vc anchor re-insertion (S04-D4) — polygon from `VerticalAnchor.footprint_polygon`
- [ ] Per-room post-growth area/dim check (1.5 m² rejection) — distinct from Step 05 aggregate
- [ ] Failure path: `valid=False ⇒ non-empty failure_records` (proto3:D018) + `check_multi_floor_feasibility` call site (S05-D6)
- [ ] Trace infra (D006): `StageOutput` + `on_stage` + JSON serializer + `manifest.json` + minimal `RunConfig`
- [ ] Viz (S01-D10): final `LabeledRoomLayout` matplotlib renderer + `viz/__init__.py` doc fix
- [ ] Test corpus A (33 cases → run-goldens) + B (apartment fixtures + failure-injection)
- [ ] xfail: 2 Step-07 PoCs reviewed; 3 latent stay xfail
- [ ] ruff (check AND format) clean; full pytest green (conda IfcOpenHouse, GEOS 3.14.1)
- [ ] Plan/Tracker closed; S07-D series finalized; merged `--no-ff` to `main`

---

## 3. Notes / decisions during execution

(Filled as work items land — drift from Plan, surprises, sub-decisions.)

- 2026-06-02 — Kickoff. §1/§2/§4 settled over chat. Branch `step07-entrypoint`
  (S07-D1 — D005: integration [joins 03/04 + 05/06] + regression risk [first
  `run()` over the 33 geometry goldens]). Test corpus = **both** (S07-D2:
  33-case run-goldens for regression continuity + realistic apartment fixtures
  for the "valid apartment" / failure-path signal; reconciles the Pipeline
  §5.1 "6 apartment fixtures" line, which predates the 33-case corpus). Trace
  seam (S07-D3): `on_stage` hook + `StageOutput` + JSON + `manifest.json` =
  Step 07 (the hook is invasive — must thread `run()` from the start; default
  None keeps it pure); canonical SVG + GIF = Step 08. Viz (S07-D4): final
  matplotlib renderer = Step 07 (S01-D10); the existing 6 stage renderers stop
  at the region-based `CorridoredLayout`, the polygonized+labeled layout has
  none; `viz/__init__.py` off-by-one ("Step 07 (SVG visualization)" → 08)
  fixed at kickoff. **Key framing:** Step 07 is not mere wiring — `CorridoredLayout`
  carries `GrownRoom.region_ids` (region-id *sets*), so polygonization
  (S04-D2), labeling (§3.8), and the deferred anchor/per-room/connectivity
  cluster are substantive new work. Work-item spine is bottom-up:
  polygonize → label → anchor/gate → `run()` assembly → trace → viz → tests →
  xfail. Step start state verified green: 732 passed + 5 xfailed (conda
  IfcOpenHouse, GEOS 3.14.1).

---

## 4. Close summary

(Filled at close — 4.12.)
