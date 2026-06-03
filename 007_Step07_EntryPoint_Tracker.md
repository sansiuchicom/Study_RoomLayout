# 007 Step 07 — Entry Point + Labeling Tracker

Status: In progress (on `step07-entrypoint` — D005 triggers fired)
Type: Step tracker
Branch: `step07-entrypoint`
Last updated: 2026-06-03

Mirrors `007_Step07_EntryPoint_Plan.md` §4 work items (proto3:D016).
Plan = the contract; Tracker = execution state + decisions-during-build.

---

## 1. Plan §4 work items

| # | Work item | Status | Commit |
|---|---|---|---|
| 4.1 | Kickoff — Plan/Tracker + `git mv` Step 06 → `legacy/step06/` + `viz/__init__.py` doc fix (S07-D4) + Progress Tracker | Done | `cd4bc3a` |
| 4.2 | `stages/polygonize.py` (NEW) — region-id sets → room + corridor polygons (S04-D2, **+S07-D5**) | Done | `18bc4c6` |
| 4.3 | Labeling (§3.8) — grown room → `LabeledRoom` (role/usage recovery, `area_m2`) | Done | `175a576` |
| 4.4 | vc anchor re-insertion (S04-D4) — polygon from `VerticalAnchor.footprint` | Done | `098a568` |
| 4.5 | Per-room post-growth area/dim gate (1.5 m² rejection) | Done | `dd62509` |
| 4.6 | `run.py` (NEW) — the `run()` join (D001) + `on_stage` hook + failure path (**+S07-D6**) | Done | `99c0a67` |
| 4.7 | Trace infra (D006) — `StageOutput` + JSON + `manifest.json` + `RunConfig` | Todo | — |
| 4.8 | Final-layout matplotlib renderer (S01-D10) | Done | `5f925cc` |
| 4.9 | Test corpus A — 33 cases through `run()` → golden `LabeledRoomLayout` | Done | `5873294` |
| 4.10 | Test corpus B — authored fixtures (anchored / admission-fail / per-room-fail) + glob bug fix | Done | `ac185d9` |
| 4.11 | xfail resolution — corridor single-component + K>seedable graceful | Todo | — |
| 4.12 | Close — README/Tracker/Progress sync + `--no-ff` merge | Todo | — |

---

## 2. Definition of Done checklist

(Plan §1 — checked at close.)

- [x] `run(shape, program, *, seed)` assembled (D001); per-floor loop; `on_stage` hook (default None = pure)
- [x] Polygonization: `CorridoredLayout` region-sets → room + corridor polygons (S04-D2; S07-D5 — room=single Polygon loud-guard, corridor=list)
- [x] Labeling (§3.8): 7-class role/usage recovery (`name==id`) + `area_m2` (polygon, S07-D6); usage carried through (S06-D3)
- [x] vc anchor re-insertion (S04-D4) — `vc_rooms`: polygon from `VerticalAnchor.footprint_polygon` (re-insert half; subtract half in `anchors.py`)
- [x] Per-room post-growth area/dim check (`check_grown_rooms`; OBB short side; collect not raise; vc exempt) — distinct from Step 05 aggregate
- [x] Failure path: `valid=False ⇒ non-empty failure_records` (proto3:D018) + `check_multi_floor_feasibility` call site (S05-D6)
- [ ] Trace infra (D006): `StageOutput` + `on_stage` + JSON serializer + `manifest.json` + minimal `RunConfig`
- [x] Viz (S01-D10): final `LabeledFloorLayout` matplotlib renderer (`save_labeled_floor_figure`) + `viz/__init__.py` doc fix (kickoff)
- [x] Test corpus A (33 cases → run-goldens) + B (anchored / admission-fail / per-room-fail fixtures)
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
- 2026-06-03 — 4.2 landed (+ S07-D5). `stages/polygonize.py`:
  `build_region_polygons` / `polygonize_room` / `polygonize_corridors`. S07-D5
  decided from a throwaway probe over the 33 goldens: **0/137 rooms** produce a
  disconnected region union (growth absorbs only adjacent regions) → a room
  union must be a single `Polygon`; `polygonize_room` raises `GeometryFailure`
  (new **third sibling** exception family in `schema/failure.py`;
  `ROOM_DISCONNECTED` / `ROOM_EMPTY`) on violation — no largest-piece repair
  (honest-fix; `run()` catches → `valid=False`). Corridors are legitimately
  multi-component (**4/33**: case_04/10/32/33 — a Stage-2 shortcut attaches
  through a room entrance) → `corridor_polygons` is plural, `list[Polygon]`.
  Area conservation verified across all 137 rooms + corridor components. The
  union primitive already existed in viz (display-only); 4.2 makes it the
  persisted contract output. 805 passed + 5 xfailed; ruff clean.
- 2026-06-03 — 4.3 landed. `stages/labeling.py`: `label_room` (recovers the
  7-class role + usage from the spec via `name == id` — growth's 4-class
  collapse is undone here; `area_m2` from the polygon, S07-D6, not
  `GrownRoom.area_m2`) + `label_floor` (polygonize each room + corridor regions
  → `corridor_polygons`). vc / corridor / leftover deliberately not labeled here
  (§4.4 / output role / coverage). Unit test proves recovery reads the spec
  (grown `public` + spec `hub` → role `'hub'`), not the grown role; 33-case
  `label_floor` sweep with synthesized specs. 840 passed + 5 xfailed; ruff clean.
- 2026-06-03 — 4.4 landed. `vc_rooms(specs, anchors)` — the re-insert half of
  the S04-D4 donut-hole (subtract half already in `anchors.py`): each
  `vertical_circulation` spec → a fixed `LabeledRoom` with polygon =
  `VerticalAnchor.footprint_polygon` (the punched-out hole) + area = footprint
  area; `host_role=None` shafts get no room. `label_floor` gains `anchors=()`
  and appends them — now the full grown+vc floor assembler (default keeps 4.3
  callers intact). Synthetic tests only (33 goldens have no anchors); full
  subtract→grow→re-insert tiling (overlap-free) deferred to run() (4.6) /
  corpus B (4.10). 843 passed + 5 xfailed; ruff clean.
- 2026-06-03 — 4.5 landed. `constraints/room_gate.py`:
  `check_grown_rooms(rooms, specs_by_id)` — per non-vc room, `area_m2 <
  area_min_m2` → `ROOM_BELOW_MIN_AREA`, OBB short side < `min_dimension_m`
  (when set) → `ROOM_BELOW_MIN_DIM`. **Collects** FailureRecords (not raise —
  run() flips valid=False); vc exempt (fixed anchor geom). New module under
  constraints/ keeps the split clean: gates.py = pre-growth aggregate/raise,
  room_gate.py = post-growth per-room/collect (gates.py docstring already
  pointed here). `_obb_short_side` = `minimum_rotated_rectangle` short side
  (rotation-invariant). Tests: reject paths + vc exemption + None-dim skip +
  OBB rotation-invariance + 33-sweep (lenient→0, huge→every room). 916 passed
  + 5 xfailed; ruff clean.
- 2026-06-03 — 4.6 landed (+ S07-D6). The keystone `run.py`: per-floor join
  (validate_input → rules from `program.target_type` [S07-D6; v1 apartment,
  else `NO_TARGET_RULES`] → multi-floor gate → admission → subtract_anchors →
  atomize/regionize/region_graph → program_to_fixture → growth → carve →
  label_floor[grown+vc] → check_grown_rooms → assemble). **Failure
  composition:** catch the raisers (Program/Domain/GeometryFailure) + extend
  with the per-room *collect* → one failure_records; `valid = not failures`;
  never raises out, partial floors kept (proto3:D018 / Pipeline §2.4).
  `StageOutput` + the `on_stage` hook landed **here** with `run()` (S07-D3 —
  invasive; NOT 4.7, which builds its consumers); default None = pure. seed
  unused (deterministic v1, reserved). `run` + `StageOutput` re-exported from
  `room_layout`. Tests: case_01 happy path (valid apartment, all polygons
  valid), determinism, on_stage emission, 3 graceful failure injections
  (area / cardinality / unknown typology). 924 passed + 5 xfailed; ruff clean.
  NOT caught here (xfail PoCs → 4.11): K>seedable `IndexError`, corridor
  single-component.
- 2026-06-03 — 4.8 landed. `viz/stages/final.py`: `save_labeled_floor_figure`
  — dev-bridge matplotlib renderer for `LabeledFloorLayout` (rooms by 7-class
  role color + id/usage/role/area label; corridors hatched; vc rooms distinct
  hatch + heavy border). `ROLE_COLORS` (D004). Behind the viz extra
  (importorskip in test; smoke-only — no golden PNG). Verified **visually**:
  case_01 `run()` → clean 5-room role-colored tiling of the 140 m² footprint
  (public 69 / private×3 / wet), 0 corridor (compact flat — all rooms
  hub-adjacent), no overlap/gap. Honest note: room *sizes* are greedy auto-seed
  growth (target-agnostic, S04-D3), not design proportions — geometry is sound;
  proportion tuning is area-aware growth (deferred). Canonical 12-layer SVG =
  Step 08. 926 passed + 5 xfailed; ruff clean.
- 2026-06-03 — 4.9 landed (corpus A). `test_golden_run.py`: every case →
  `run()` (program synthesized from its growth_fixture) → **GEOS-stable** digest
  golden (`run.json`: valid + failure_codes + per-room id/role/usage/area_m2 +
  corridor count/area; areas 6 dp like the layout/corridor region-id digests,
  not coordinate-level). 33 goldens committed (with the test — first creation):
  31 valid, **case_24 + case_27** valid=False (`PROGRAM_CARDINALITY_INSUFFICIENT`
  — those abstract shapes lack a public/wet room; the failure path is contract).
  Confirms run() = the corridor_auto path carried through labeling. 959 passed
  + 5 xfailed; ruff clean. (Corpus A done; corpus B + failure-injection = 4.10
  → then the DoD test-corpus item is fully checked.)
- 2026-06-03 — 4.10 landed (corpus B) + bug fix. `test_golden_corpus_b.py`: 3
  **distinct** authored fixtures — `apt_anchored_core` (valid; anchor
  end-to-end subtract→grow→vc-reinsert, targeted test confirms vc == footprint
  + zero overlap), `apt_infeasible` (valid=False, admission
  `DOMAIN_AREA_GATE_FAIL`), `apt_undersized_room` (valid=False, post-growth
  `ROOM_BELOW_MIN_AREA`). **Finding:** target-agnostic growth (S04-D3) +
  realistic `area_min` → a realistic apartment can grow *invalid* (the living
  room got the smallest share, below its min). So corpus B is value-driven (3
  distinct behaviors, two failure paths golden'd), not a redundant realistic-apt
  suite — valid non-anchored is corpus A's 31. **Bug fix:** the per-stage sweeps
  (room_gate/labeling/polygonize) globbed *all* `tests/golden/` dirs, so the new
  `apt_*` dirs (no growth_fixture) broke `_carve` → filtered to
  `startswith("case_")` (matching test_golden_run). 965 passed + 5 xfailed; ruff
  clean. **Open design question** (the §4.10 finding): how should the pipeline
  handle "realistic program → target-agnostic growth → per-room reject"?
  (area-aware growth vs gate stance vs program-as-hint) — to be discussed +
  recorded as a deferred concern.

---

## 4. Close summary

(Filled at close — 4.12.)
