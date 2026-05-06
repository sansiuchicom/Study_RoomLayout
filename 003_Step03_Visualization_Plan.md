# 003 Step 03 — Visualization Renderer / Visual Vocabulary Plan

Status: Completed
Started: 2026-05-06
Completed: 2026-05-06
Branch: `step03-visualization` (merged into main via `--no-ff`, deleted)
Companion tracker: [003_Step03_Visualization_Tracker.md](003_Step03_Visualization_Tracker.md)

---

## 0. Purpose

Step 03 is the **first cross-cutting infrastructure Step that consumes Step 02 schemas**. It delivers:

1. an SVG-first renderer ([D013](000_Architecture_Decisions.md)) with stable 12-layer order,
2. a coded visual vocabulary palette mirroring [Pipeline Overview §12.3](000_Pipeline_Overview.md),
3. a minimum apartment fixture so the renderer has *something* to draw,
4. a smoke test proving the renderer produces a valid SVG with all 12 layer groups present.

Step 03 does **not** implement any Stage 03–13 logic. The renderer is the *infrastructure* every later Stage will plug into.

---

## 1. Definition of Done

| # | Condition |
|---|---|
| DoD-1 | `src/proto3/viz/` module tree exists per §3 (3 files) and all imports OK |
| DoD-2 | `palette.py` defines: 12-entry `LAYER_ORDER` constant + `LAYER_COLORS` palette dict matching [Pipeline Overview §12.3 vocabulary table](000_Pipeline_Overview.md) 1:1 |
| DoD-3 | `svg.py` defines `render(building, *, regions=None, atoms=None, ..., out_path)` keyword-only API per S03-D5 |
| DoD-4 | Rendered SVG contains exactly 12 `<g class="layer-NN-name">` group elements in [D013](000_Architecture_Decisions.md) order, even when the corresponding data is `None` (empty `<g>`) |
| DoD-5 | `fixtures/apartment_minimal.json` exists, loads via `BuildingInput.from_json`, and round-trips to dict identical to the file content |
| DoD-6 | Smoke test loads fixture → calls `render()` → asserts: SVG file exists, parses as valid XML, contains 12 layer groups, contains ≥1 `<polygon>` for footprint |
| DoD-7 | `pytest -q` passes (existing 14 tests + new viz tests, total ≥ 17) |
| DoD-8 | `pip install -e .` regression-free (no new runtime deps; stdlib `xml.etree.ElementTree` only) |
| DoD-9 | Step 02 docs moved into `legacy/step02/` via `git mv` (history preserved) |
| DoD-10 | `000_Progress_Tracker.md` updated: Step 02 archived, Step 03 → Done at close |
| DoD-11 | All §4 work-item commits land on `step03-visualization` branch |
| DoD-12 | Branch merged into `main` with `--no-ff` and deleted ([D015](000_Architecture_Decisions.md)) |
| DoD-13 | `notebooks/step03_viz_demo.ipynb` exists + after `pip install -e ".[dev]"` runs top-to-bottom + writes `outputs/notebooks/step03_viz_demo/<run_id>/minimal.svg` |
| DoD-14 | `.gitattributes` registers `*.ipynb filter=nbstripout`; `pyproject.toml` has `[project.optional-dependencies] dev` group |

---

## 2. 결정 기록 (Decision Record)

| ID | Decision | Rationale |
|---|---|---|
| S03-D1 | **All 12 D013 layers register as `<g class="layer-NN-name">` from Step 03**, even if the layer has no data yet. Empty layers emit an empty group, not nothing. | D013 mandates "stable layer order" as a cross-cutting invariant. Late-registering layers when each Stage lands would break order stability and force renderer commits in every later Step. Cost of stub group ≈ 1 line. |
| S03-D2 | Module location: `src/proto3/viz/` with 3 files: `__init__.py`, `svg.py`, `palette.py`. No `cli.py` in Step 03 (deferred). | Three-file split keeps palette/render concerns separate without premature modularization. |
| S03-D3 | Single `.svg` output per `render()` call. Layers grouped via `<g class="layer-NN-name">`. No multi-file output, no PNG export. | Keeps Stage-by-Stage debug output from §0_Pipeline §12.3 simple — one SVG per stage_svg_filename. |
| S03-D4 | **Visual vocabulary v1 = [Pipeline Overview §12.3](000_Pipeline_Overview.md) suggested-treatment table, taken verbatim and codified as a `dict[str, str]` in `palette.py`.** Plus a `role_to_palette_key(role: str) -> str` mapping function for `SpaceUnitSpec.role` enum (`public|private|service|wet|hub|corridor`) → palette key (`public-hub|private|wet-service|corridor`). `corridor` color = neutral grey `#888` (not in §12.3, stub for now). No new colors invented in Step 03. | Avoids bikeshedding; the table is already canonical. `SpaceUnitSpec.role` (public/private/service/wet/hub/corridor) ≠ §12.3 grouping (public-hub/private/wet-service) 1:1, so a mapping function is required. Future styling refinements get their own decision IDs. |
| S03-D5 | Renderer signature: `render(building: BuildingInput, *, regions: list[RegionPolygon] \| None = None, atoms: list[AtomCell] \| None = None, graph=None, out_path: str)` — all post-`building` args keyword-only, all `None`-defaultable. | Stages can pass only the data they have without positional ordering pain. Keyword-only forces call-site clarity. Exact list of optional params nailed in §4.4 implementation, not here. |
| S03-D6 | Coordinate system: input units = mm (matching `BuildingInput`). SVG `viewBox` in mm directly (1mm = 1 user unit). **Y axis flipped** so SVG-y grows downward while polygon-y grows upward. `viewBox` adds 5% padding around footprint bbox. | mm-direct keeps fixtures readable; flip is the standard SVG-vs-math convention. |
| S03-D7 | Grid: 100mm spacing as light reference grid. Drawn in dedicated layer (= part of layer 4 atoms, or as a separate sub-`<g>` inside layer 1). Toggleable via CSS class. | User-specified (mm too dense, 100mm = 10cm = readable for apartment scale). |
| S03-D8 | Labels: English only. No i18n. Font family `sans-serif` (system default), size derived from viewBox dimension (e.g. 1.5% of max bbox edge). | User-specified: English only, no need for i18n. |
| S03-D9 | Smoke validation = structural assertions (group count, polygon presence, valid XML), **not snapshot/pixel comparison**. Snapshot tests deferred. | Snapshot tests are noisy until the renderer is mature; structural is enough to catch the regressions Step 03 cares about. |
| S03-D10 | `apartment_minimal.json` fixture spec: 8000mm × 6000mm rectangular footprint, 1 floor at index 0, `floor_root` at `[4000, 0]`, 3 entries in `BuildingInput.program_request["spaces"]` (raw dict shape: `{"name": str, "role": str}`) — `living`/`public`, `bedroom_1`/`private`, `bathroom_1`/`wet`. `persistent_anchors=[]`, `anchor_projections=[]`, `floor_program=null`. NOTE: `program_request` is `dict` per `BuildingInput` schema; will be typed in Step 06. | Smallest input that lets the renderer prove palette role-mapping works while staying loyal to current `BuildingInput` schema (no `ProgramInstance` yet — that's a Stage 01 output, not a Stage 00 input). |
| S03-D11 | XML library: stdlib `xml.etree.ElementTree` only. No `lxml`, no `svgwrite`, no other deps for the renderer. | Keeps the runtime dep set lean. Pretty-printing is acceptable via `ET.indent()` (Python 3.9+). |
| S03-D12 | **Notebook location and naming**: `notebooks/<stepNN>_<purpose>.ipynb` (e.g., `notebooks/step03_viz_demo.ipynb`). First code cell **walks up from `Path.cwd()`** until a directory containing `pyproject.toml` is found and binds it as `ROOT`. This makes notebooks robust to cwd differences (VSCode Jupyter sets cwd to the notebook's directory by default; CLI `jupyter` from repo root sets cwd to repo root). First markdown cell describes purpose + prerequisite (`pip install -e ".[dev]"`). | Establishes the convention before notebooks accumulate. The walk-up approach (vs. asserting `cwd == repo_root`) avoids forcing a single launch path. Numeric-prefix doc convention (000_*) is *not* used for notebooks — different namespace. |
| S03-D13 | **Notebook artifact output location**: `outputs/notebooks/<notebook_stem>/<run_id>/` where `run_id` = ISO `YYYYMMDDTHHMMSS`. Mirrors `RunConfig.run_folder()` style. `.gitignore` extended in §4.6 with `outputs/notebooks/*` + `!outputs/notebooks/.gitkeep` (same pattern as `outputs/debug_runs/`), realizing [D014](000_Architecture_Decisions.md) for this subtree. | Keeps notebook artifacts grouped per-notebook + per-run, never in repo root. Reuses run_folder pattern + the existing debug_runs gitignore pattern for consistency. |
| S03-D14 | **Committed `.ipynb` files have cell outputs stripped**. Implementation: `.gitattributes` registers `*.ipynb filter=nbstripout`; user runs `nbstripout --install` once after cloning. Pre-commit hook framework not introduced in Step 03 (deferred). | base64-inlined SVG/PNG outputs would explode .ipynb diffs. Trade-off: GitHub preview won't show results — that's acceptable; users export HTML if they want to share live. |
| S03-D15 | **`pyproject.toml` gains `[project.optional-dependencies] dev = ["jupyter", "nbstripout"]`**. Default `pip install -e .` does not install these. | dev tooling separated from runtime deps. Keeps runtime install footprint unchanged. |

---

## 3. Directory structure (additions)

```text
src/proto3/viz/
├── __init__.py     # exports: render, LAYER_ORDER, LAYER_COLORS, role_to_palette_key
├── palette.py      # LAYER_ORDER (list[str], 12 entries) + LAYER_COLORS + role_to_palette_key
└── svg.py          # render() function + internal helpers

fixtures/
└── apartment_minimal.json   # S03-D10 fixture

notebooks/                      # NEW (S03-D12)
└── step03_viz_demo.ipynb       # DoD-13 demo notebook

tests/
└── test_viz_smoke.py        # DoD-6 smoke test

legacy/step02/                # destination of §4.1 git mv
├── 002_Step02_CoreSchema_Plan.md
└── 002_Step02_CoreSchema_Tracker.md

# Repo root additions
.gitattributes                 # NEW (S03-D14): *.ipynb filter=nbstripout
pyproject.toml                 # MODIFIED (S03-D15): + [project.optional-dependencies] dev
```

No changes to existing `src/proto3/schema/`, `src/proto3/config.py`, `src/proto3/debug.py`. `outputs/notebooks/` is created lazily by the notebook itself; not tracked.

---

## 4. Work items

Each item = 1 commit. Plan §4 numbering ↔ Tracker §1 numbering 1:1 ↔ §8 commit list 1:1.

### 4.1 Archive Step 02 docs + scaffold viz module

- `git mv 002_Step02_CoreSchema_Plan.md legacy/step02/`
- `git mv 002_Step02_CoreSchema_Tracker.md legacy/step02/`
- Create `src/proto3/viz/__init__.py` (empty stub with `# Step 03` marker), `palette.py` (empty stub), `svg.py` (empty stub).
- Create `tests/test_viz_smoke.py` placeholder with one trivially-passing test.
- Add this Plan and the Tracker to repo root (already done by initial commit of branch).
- **Verify**: `pip install -e .` succeeds, `python -c "import proto3.viz"` succeeds, `pytest -q` still 14+1 passing.
- **Commit msg**: `chore: archive step02 docs + scaffold step03 module structure`

### 4.2 Visual vocabulary palette

- Implement `palette.py`:
  - `LAYER_ORDER: list[str]` — exactly 12 entries in [D013](000_Architecture_Decisions.md) order. Names use kebab-case matching the suggested CSS class form: `["footprint", "anchors", "regions", "atoms", "graph-edges", "role-scores", "spine", "slots", "seeds", "grown", "doors", "failure"]`.
  - `LAYER_COLORS: dict[str, str]` — palette by **role/category**, not by layer (since e.g. `regions` layer contains rooms that take colors by program category). Map: `footprint` → `#000`, `public-hub` → orange (`#ffb84d`), `private` → green (`#8cc97a`), `wet-service` → purple (`#b58ad1`), `corridor` → grey (`#888`, S03-D4 stub), `spine` → blue (`#3f7cd0`), `invalid` → red (`#e04a3a`), `anchors` → dark grey (`#444`), `sliver` → grey (`#aaa`). Verbatim from [Pipeline §12.3](000_Pipeline_Overview.md) where applicable; corridor is the only addition.
  - `def role_to_palette_key(role: str) -> str` — maps `SpaceUnitSpec.role` enum (`public|private|service|wet|hub|corridor`) → palette key (`public-hub|private|wet-service|corridor`). Unknown role → fallback `"private"` with a comment noting it's a stub for Step 04 to refine.
  - `GRID_SPACING_MM: int = 100` (S03-D7).
  - `LABEL_FONT_FAMILY: str = "sans-serif"`, `LABEL_FONT_SIZE_RATIO: float = 0.015` (S03-D8).
- **Verify**: `from proto3.viz.palette import LAYER_ORDER, LAYER_COLORS, role_to_palette_key; assert len(LAYER_ORDER) == 12; assert LAYER_COLORS["footprint"] == "#000"; assert role_to_palette_key("hub") == "public-hub"`.
- **Commit msg**: `feat: visual vocabulary v1 (12-layer order + palette + role mapping)`

### 4.3 Minimal apartment fixture

- Write `fixtures/apartment_minimal.json` per S03-D10. JSON shape must match `BuildingInput.from_json` deserializer.
- Concrete content:
  ```json
  {
    "target_type": "apartment",
    "floors": [{
      "footprint": [[0, 0], [8000, 0], [8000, 6000], [0, 6000]],
      "floor_root": [4000, 0],
      "floor_program": null,
      "anchor_projections": []
    }],
    "program_request": {
      "spaces": [
        {"name": "living",     "role": "public"},
        {"name": "bedroom_1",  "role": "private"},
        {"name": "bathroom_1", "role": "wet"}
      ]
    },
    "persistent_anchors": []
  }
  ```
- **Verify**: `BuildingInput.from_json(open("fixtures/apartment_minimal.json").read())` deserializes; round-trip via `to_json` produces equivalent JSON.
- **Commit msg**: `feat: minimal apartment fixture (S03-D10)`

### 4.4 SVG renderer core

- Implement `svg.py`:
  - `render(building, *, regions=None, atoms=None, graph=None, spine=None, anchors=None, role_scores=None, slots=None, seeds=None, grown=None, doors=None, failure=None, out_path)` — every post-`building` keyword optional.
  - Compute `viewBox` from `building.floors[0].footprint` bbox + 5% padding (S03-D6). Y-flip applied at coord-transform layer.
  - Emit 12 `<g class="layer-NN-name">` groups in `LAYER_ORDER`, even when payload is None.
  - Layer 0 `footprint`: draw `<polygon>` from footprint coords.
  - Layer 2 `regions`: if `regions=None`, empty group. (Step 04+ will pass real data.)
  - Layer 3 `atoms`: same — empty if None. Grid sub-`<g>` inside layer 3 for 100mm reference grid (S03-D7).
  - Other layers: empty `<g>` for now.
  - Use stdlib `xml.etree.ElementTree`. `ET.indent(root)` for pretty-print. Write to `out_path` as UTF-8.
- **Verify**: hand-call `render(BuildingInput.from_json(...), out_path="/tmp/x.svg")` — file exists, opens in browser as a black footprint outline + 100mm grid.
- **Commit msg**: `feat: SVG renderer core (12-layer stable order, footprint+grid)`

### 4.5 Smoke test + DoD verification

- Implement `tests/test_viz_smoke.py`:
  - `test_render_minimal`: load fixture → `render(out_path=tmp_path / "out.svg")` → file exists.
  - `test_layer_order_stable`: parse output XML → assert exactly 12 `<g>` children of root SVG, classes in `LAYER_ORDER` sequence.
  - `test_footprint_polygon_present`: assert ≥1 `<polygon>` in `layer-00-footprint` group.
  - `test_empty_layers_are_present_but_empty`: assert layer-04..11 groups exist but have no shape children (only the layer's `<g>` itself).
- Run `pytest -q` → all green (≥ 17 tests).
- **Commit msg**: `feat: viz smoke test (12-layer stable order verified)`

### 4.6 Notebook + dev deps + nbstripout policy

- Add `pyproject.toml` `[project.optional-dependencies] dev = ["jupyter", "nbstripout"]` (S03-D15).
- Add `.gitattributes` at repo root with single line: `*.ipynb filter=nbstripout` (S03-D14).
- Write `notebooks/step03_viz_demo.ipynb` (S03-D12) cells:
  1. **Markdown**: title `# Step 03 Viz Demo`, purpose, prerequisites (`pip install -e ".[dev]"` + `nbstripout --install` once + run from repo root).
  2. **Code (root resolver)**: defines `_find_repo_root(start)` that walks up from `start.resolve()` until a directory containing `pyproject.toml` is found; binds `ROOT = _find_repo_root(Path.cwd())`. Robust to VSCode Jupyter (cwd = notebook dir) and CLI launch from repo root alike.
  3. **Code (load fixture)**: `from proto3.schema.input import BuildingInput; import json; b = BuildingInput.from_json(open(ROOT/"fixtures/apartment_minimal.json").read())`.
  4. **Code (render)**: compute `run_id` ISO timestamp → `out_dir = ROOT/"outputs/notebooks/step03_viz_demo"/run_id; out_dir.mkdir(parents=True, exist_ok=True)`; `from proto3.viz import render; render(b, out_path=str(out_dir/"minimal.svg"))`; print path.
  5. **Code (inline display)**: `from IPython.display import SVG, display; display(SVG(filename=str(out_dir/"minimal.svg")))`.
  6. **Markdown (footer)**: notes — re-running creates new `run_id` folder; older runs are kept for comparison.
- **Verify**: `pip install -e ".[dev]"` succeeds; `jupyter nbconvert --to notebook --execute notebooks/step03_viz_demo.ipynb --output /tmp/executed.ipynb` succeeds (or VSCode "Run All" succeeds); SVG file produced at the expected path.
- **Commit msg**: `feat: step03 viz demo notebook + nbstripout policy + dev deps`

### 4.7 Step 03 cleanup

- Update `000_Progress_Tracker.md`:
  - §1 Current phase → "Step 03 complete. Ready for Step 04 kickoff."
  - §2 Active files → mark Step 03 docs as "Completed; pending move to legacy/step03/ at Step 04 kickoff". Note Step 02 docs archived to `legacy/step02/`.
  - §6 Step status table → Step 03 → Done.
- Mark all this Plan's DoD items in [Tracker §2](003_Step03_Visualization_Tracker.md) as `[x]`.
- Update Tracker §변경이력.
- **Commit msg**: `docs: step03 cleanup (Plan/Tracker, Progress Tracker)`
- After commit: `git checkout main && git merge --no-ff step03-visualization && git branch -d step03-visualization && git push origin main`.

---

## 5. Deferred (explicit non-goals)

| # | Deferred item | 유예 reason | Where it lands |
|---|---|---|---|
| Def-1 | Real apartment fixtures (multi-room, irregular footprints, multi-floor) | Step 04 owns fixtures by Pipeline §15 | Step 04 |
| Def-2 | Stage 03–13 actual data rendering (regions/atoms/graph/spine/...) | Each Stage Step (07–13) will call `render(...)` with its data | Step 07–13 |
| Def-3 | Snapshot / pixel-diff visual regression | Premature; structural assertions are enough now | Possibly Step 12+ |
| Def-4 | CLI tool (`python -m proto3.viz fixture.json -o out.svg`) | Trivial wrapper; build only when actually needed | TBD |
| Def-5 | Legend, gradients, patterns (hatch fills), animations | Fine styling — covered by S03-D4 vocabulary v1 limit | Future styling iteration |
| Def-6 | i18n / non-English labels | User-specified out of scope | — |
| Def-7 | PNG / PDF export | SVG-first per [D013](000_Architecture_Decisions.md); export can be a separate post-process | TBD |
| Def-8 | Snapshot of failure overlays (Stage 12 output) | Stage 12 doesn't exist yet | Step 12 |
| Def-9 | Pre-commit hook framework (e.g., `pre-commit` package) | `.gitattributes` filter is enough for now; framework adds setup overhead | TBD if multiple hooks needed |
| Def-10 | Multi-fixture comparison in notebook | Single fixture is enough to prove the rendering pipeline; comparisons land when Step 04 produces multiple fixtures | Step 04+ |

---

## 6. Risks

| ID | Risk | Mitigation |
|---|---|---|
| R-S03-1 | Y-axis flip implementation mistakes (polygons drawn upside-down or off-canvas) | S03-D6 fixes it at one helper function `to_svg_xy(x, y, bbox)`. Smoke test footprint must be in viewBox to catch this. |
| R-S03-2 | `LAYER_COLORS` keys diverge from program-category strings used elsewhere later | Keep palette keys conceptual ("public-hub"/"private"/"wet-service"). Mapping from `ProgramInstance.category` → palette key is a TODO comment in `svg.py` until Step 04 fixes program category strings. |
| R-S03-3 | `apartment_minimal.json` schema drift if Step 02 schema evolves before Step 04 | Fixture round-trip test in DoD-5 will catch this immediately. |
| R-S03-4 | 12-layer order constant drifts from D013 if D013 is later edited | Add a unit test that asserts `LAYER_ORDER` matches a hard-coded canonical list. Single source of truth for now: `palette.py` constant + this Plan §3. |
| R-S03-5 | nbstripout filter not installed by user → cell outputs commit anyway | Notebook's first markdown cell explicitly states `nbstripout --install` as a one-time setup. `.gitattributes` registration alone doesn't activate the filter; user must run install once. |
| R-S03-6 | `jupyter nbconvert --execute` requires kernel; CI environment may not have one | DoD-13 verification accepts either nbconvert OR a stripped manual execution. CI integration deferred (Def-9 family). |

---

## 7. Next-Step linkage

Step 03 produces:
- `proto3.viz.render(...)` — used by every later Stage's debug emission via `DebugArtifact`,
- `LAYER_ORDER` / `LAYER_COLORS` — referenced by Stage rendering code,
- `apartment_minimal.json` — used as the smoke fixture for Step 04 / Step 05 / etc. until larger fixtures land.

Step 04 (Apartment Fixtures) will:
- add multi-room fixtures with adjacent outer rooms,
- formalize program category strings → palette key mapping (resolves R-S03-2),
- not modify the renderer itself.

Step 05 (Geometry Kernel) will:
- add polygon utilities (currently footprint is rendered raw from a coordinate list),
- decide atom resolution (which feeds the grid and atom-layer rendering).

---

## 8. Branch / Commit strategy

- **Branch**: `step03-visualization` (already checked out 2026-05-06)
- **Commits** (one per §4 item, 7 total, in order):
  1. `chore: archive step02 docs + scaffold step03 module structure` (§4.1)
  2. `feat: visual vocabulary v1 (12-layer order + palette + role mapping)` (§4.2)
  3. `feat: minimal apartment fixture (S03-D10)` (§4.3)
  4. `feat: SVG renderer core (12-layer stable order, footprint+grid)` (§4.4)
  5. `feat: viz smoke test (12-layer stable order verified)` (§4.5)
  6. `feat: step03 viz demo notebook + nbstripout policy + dev deps` (§4.6)
  7. `docs: step03 cleanup (Plan/Tracker, Progress Tracker)` (§4.7)
- **Close**: `git merge --no-ff step03-visualization` into main → `git branch -d step03-visualization` → `git push origin main` ([D015](000_Architecture_Decisions.md)).

---

## 9. 변경이력 (this Plan)

| Date | Change |
|---|---|
| 2026-05-06 | Initial draft. §0–§8. 11 decisions (S03-D1 ~ S03-D11). 6 work items. |
| 2026-05-06 | Pre-implementation revision. Schema check revealed `BuildingInput.program_request: dict` (not ProgramInstance) → S03-D10 fixture format updated. `SpaceUnitSpec.role` enum (public/private/service/wet/hub/corridor) ≠ §12.3 grouping → S03-D4 boosted with `role_to_palette_key()` mapping function + corridor=grey stub. Notebook convention added (S03-D12 location, S03-D13 output dir, S03-D14 nbstripout, S03-D15 dev deps). Work items 6 → 7 (4.6 notebook inserted, cleanup → 4.7). DoD-13 + DoD-14 added. R-S03-5/6, Def-9/10 added. |
| 2026-05-06 | Mid-implementation refinement (§4.6). S03-D12 walk-up resolver wording (VSCode Jupyter cwd issue I-S03-2). S03-D13 wording corrected re: `.gitignore` extension done in §4.6 (I-S03-1: `outputs/notebooks/*` was not previously ignored). |
| 2026-05-06 | Step 03 closed. 7 commits on `step03-visualization`; merge --no-ff into main next. |
