# 003 Step 03 — Geometry Pipeline Port Tracker

Status: Active
Type: Step tracker
Branch: `step03-geometrypipeline`
Last updated: 2026-05-25

Mirrors Plan §4 work items 1:1 in §1 checklist (per `proto3:D016`).

---

## 1. Plan §4 work items

- [ ] **4.1** Plan + Tracker land + `git mv` Step 02 docs to `legacy/step02/`
- [ ] **4.2** Scaffold: `stages/`, `viz/stages/`, `tests/_golden.py` skeleton
- [ ] **4.3** Cell 33-case fixtures → JSON one-shot under `tests/golden/<case>/input.json` (S03-D7)
- [ ] **4.4** Polygon-aware golden comparator (`tests/_golden.py::assert_layout_equal`) + `pytest --update-goldens` flag + self-tests (S03-D10)
- [ ] **4.5** `stages/_helpers.py` — Cell geometry utilities ported (`to_shapely` / `polygon_parts` / `part_theta`) + unit tests
- [ ] **4.6** `stages/dimensions.py` — `DimensionPolicy` + `is_quantum_aligned` + `split_interval` + unit tests (S03-D8)
- [ ] **4.7** `stages/atomize.py` (Atom + atomize) + `viz/stages/atomize.py` + 33-case `atomize.json` + PNG sidecars + unit tests + extend `test_golden_per_stage.py` — **first manual review checkpoint**
- [ ] **4.8** `stages/territory.py` (Territory + resolve_territories) + unit tests
- [ ] **4.9** `stages/regionize.py` (Region + regionize) + `viz/stages/regionize.py` + 33-case `regionize.json` + PNG sidecars + unit tests — **second manual review checkpoint**
- [ ] **4.10** `stages/region_graph.py` (build_region_graph) + region-graph viz overlay + 33-case `region_graph.json` + PNG sidecars + unit tests
- [ ] **4.11** `stages/shape_gate.py` (gates raising `DimGateFailure`) + `viz/stages/gates.py` + 33-case `gates.json` + PNG sidecars + unit tests — **third manual review checkpoint**
- [ ] **4.12** `viz/demo.py` CLI (`python -m room_layout.viz.demo --case <n> --stage <s> --out outputs/step03/`)
- [ ] **4.13** Step close + `git merge --no-ff step03-geometrypipeline` to `main`

---

## 2. Definition of Done checklist

- [ ] Phase 3–5 modules importable from `room_layout.stages` (atomize / regionize / region_graph / territory / shape_gate / dimensions + `_helpers`)
- [ ] Every stage accepts `room_layout.schema.ShapeInput` (new schema); internal types (`Atom` / `Region` / `Territory` / `DimensionPolicy`) live alongside their producing stage and are not re-exported from `room_layout` (S03-D6)
- [ ] Internal dataclasses round-trip through `to_dict` / `from_dict` per work-item unit tests (proto3:D017 carry)
- [ ] 33 Cell fixtures converted to JSON under `tests/golden/<case>/input.json` (S03-D7); each loads cleanly via `from_json(ShapeInput, ...)` / `from_json(ProgramRequest, ...)`
- [ ] Per-stage golden JSON files exist for all 33 cases × 4 stages: `atomize.json`, `regionize.json`, `region_graph.json`, `gates.json`
- [ ] Polygon-aware comparator `tests/_golden.py::assert_layout_equal(actual, expected, *, tol=1e-6)` implemented + self-tested in `test_golden_comparator.py`
- [ ] 33 × 4 = 132 per-stage golden assertions all pass (`pytest tests/test_golden_per_stage.py`)
- [ ] `pytest --update-goldens` flag implemented; rewrites are loud (per-file print) and produce git-visible diffs
- [ ] 4 dev-bridge renderers under `src/room_layout/viz/stages/` (input / atomize / regionize / gates) with shared `viz/_helpers.py` (S03-D4 selective port)
- [ ] PNG sidecars rendered for all 33 cases × 4 stages → `tests/golden/<case>/<stage>.png` (committed)
- [ ] `outputs/step03/` directory active (D006); `viz/demo.py` regenerates PNGs into it without re-rendering goldens
- [ ] Unit tests for every ported module (S03-D11 — written fresh, not auto-ported from Cell)
- [ ] `python -m pytest` green
- [ ] `ruff check .` + `ruff format --check .` green
- [ ] CI green on `step03-geometrypipeline` branch
- [ ] CI green on `main` after `--no-ff` merge
- [ ] **Viz status documented**: 4 dev-bridge renderers exist; canonical SVG replacement deferred to Step 07
- [ ] `docs/000_Progress_Tracker.md` §1 / §2 / §3 updated (Step 03 closed; Step 04 kickoff)

---

## 3. Notes / decisions during execution

_Per-work-item notes go below as they accumulate. Pre-execution decisions
S03-D1..D12 are frozen in Plan §2._

- **2026-05-26 — 4.3 heuristics flagged for Step 05/06 revisit**: Cell
  ``LayoutFixture`` doesn't carry per-room target areas or a typology
  label, so two values were filled by heuristic during fixture
  conversion: (1) ``SpaceUnitSpec.area_target_m2 =
  footprint_area_m2 / num_rooms`` (equal split) — Cell has min areas
  via ``role_min_areas`` but no per-room target; Phase 6 growth will
  refine. (2) ``ProgramRequest.target_type = "apartment"`` for all 33
  cases — Cell fixtures are Korean apartment-style by design; Step 05
  will re-evaluate once ``target_rules/<typology>.json`` lands. Both
  decisions are also documented in
  ``scripts/cell_fixtures_to_json.py`` docstring; flagging here so
  they don't get forgotten when downstream stages start depending on
  them as ground truth.

- **2026-05-26 — 4.3 slug convention**: replaced Cell's lossy
  ``case_slug`` (NFKD + ASCII-strip → "타워형" → "case") with an
  English-only mapping table in ``scripts/cell_fixtures_to_json.py``
  (``_english_slug``). Maps shape ideograms (ㄱ자/ㄷ자/7자/十자/ㅁ자/E자/
  ㄹ자/T자/standalone ㄱ/ㄷ/ㅁ/ㄹ) + 평/판상형/타워형/비대칭/큰 to
  meaningful tokens (``l_shape`` / ``c_shape`` / ``j_shape`` / ``cross``
  / ``donut`` / ``e_shape`` / ``z_shape`` / ``t_shape`` / ``py`` /
  ``flat`` / ``tower`` / ``asym`` / ``big``). Result: every case dir is
  human-readable (e.g., ``case_05_tower``, ``case_31_asym_l``). Trade-
  off: slug names no longer match Cell's ``case_slug`` output, so
  cross-referencing Cell docs requires the index alone, not the slug.
  Acceptable — ongoing-dev readability beats Cell-doc symmetry.

- **2026-05-26 — 4.3 ``.gitkeep`` retired**: ``tests/golden/.gitkeep``
  removed in the 4.3 commit since the directory now has 33 case
  subdirectories carrying real fixture content.

---

## 4. Close summary

_Populated at Step close (work item 4.13). One-paragraph retro: what was
actually built, any surprises encountered during manual golden bootstrap
(4.7 / 4.9 / 4.11), any items pushed forward to Step 04 — e.g., a stage
that turned out to need Phase 6 context to validate, or a case from the
33 that revealed an edge condition worth a Tracker §3 entry._
