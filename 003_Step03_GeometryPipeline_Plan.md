# 003 Step 03 — Geometry Pipeline Port Plan

Status: Active
Type: Step plan
Branch: `step03-geometrypipeline` (D005 — regression risk + integration work
touching all downstream stages)
Last updated: 2026-05-25

---

## 0. Purpose

Step 03 lands the **geometry-side half** of the pipeline (Cell **Phase 3–5**)
into `src/room_layout/stages/`, refactored against the new
`room_layout.schema` from Step 02 (S02-D8 semantic migration). It also
establishes the development-bridge visualization (`src/room_layout/viz/`)
and the per-stage JSON golden test infrastructure
(`tests/golden/`) that subsequent Steps depend on for regression coverage.

Phase 3–5 are the **pure-geometry stages** — ShapeInput → atoms → regions
→ gate-OK. The growth-and-carving half (Phase 6–8) is deferred to
**Step 04** to keep this Step reviewable and the work-item commits atomic
(S03-D3).

After Step 03 closes:

- `from room_layout.stages import atomize, regionize, ...` works.
- A `ShapeInput` can be carried through atomize → regionize → gate
  checks; intermediate outputs are typed Python dataclasses.
- Per-stage matplotlib renderers (input / atomize / regionize / gates)
  produce dev-bridge PNGs; visual vocabulary mirrors Cell `viz.py`
  selectively, code is new-schema-native (S03-D4).
- `tests/golden/<case>/` carries 33 Cell showcase cases as JSON
  fixtures, each with per-stage golden outputs and PNG sidecars; a
  Polygon-aware comparator (`tests/_golden.py`) drives regression
  coverage with `tol=1e-6` (S03-D5).

Cross-references:

- `docs/000_Pipeline_Overview.md` §3 — per-stage operational view
  (this Step implements the atomize / regionize / gates portion).
- `docs/000_Architecture_Decisions.md`:
  - **D001** — external contract (Step 02 implemented; Step 03 ports
    algorithm against it).
  - **D002** — seed-first vs spine-first growth (decided; relevant
    background for the regions → growth transition in Step 04).
  - **D005** — solo-mode workflow (justifies branching).
  - **D006** — output directory convention (`outputs/step03/` for
    dev-bridge PNG demo runs).
  - **`proto3:D012`** carry — no pydantic.
  - **`proto3:D016`** H011 — deferred-archive pattern (Step 02 docs
    moved to `legacy/step02/` at §4.1).
  - **`proto3:D017`** carry — strict `Literal` validation already
    enforced by `room_layout.schema.from_dict`; golden fixture
    deserialization rides on it.
- `legacy/step02/002_Step02_CoreSchema_*.md` — direct predecessor;
  Plan §7 sketches this Step's outline.
- `archive/celllayout/algorithm/celllayout_tf/` — porting source.
  Phase 3–5 modules: `atomize.py`, `regionize.py`, `region_graph.py`,
  `territory.py`, `shape_gate.py`, `dimensions.py` + the support
  helpers in `geometry.py`. Phase 6–8 modules untouched this Step.
- `archive/celllayout/algorithm/celllayout_tf/viz.py` — visual
  vocabulary reference (S03-D4 selective port).
- `archive/celllayout/algorithm/celllayout_tf/cases.py` +
  `layout_fixtures.py` — Cell's 33 showcase cases; converted one-shot
  to JSON under `tests/golden/` per S03-D7.
- Companion: `003_Step03_GeometryPipeline_Tracker.md`.

---

## 1. Definition of Done

| Item | Verification |
|---|---|
| Phase 3–5 modules ported into `src/room_layout/stages/` (atomize / regionize / region_graph / territory / shape_gate / dimensions + `_helpers.py` for shared geometry utilities) | `python -c "from room_layout.stages import atomize, regionize, region_graph, territory, shape_gate, dimensions"` |
| Every stage accepts `room_layout.schema.ShapeInput` (new schema) — Cell internal types (`Atom` / `Region` / `Territory` / `DimensionPolicy`) live alongside their producing stage and are not re-exported from `room_layout` (S03-D6 internal-types policy) | code review + `room_layout.__all__` audit |
| Internal dataclasses (`Atom` / `Region` / `Territory`) round-trip through `to_dict` / `from_dict` cleanly (proto3:D017 strict-Literal carry) | unit tests under `tests/test_stages_*.py` |
| 33 Cell showcase fixtures converted to JSON under `tests/golden/<case>/input.json` (one-shot via `scripts/cell_fixtures_to_json.py`; Cell Python `LayoutFixture` form retired afterward) | directory listing + each input.json loads via `from_json(ShapeInput, ...)` cleanly |
| Per-stage golden JSON files exist for all 33 cases × 4 stages: `atomize.json`, `regionize.json`, `region_graph.json`, `gates.json` | listing under `tests/golden/<case>/` |
| Polygon-aware comparator `tests/_golden.py::assert_layout_equal(actual, expected, *, tol=1e-6)` implemented + self-tested | `tests/test_golden_comparator.py` green |
| 33 × 4 = 132 per-stage golden assertions all pass | `pytest tests/test_golden_per_stage.py` green |
| Golden update mechanism: `pytest --update-goldens` flag (pytest fixture hook) regenerates the *.json files in place; documented in Plan §3 / Tracker | running with the flag produces a diff in `tests/golden/<case>/<stage>.json` for any case where the algorithm changed |
| 4 dev-bridge matplotlib renderers under `src/room_layout/viz/stages/` (input / atomize / regionize / gates) with shared `viz/_helpers.py` for `_draw_part` / `_draw_footprint` / `_finish_axis` / color palette | `python -m room_layout.viz.demo --case 1 --stage atomize --out outputs/step03/` produces a PNG; visual style matches Cell viz selectively (S03-D4) |
| PNG sidecars rendered for all 33 cases × 4 stages → `tests/golden/<case>/<stage>.png` (committed; small enough to git-track) and also reproducible via `viz/demo.py` into `outputs/step03/` (D006) | listing + spot check |
| Unit tests for every ported module (mirroring Cell test coverage but written against the new schema, not auto-ported — S03-D11) | per-module test files green |
| `python -m pytest` green; `ruff check .` + `ruff format --check .` green | local + CI |
| CI green on `step03-geometrypipeline` branch | `gh run list` |
| CI green on `main` after `git merge --no-ff` | `gh run list` |
| **Viz status documented**: 4 dev-bridge renderers exist; canonical SVG replacement deferred to Step 07 (S02-D13 viz-at-every-step convention) | Tracker §2 + close summary |
| `docs/000_Progress_Tracker.md` §1 / §2 / §3 updated (Step 03 closed; Step 04 kickoff) | docs review |

---

## 2. 결정 기록

| ID | Title | Decision |
|---|---|---|
| **S03-D1** | Branch policy | `step03-geometrypipeline` branch per D005 (regression risk + integration work touching the whole downstream chain). Merge `--no-ff` to `main` at Step close. |
| **S03-D2** | Module structure | Flat `src/room_layout/stages/`: each ported module is a single file (`atomize.py`, `regionize.py`, …). No per-phase subdirectories — module count this Step is ~6, nesting would be premature. Revisit if Step 04 pushes the count past ~10. |
| **S03-D3** | Step 03 scope split | **Phase 3–5 only** (atomize / regionize / region_graph / territory / shape_gate / dimensions). Phase 6–8 (seed_placement / growth_* / corridor_* / atom_graph) deferred to **Step 04** — bundling all Phase 3–8 in one Step would produce an oversized PR and conflate "pure geometry" with "algorithm core" concerns. |
| **S03-D4** | Viz strategy | **Selective port**, not whole-port and not rewrite-from-scratch. For each Phase 3–5 stage, take Cell `viz.py`'s corresponding function as a *visual vocabulary reference* — color palette, label format (`R3\n12.3m²`), backdrop+overlay pattern — and rewrite against the new schema in `src/room_layout/viz/stages/`. Shared helpers (`_draw_part`, `_draw_footprint_outline`, `_finish_axis`, `PART_COLORS`) live in `viz/_helpers.py`. Cell `viz.py` itself stays untouched in `archive/` as the reference. Step 07 replaces this dev bridge with canonical SVG. |
| **S03-D5** | Golden test approach | **Per-stage JSON goldens + Polygon-aware comparator + PNG sidecars (visual-only)**. Each case directory under `tests/golden/<case>/` holds `input.json`, one `<stage>.json` per stage, and a matching `<stage>.png`. Comparator `tests/_golden.py::assert_layout_equal` deep-compares dataclass field-by-field; for `shapely.Polygon` fields it uses `equals_exact(other, tol=1e-6)`. PNGs are sidecar artifacts for human inspection — test assertions ignore them. |
| **S03-D6** | Internal types location | `Atom` / `Region` / `Territory` / `DimensionPolicy` dataclasses live in their producing stage module (`stages/atomize.py` defines `Atom`, etc.), are *not* re-exported from `room_layout` or `room_layout.schema`. Rationale: `room_layout.schema` is the D001 public contract; these are implementation details of the pipeline. Tests import directly from the stage module. |
| **S03-D7** | Cell `LayoutFixture` migration | **One-shot convert + drop the Python form**. A throwaway `scripts/cell_fixtures_to_json.py` calls Cell's `layout_fixtures.selected_fixtures(...)`, emits each as `tests/golden/<case>/input.json` via the new schema's `to_json`. After conversion, the script's only purpose is documentation — fixtures live solely as JSON. The Cell Python form is *not* mirrored in `src/`. |
| **S03-D8** | `DimensionPolicy` location | `stages/dimensions.py` (alongside the helpers that consume it: `is_quantum_aligned`, `split_interval`). Other stages (`atomize` / `regionize`) import from there. Not promoted to `room_layout.schema` because `DimensionPolicy` is an internal algorithmic parameter, not part of the D001 contract surface. |
| **S03-D9** | 33-case scope | **All 33 Cell showcase cases** ported as goldens in Step 03 (not a subset). Rationale: empirical experience with similar pipeline ports has shown that "subset coverage" misses algorithm-edge cases — e.g., concave-shape behavior that doesn't surface in 5 cases but breaks in case 19. Bootstrap cost is high (manual review per case) but pays back in regression coverage from Step 04 onward. |
| **S03-D10** | Golden update interface | `pytest --update-goldens` flag (pytest fixture hook). When set, the per-stage golden test rewrites the expected `*.json` file in place using the current algorithm output instead of comparing. Idiomatic — uses the same test invocation; no separate CLI. Updates are *always* committed as a separate commit so the diff is visible in PR review. |
| **S03-D11** | Cell test porting policy | Cell's 17 test files under `archive/celllayout/algorithm/tests/` are kept as *reference only*. New tests for the ported stages are written from scratch against the new schema and committed alongside their stage in the same work-item commit (not as a separate test-bundle commit per Step 02 §4.8 pattern). |
| **S03-D12** | Viz output locations | Two paths, intentionally: (a) `tests/golden/<case>/<stage>.png` — committed sidecars for in-PR visual inspection (33 × 4 = 132 PNGs, kept small via `dpi=130`). (b) `outputs/step03/<case>/<stage>.png` — D006-compliant dev demo target (`.gitignore`d, regenerable via `python -m room_layout.viz.demo`). |
| **S03-D13** | Stage input granularity | Phase 3–5 stages take a **`FloorShape`**, not a `ShapeInput`. Cell's `ShapeInput` was single-floor (`name` + `parts`), so the 1:1 semantic mapping to the new schema is `FloorShape` (one floor's `parts`), not the new multi-floor `ShapeInput`. Per-floor orchestration (`for floor in shape.floors`) lives in Step 06 `run()`; stages stay floor-scoped, matching Pipeline §2.1 ("processes one floor at a time") and keeping multi-floor (Step 09) a loop-only change with no stage rewrite. v1 golden drivers call stages with `shape.floors[0]`. `vertical_anchors` are not passed to Phase 3–5 stages (unused until Phase 6+; supplied separately then). Discovered while porting `territory` (4.7), which accessed Cell's `shape.parts`. |
| **S03-D15** | `region_graph` golden = edges only | `build_region_graph` returns a `RegionGraph(regions, edges)` dataclass — the `regions` are identical to regionize's output (already pinned by `regionize.json`), so the region_graph golden stores **only the `edges`** (`region_a` / `region_b` / `shared_boundary_length` / `centroid_distance` / `same_theta_group` / `exterior_contact` / `hole_contact`, floats rounded). Avoids duplicating region geometry; pins exactly what this stage adds — the adjacency. `atom_graph` is an *intermediate* (consumed only by `region_graph`): no standalone golden or viz (territory precedent), covered indirectly via the region_graph golden + direct unit tests. Note: both `build_atom_graph` and `build_region_graph` return plain dataclasses (not `networkx.Graph`), so `to_dict` serializes them with no special adapter — the earlier networkx-serialization concern was unfounded. |
| **S03-D14** | Golden granularity per stage | Golden representation is matched to each stage's output semantics. **`atomize` → digest** (`n_atoms`, `total_area`, `per_part_counts`, `n_slivers`, `bbox`, distinct `thetas`), **not** full per-atom geometry: a single case produces ~1500 mechanical grid cells (~400 KB full JSON; ~13 MB across 33 cases), and individual atoms carry no human-meaningful identity. The digest catches the real port-regression modes (atom-count drift, area-conservation break, part-assignment change, sliver-absorption change, bounds shift) at ~200 B/case. **`regionize` / `region_graph` / `gates` → full goldens** — their outputs are few + meaningful (tens of regions, a small graph, per-region pass/fail), so exact geometry is worth pinning and cheap to store. `tests/golden/<case>/atomize.json` holds the digest (filename convention preserved); the digest builder lives in the test layer (golden-strategy concern, not algorithm). If exact per-atom regression is ever needed, add full goldens for a few representative cases then. |

---

## 3. Directory structure (target state after Step 03)

```text
Study_RoomLayout/
├── 003_Step03_GeometryPipeline_Plan.md         (this file)
├── 003_Step03_GeometryPipeline_Tracker.md      (companion)
├── legacy/
│   ├── step01/                                  (Step 01 archive — unchanged)
│   └── step02/                                  (new — D016 H011 archive at §4.1)
│       ├── 002_Step02_CoreSchema_Plan.md
│       └── 002_Step02_CoreSchema_Tracker.md
├── scripts/                                     (new — Step 03 introduces)
│   └── cell_fixtures_to_json.py                 (one-shot Cell → JSON converter; retired after 4.3)
├── src/
│   └── room_layout/
│       ├── __init__.py                          (existing — Step 02 re-exports; may add stages re-export at close)
│       ├── schema/                              (existing — public contract; unchanged)
│       ├── stages/                              (new package, Phase 3–5)
│       │   ├── __init__.py
│       │   ├── _helpers.py                      (Cell geometry utilities ported: to_shapely, polygon_parts, part_theta)
│       │   ├── dimensions.py                    (DimensionPolicy + is_quantum_aligned + split_interval)
│       │   ├── atomize.py                       (Atom dataclass + atomize())
│       │   ├── territory.py                     (Territory dataclass + resolve_territories())
│       │   ├── regionize.py                     (Region dataclass + regionize())
│       │   ├── atom_graph.py                     (AtomGraph + build_atom_graph(); region_graph dep)
│       │   ├── region_graph.py                  (RegionGraph + build_region_graph())
│       │   └── shape_gate.py                    (shape gate checks; raises DimGateFailure)
│       └── viz/                                 (existing — currently empty)
│           ├── __init__.py
│           ├── _helpers.py                      (new — shared draw helpers + PART_COLORS palette)
│           ├── demo.py                          (new — CLI: render any case × any stage)
│           └── stages/                          (new)
│               ├── __init__.py
│               ├── input.py                     (save_input_figure)
│               ├── atomize.py                   (save_atom_figure)
│               ├── regionize.py                 (save_region_figure + save_region_graph_figure)
│               └── gates.py                     (save_gate_figure + save_dimension_examples_figure)
├── tests/
│   ├── golden/                                  (existing — was empty; populated here)
│   │   ├── case_01_<slug>/
│   │   │   ├── input.json                       (ShapeInput + ProgramRequest)
│   │   │   ├── atomize.json
│   │   │   ├── regionize.json
│   │   │   ├── region_graph.json
│   │   │   ├── gates.json
│   │   │   ├── atomize.png                      (sidecar, dpi=130)
│   │   │   ├── regionize.png
│   │   │   └── gates.png
│   │   └── ... (33 cases total per S03-D9)
│   ├── _golden.py                               (new — assert_layout_equal + Polygon-aware tolerance)
│   ├── test_golden_comparator.py                (new — tests for the comparator itself)
│   ├── test_stages_dimensions.py                (new)
│   ├── test_stages_atomize.py                   (new)
│   ├── test_stages_territory.py                 (new)
│   ├── test_stages_regionize.py                 (new)
│   ├── test_stages_region_graph.py              (new)
│   ├── test_stages_shape_gate.py                (new)
│   ├── test_golden_per_stage.py                 (new — parametrized 33 × 4)
│   ├── test_schema_*.py                         (existing — Step 02; unchanged)
│   └── test_smoke.py                            (existing)
└── outputs/
    └── step03/                                  (new, .gitignored — viz/demo.py target dir)
        └── <case>/<stage>.png
```

---

## 4. Work items

Each = one atomic commit on `step03-geometrypipeline`. Order designed so
each commit leaves the tree in a green-CI state. The "big" items
(4.7 / 4.9 / 4.11) bundle module port + viz renderer + 33-case golden
generation; this is intentional — the manual review for golden bootstrap
is per-stage, so the commit boundary matches the review boundary.

### 4.1 Plan + Tracker land + Step 02 archive

Files:

- `003_Step03_GeometryPipeline_Plan.md` (this file).
- `003_Step03_GeometryPipeline_Tracker.md` (companion).
- `git mv 002_Step02_CoreSchema_Plan.md legacy/step02/` (`proto3:D016` H011).
- `git mv 002_Step02_CoreSchema_Tracker.md legacy/step02/`.

Commit: `docs(step03): plan + tracker + archive step02`.

Verification: both Step 03 docs at repo root; both Step 02 docs under
`legacy/step02/`; `git status` clean.

### 4.2 Scaffold

Files (all docstring-only placeholders, no implementation):

- `src/room_layout/stages/__init__.py` + `_helpers.py` + 6 stage module files (empty docstrings).
- `src/room_layout/viz/_helpers.py` + `viz/stages/__init__.py` + 4 stage renderer files.
- `tests/_golden.py` (skeleton — signature + docstring for `assert_layout_equal`).
- `tests/golden/` left empty; `.gitkeep` unchanged.

Commit: `feat(step03): scaffold stages + viz/stages + golden infrastructure`.

Verification: `python -c "import room_layout.stages, room_layout.viz.stages"`
succeeds; `python -m pytest` green (115 carry-over tests).

### 4.3 Cell fixtures → JSON one-shot

Files:

- `scripts/cell_fixtures_to_json.py` (throwaway converter; reads
  `archive/celllayout/algorithm/celllayout_tf/layout_fixtures.py` via
  importlib + emits `tests/golden/<case>_<slug>/input.json`).
- `tests/golden/case_01_<slug>/input.json` … 33 cases populated.

Commit: `chore(step03): port 33 Cell showcase cases to golden JSON fixtures`.

Verification: 33 directories under `tests/golden/`; each `input.json`
loads via `from_json(ShapeInput, ...)` and via `from_json(ProgramRequest, ...)`
in a smoke test.

### 4.4 Golden comparator + self-tests

Files:

- `tests/_golden.py` — `assert_layout_equal(actual, expected, *, tol=1e-6)`.
  Deep-compares dataclasses; `Polygon` fields use `equals_exact(tol)`;
  optional `update_mode=True` rewrites the expected JSON in place.
- `tests/test_golden_comparator.py` — covers: equal dataclasses pass,
  unequal fail with diff, Polygon within / outside tolerance,
  nested list/dict handling, update-mode round-trip.
- `conftest.py` (new) — `--update-goldens` pytest flag.

Commit: `feat(step03): polygon-aware golden comparator + --update-goldens flag`.

Verification: `pytest tests/test_golden_comparator.py` green; flag
appears in `pytest --help`.

### 4.5 Stage geometry helpers (`stages/_helpers.py`)

Port from Cell `geometry.py`: `to_shapely(part)`, `polygon_parts(...)`,
`part_theta(part)`. Adapt to new `ShapePart` (which already exposes
`exterior` + `holes` directly — should be a thin re-implementation).

Files:

- `src/room_layout/stages/_helpers.py`.
- `tests/test_stages_helpers.py` — unit tests.

Commit: `feat(step03): stages geometry helpers (port from cell geometry.py)`.

### 4.6 `DimensionPolicy` (`stages/dimensions.py`)

Port from Cell `dimensions.py`. Includes `DimensionPolicy` dataclass +
`is_quantum_aligned(value, q)` + `split_interval(...)` + any helper used
by atomize / regionize. `__post_init__` validation for positive quanta.

Files:

- `src/room_layout/stages/dimensions.py`.
- `tests/test_stages_dimensions.py`.

Commit: `feat(step03): dimension policy + quantum helpers`.

### 4.7 Territory (`stages/territory.py`)

**Order note (2026-05-28)**: swapped ahead of atomize. `atomize` imports
`resolve_territories` / `collect_cross_theta_contact_coords` /
`KIND_CURVED` from `territory` and calls `resolve_territories(...)` as its
first step, so territory is a hard prerequisite. Original Plan ordered
atomize (4.7) before territory (4.8); corrected here.

Files:

- `src/room_layout/stages/territory.py` — `Territory` dataclass +
  `part_kind(part)` + `resolve_territories(floor: FloorShape)` (S03-D13)
  + `collect_cross_theta_contact_coords(floor, territories)` + the
  `KIND_AXIS_ALIGNED` / `KIND_ROTATED` / `KIND_CURVED` constants.
- `tests/test_stages_territory.py`.

No standalone viz (territory is intermediate; visualized as part of
regionize). No standalone golden — output is absorbed into
`regionize.json` and covered indirectly by the regionize goldens plus
direct unit tests (S03-D9 thoroughness is satisfied via the downstream
stage; territory is a well-exercised module elsewhere).

Commit: `feat(step03): territory resolution`.

### 4.8 Atomize + viz + 33 goldens

Files:

- `src/room_layout/stages/atomize.py` — `Atom` dataclass (frozen) +
  `atomize(floor: FloorShape, policy)` (S03-D13).
- `src/room_layout/viz/stages/atomize.py` — `save_atom_figure(...)`.
- `tests/golden/case_*/atomize.json` × 33.
- `tests/golden/case_*/atomize.png` × 33.
- `tests/test_stages_atomize.py` — unit tests (orientation, partitioning,
  edge cases).
- `tests/test_golden_per_stage.py` — initial parametrized golden test
  covering atomize (other stages added in their own work items).

Split into **8a** (algorithm port + unit tests — committed) and **8b**
(viz + golden bootstrap, this part). `atomize.json` holds a **digest**,
not full per-atom geometry (S03-D14).

Commit (8b): `feat(step03): atomize dev-bridge viz + 33-case digest goldens`.

**Manual review checkpoint**: this is the first "big" work item where
golden bootstrap happens. Review pattern: render all 33 atomize PNGs
to `outputs/step03/` + `tests/golden/<case>/`, eyeball each for sanity
(atom count, boundary alignment, theta inheritance), THEN commit
goldens. If any case looks wrong, fix algorithm and re-render before
commit. The digest golden (S03-D14) pins count / area / part-assignment
/ sliver / bbox; the PNG is the human-facing artifact for the parts a
digest can't capture (boundary placement).

### 4.9 Regionize + viz + 33 goldens

Files:

- `src/room_layout/stages/regionize.py` — `Region` dataclass + `regionize(
  shape, atoms, policy, target_area)`.
- `src/room_layout/viz/stages/regionize.py` — `save_region_figure(...)`.
- `tests/golden/case_*/regionize.json` × 33.
- `tests/golden/case_*/regionize.png` × 33.
- `tests/test_stages_regionize.py`.
- `tests/test_golden_per_stage.py` — extend to cover regionize.

Commit: `feat(step03): regionize + viz + 33-case goldens`.

**Manual review checkpoint** (second of three): regionize is the
algorithm's "where do walls roughly go" decision, so visually
checking R# labels + areas across all 33 cases is the most
load-bearing inspection of the Step.

### 4.10 Atom graph + region graph + 33 goldens

**Dependency note (2026-05-28)**: `region_graph` imports `build_atom_graph`
from `atom_graph` — `atom_graph` was mis-bucketed as Phase 8 in the
original Plan but is a Phase 4 dependency (it only needs `atomize` /
`dimensions` / `_helpers` / `schema`). Ported here, ahead of
`region_graph`. Both `build_atom_graph` and `build_region_graph` return
plain dataclasses (`AtomGraph` / `RegionGraph`), not `networkx.Graph`.

Split into **10a** (both graph modules + unit tests) and **10b** (viz +
goldens).

10a files:

- `src/room_layout/stages/atom_graph.py` — `AtomEdge` + `AtomGraph` +
  `build_atom_graph(floor, ...)`. Intermediate (consumed by
  region_graph): no standalone viz/golden (S03-D15), unit-tested only.
- `src/room_layout/stages/region_graph.py` — `RegionEdge` +
  `RegionGraph` + `build_region_graph(floor, ...)`.
- `tests/test_stages_atom_graph.py`, `tests/test_stages_region_graph.py`.

10b files:

- `src/room_layout/viz/stages/regionize.py` — extend with
  `save_region_graph_figure(...)` (graph overlaid on regions).
- `tests/golden/case_*/region_graph.json` × 33 — **edges only** per
  S03-D15 (regions already pinned by `regionize.json`).
- `tests/golden/case_*/region_graph.png` × 33 (additive — same dir).
- `tests/test_golden_per_stage.py` — extend with the region_graph
  edges golden.

Commits: 10a `feat(step03): atom graph + region graph (algorithm port)`;
10b `feat(step03): region graph viz + 33-case edge goldens`.

### 4.11 Shape gate + viz + 33 goldens

Files:

- `src/room_layout/stages/shape_gate.py` — gate checks; raises
  `DimGateFailure` / `AccessSchemaFailure` (from Step 02) on violation.
- `src/room_layout/viz/stages/gates.py` — `save_gate_figure(...)` +
  `save_dimension_examples_figure(...)` (the singleton diagnostic).
- `tests/golden/case_*/gates.json` × 33.
- `tests/golden/case_*/gates.png` × 33.
- `tests/test_stages_shape_gate.py`.
- `tests/test_golden_per_stage.py` — extend.

Commit: `feat(step03): shape gate + dev-bridge viz + 33-case goldens`.

**Manual review checkpoint** (third of three): gates determine which
cases proceed to Step 04 growth; passing/failing wrongly here would
cascade.

### 4.12 Demo CLI

Files:

- `src/room_layout/viz/demo.py` — argparse CLI:
  `python -m room_layout.viz.demo --case <n> --stage <name> [--all]
  --out outputs/step03/`. Mirrors Cell `demos/visualize_phase.py`
  ergonomics, against the new schema.

Commit: `feat(step03): viz demo CLI for dev-bridge PNG generation`.

### 4.13 Step close + merge to `main`

- Tracker §1 / §2 all checked.
- Tracker §4 close summary filled.
- `docs/000_Progress_Tracker.md` §1 / §2 / §3 updated (Step 03 closed;
  Step 04 kickoff).
- Optionally: `src/room_layout/__init__.py` extends re-export to include
  `stages.atomize` / `stages.regionize` / etc. **Default**: do NOT
  re-export internal stage types per S03-D6. Decide at close.
- Commit on branch: `chore(step03): close — update progress tracker`.
- Switch to `main`: `git switch main && git merge --no-ff
  step03-geometrypipeline && git push`.
- CI green on `main` confirms merge.
- `git branch -d step03-geometrypipeline` after merge.

---

## 5. 의도적으로 하지 않는 것

- **Phase 6–8** (`seed_placement`, `growth_seed`, `growth_cells`,
  `growth_partition`, `growth_absorb`, `room_growth`, `corridor`,
  `corridor_*`, `atom_graph`) → **Step 04** (Algorithm core port).
- **`run()` entry point + `on_stage` callback + `manifest.json` writer**
  → **Step 06**.
- **`target_rules/<typology>.json` + `expand_program()` helper +
  `TargetAdapter`** → **Step 05**.
- **Canonical SVG renderer + `pipeline.gif`** → **Step 07**; the
  selective-port matplotlib bridge from this Step is throwaway.
- **`ResearchBIM_synthetic-bim` `Building` / `Storey` adapter** →
  Step 08, post-v1.
- **Multi-floor orchestrator** → Step 09, post-v1.
- **Cell test porting wholesale**: Cell's 17 test files stay under
  `archive/` as reference; new tests are written fresh against the new
  schema (S03-D11).
- **In-Python `LayoutFixture` form**: Cell's Python-form fixtures are
  one-shot converted to JSON and the Python form is dropped (S03-D7).
- **Re-exporting internal stage types** (`Atom` / `Region` /
  `DimensionPolicy` etc.) from `room_layout` or `room_layout.schema`:
  these are pipeline-internal (S03-D6).

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| **Manual golden bootstrap for 33 cases is the single biggest cost** — for each "big" work item (4.7 / 4.9 / 4.11) all 33 outputs need eyeball review before goldens are committed. Bad goldens lock in bugs. | Render PNGs first → eyeball pass against Cell's pre-existing PNGs (if available) and against the visual vocabulary in `archive/celllayout/algorithm/celllayout_tf/viz.py` → THEN commit JSON+PNG goldens. Per-stage commit boundary matches review boundary so re-do scope is contained. |
| Cell internal types (`Atom` / `Region` / `Territory`) were built around Cell's old `ShapePart` (single-floor `parts` only). Refactoring against the new multi-floor schema may surface non-trivial shape — e.g., does `Atom.part_id` still make sense across floors? | Phase 3–5 are single-floor stages in v1 (per Pipeline §2.1 — algorithm processes one floor at a time). New schema's `FloorShape.parts` is just `ShapePart` list, so `Atom.part_id: int` maps directly to `FloorShape.parts[i]`. Multi-floor orchestration is Step 09, not this Step. |
| `DimensionPolicy` is consumed by atomize / regionize / shape_gate — any divergence between Cell's implementation and the port surfaces as algorithm drift. | Port `dimensions.py` (4.6) before any consumer (4.7+). Unit tests in `test_stages_dimensions.py` use known-good Cell example values for regression. |
| Selective-port viz may drift in appearance from Cell viz (different label position / font / spacing) → makes visual regression checks against Cell's pre-existing PNGs harder. | Accept the drift; goldens are about the new code's output, not parity with Cell. PNG sidecars exist for *future* regression coverage (i.e., within Step 03+ history), not for direct Cell parity. |
| Branch lifetime > Step 02's (1 day) — Step 03 is bigger. Drift from `main`. | Rebase or merge `main` into branch every 1–2 work items. Solo single-developer realistic drift is small but real. |
| 33 × 4 = 132 JSON files + 132 PNG files + 33 input.json = ~300 new files in git. Risk: bloated commits, slow `git status` on `tests/golden/`. | PNG dpi=130 keeps individual PNGs ~30–80 KB. JSON files are 1–10 KB each. Total ~10–20 MB across 33 cases. Manageable. If repo bloat becomes a concern post-Step 04, consider Git LFS for PNGs only — JSON stays in regular git. |
| `pytest --update-goldens` is risky if accidentally enabled — silently rewrites all goldens. | Hook prints a loud `[GOLDEN UPDATE] rewriting tests/golden/<case>/<stage>.json` line per file. Make goldens updates always be a separate commit so PR review catches "this PR shouldn't be updating goldens but is". |
| Cell `viz.py` imports its own internal modules (`from .atomize import atomize`) — using it directly as a reference shows API patterns we don't want to inherit (e.g., calling the algorithm inside the renderer). | Render functions in `viz/stages/` take *outputs* (lists of `Atom` / `Region`) as parameters, not `ShapeInput`. The CLI (`viz/demo.py`) orchestrates: run pipeline → pass results to renderer. Decouples viz from algorithm. |

---

## 7. Next-Step linkage

Step 03 close → **Step 04 (Algorithm core port)** kickoff.

At Step 04's §4.1 commit (per `proto3:D016` H011 deferred-archive pattern):

- `git mv 003_Step03_GeometryPipeline_Plan.md legacy/step03/`
- `git mv 003_Step03_GeometryPipeline_Tracker.md legacy/step03/`
- Write `004_Step04_AlgorithmCore_Plan.md` + Tracker.

Step 04 will:

- Port Cell **Phase 6–8** modules into `src/room_layout/stages/`:
  `seed_placement.py`, `growth_seed.py`, `growth_cells.py`,
  `growth_partition.py`, `growth_absorb.py`, `room_growth.py`,
  `corridor.py` + `corridor_*.py` (×5), `atom_graph.py`.
- Reuse `Region` / `DimensionPolicy` / `Atom` from Step 03 — no
  re-declaration; these are the input to growth.
- Add per-stage golden JSON + PNG for each new Phase 6–8 stage (seed,
  layout, corridor) on the same 33 cases — Step 03's golden
  infrastructure carries through; only the stage list grows.
- Extend the 4 dev-bridge renderers with `viz/stages/seed.py`,
  `viz/stages/layout.py`, `viz/stages/corridor.py` matching the same
  selective-port pattern.
- Establish the final `LabeledRoomLayout` output for each fixture
  (Step 04's last stage — corridor — emits the final result). This is
  the input to Step 06's `run()` integration.

---

## A. (Reserved) Appendix — inline file contents

_Not used this Step._ All work items 4.2–4.12 produce code written
directly; no single-use scaffolding needed in the Plan itself.
