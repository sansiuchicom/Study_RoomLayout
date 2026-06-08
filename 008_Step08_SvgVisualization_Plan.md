# 008 Step 08 — SVG Visualization Plan

Status: In progress (kickoff on `step08-svg-viz`)
Type: Step plan
Branch: `step08-svg-viz` (D005 — branch on **size + milestone**, not the classic
integration/regression triggers. Honest framing: Step 08 is **additive viz** —
`run()` is untouched (S08-D7), so regression risk to the 975-test suite is *low*
(SVG/GIF are downstream consumers of `run()`'s return value + the `on_stage`
trace, never feeding back). The branch is justified instead by (a) **size** — a
self-contained new module cluster (`viz/svg.py` + `viz/palette.py` + `viz/gif.py`
+ an `SvgRunWriter` + a `pyproject` dep + tests), and (b) **milestone** — this is
the **v1 ship gate**; a clean branch gives the v1-closing PR a reviewable
boundary, the same shape Step 07 had for its external review. Step 06 (small,
mostly-new-files) stayed on `main`; this cluster is larger and milestone-marking.)
Last updated: 2026-06-08

---

## 0. Purpose

Step 08 is the **v1 ship gate**. It delivers the **canonical visualization
path** — a layered SVG renderer + a `make_gif()` pipeline-progression animation —
consuming the `StageOutput` trace (`on_stage` hook) and the `debug_run` layout
that Step 07 landed (D006). After Step 08, the matplotlib renderers demote from
"the viz path" to "a development helper"; SVG becomes the canonical artifact
(Pipeline §5.1, `proto3:D013`).

**Honest framing — this is not a mechanical port.** The Step DoD (Pipeline §5.1)
reads "proto3 `viz/svg.py` ported", but reading the archive
(`archive/proto3/src/proto3/viz/svg.py`) shows that file is a **near-empty
skeleton**: it draws only the footprint (layer 0) + a 100 mm reference grid, and
**raises `ValueError`** if you pass `atoms` / `regions` / `spine` — explicitly
deferring real layer rendering to "proto3's Step 07", which proto3 never reached
before it was superseded. So the real work is:

1. **Adopt proto3's *architecture*** — the stable ordered named `<g>` layer
   groups (`layer-NN-name` class convention), `xml.etree.ElementTree`
   construction, Y-flip (math-y-up → SVG-y-down), `viewBox` + padding + display-
   scale — and
2. **Implement the layers for *our* data types**, which proto3 never did, against
   our **meters** unit (proto3 was mm — `proto3:D019` dropped, Pipeline §2.4) and
   our **schema** (`ShapeInput` / `FloorShape` / `ShapePart` with parts + holes +
   `vertical_anchors`, not proto3's single `BuildingInput.footprint`).

**Layer stack re-derived (S08-D2).** proto3's 12-layer `LAYER_ORDER`
(`footprint, anchors, regions, atoms, graph-edges, role-scores, spine, slots,
seeds, grown, doors, failure`) is **proto3's spine-first vocabulary**. Our
pipeline is Cell-derived **seed-first growth + post-hoc corridor carve** — it has
no `spine`, `role-scores`, or `slots` stage, and it *does* have `corridor`
(carved), labeled `rooms` (role-fill), and `vc` anchors that proto3's stack lacks.
We keep proto3's *structural conventions* but re-derive the layer *names* from our
actual stages (§3.1 / 3.2–3.8).

Cross-references:

- `docs/000_Pipeline_Overview.md` §3.1 (stage flow → layer source), §3.9
  (cross-cutting: "debug artifacts (SVG default per `proto3:D013`)"), §5.1
  (Step 08 DoD), §5.2 (post-v1).
- `docs/000_Architecture_Decisions.md`:
  - **D006** — output directory convention; `on_stage` hook + `StageOutput` +
    `manifest.json` (landed Step 07); canonical render lands **here**.
  - **proto3:D013** — SVG-first viz, stable layer order, coded visual vocabulary.
  - **S01-D10** — "viz at every Step".
- `archive/proto3/src/proto3/viz/{svg,palette}.py` — the architecture template
  (skeleton: footprint + grid only; layer-group + ElementTree + viewBox/Y-flip).
- `legacy/step07/007_Step07_EntryPoint_Plan.md` — S07-D3 (trace seam: the SVG
  renderer is a pure `StageOutput` consumer, deferred here), S07-D4 (viz seam:
  matplotlib is the dev-bridge; canonical SVG is Step 08).
- `src/room_layout/viz/` — the 8 existing matplotlib renderers (`make_gif`
  frame source, S08-D3); `viz/stages/final.py` `ROLE_COLORS` (palette merge,
  S08-D6).
- `src/room_layout/{debug_run,schema/run_config,schema/trace}.py` — the
  `on_stage` / `DebugRunWriter` / `RunConfig.debug_artifacts` seam (S08-D7).

---

## 1. Definition of Done

```text
Step 08 closes when:

1. Canonical SVG renderer (viz/svg.py, NEW) — render() produces a single
   layered .svg from a LabeledFloorLayout (+ optional upstream stage payloads
   for debug layers). Stable, ordered, named <g> layer groups (layer-NN-name
   class); absent layers register as empty <g> (contract — layer order stays
   stable as inputs vary). Meters in; Y-flipped; viewBox + 5% padding +
   display-scale. Adopts proto3's architecture (S08-D2 framing); implements
   our layers.

2. Layer stack re-derived from our pipeline (S08-D2) — ~12 named layers
   sourced from our stages (grid / footprint / atoms / regions / region-graph
   / anchors / seeds / grown / corridor / rooms (role-fill) / labels / failure),
   z-ordered debug-low → final-high → failure-top. Exact list + order finalized
   at 4.2. No proto3 dead layers (spine / role-scores / slots dropped).

3. Single palette source of truth (viz/palette.py, NEW — S08-D6) — LAYER_ORDER
   + role/layer colors + grid spacing + label font. The matplotlib renderers
   (final.py ROLE_COLORS) and the SVG renderer both read it; the duplicate
   color table is removed (final.py imports from palette).

4. make_gif() (viz/gif.py, NEW — S08-D3/D4) — composes a pipeline-progression
   GIF (one frame per stage: input → atomize → regionize → region_graph → seed
   → layout → corridor → final) from the EXISTING matplotlib PNG renderers
   (pillow stitch). NOT search-candidate frames (orchestrator deferred); NOT
   SVG rasterization (no cairosvg dep). Consumes a debug-run dir or runs fresh.

5. RunConfig.debug_artifacts opt-in wiring (S08-D7) — run() stays UNCHANGED
   (pure; SVG rides the existing on_stage hook). An SvgRunWriter (on_stage
   callback, sibling of DebugRunWriter) renders each StageOutput to per-stage
   SVG; write_debug_run emits SVG (and/or PNG, GIF) when debug_artifacts
   selects it. debug_artifacts extends from bool to a richer selector
   (shape decided at 4.5).

6. Tests structural, not byte-golden (S08-D5) — assert layer count / order /
   class names, per-layer element presence + counts, valid XML, footprint
   present, role-fill colors present. SVG byte-goldens are float/attr-order
   brittle (matches the existing test_viz_final smoke philosophy + the GEOS-
   golden caution). gif: smoke (file written, non-empty, N frames).

7. pyproject viz extra adds pillow (make_gif). matplotlib stays the viz extra
   (dev-bridge + gif frames). No cairosvg / SVG-raster dep.

8. Step 07 docs archived (4.1, proto3:D016 H011): git mv 007_*.md →
   legacy/step07/. Progress Tracker: Step 08 opened.

9. ruff (BOTH check AND format) + full pytest green (conda IfcOpenHouse,
   GEOS 3.14.1); Plan/Tracker closed; S08-D series finalized; README +
   Progress + Pipeline status synced to "v1 ships"; merged --no-ff to main.
```

---

## 2. 결정 기록

Decisions locked during Step 08 planning (chat discussion 2026-06-08). The six
design forks (S08-D2..D7) were agreed against the recommendations in that
discussion; S08-D1 is the branch call. Predecessor decisions referenced as
`S0N-Dxx` / `proto3:Dxxx`.

| # | Topic | Decision |
|---|---|---|
| **S08-D1** | Branch | Work on `step08-svg-viz`, merge `--no-ff` at close. Honest D005 framing: the classic **integration / regression** triggers are *weak* here — Step 08 is additive viz, `run()` is untouched (S08-D7), and SVG/GIF are downstream of `run()`'s return value, so the 975-test suite cannot drift from this work. The branch is justified by **size** (a self-contained new module cluster: `svg.py` + `palette.py` + `gif.py` + `SvgRunWriter` + a `pyproject` dep + tests) and **milestone** (the **v1 ship gate** — a clean PR boundary for the v1-closing change, mirroring Step 07's external-review shape). Stated plainly rather than manufacturing a fake regression trigger (honest-fix). |
| **S08-D2** | Layer stack — re-derive, don't copy proto3 | proto3's 12-layer `LAYER_ORDER` is its **spine-first** vocabulary (`spine` / `role-scores` / `slots` have no stage in our Cell-derived seed-first + post-hoc-carve pipeline; they would be permanently-empty dead layers). And proto3's `viz/svg.py` never implemented the layers anyway (skeleton — footprint + grid only). So we **keep proto3's structural conventions** (ordered named `<g>` groups, `layer-NN-name` class, empty-group-for-absent-layer contract, ElementTree, Y-flip / viewBox / padding) and **re-derive the layer names from our stages** (§3.1). Indicative 12-layer z-order (bottom→top): `grid → footprint → atoms → regions → region-graph → anchors → seeds → grown → corridor → rooms (role-fill) → labels → failure`. Debug layers low, final role-fill + labels high, failure markers on top. Final list/order is fixed at 4.2 (like Step 07 fixed its module split at the work item). |
| **S08-D3** | `make_gif` frame source = matplotlib PNG, not SVG raster | `make_gif` is a **net-new** deliverable (it exists in neither proto3 nor celllayout — only the README/Pipeline promise). We already have **8 working matplotlib PNG renderers** (`viz/stages/*.py` + `final.py`) covering every pipeline stage. `make_gif` stitches those PNG frames via `pillow`. Rejected: SVG → raster → GIF (needs `cairosvg`/`svglib` — a heavier, more fragile dependency for no v1 benefit). SVG stays the canonical **static** per-stage/final artifact; the GIF is the **animation**, and PNG frames are a fine, robust source for it. |
| **S08-D4** | GIF semantics = pipeline progression | One frame per **pipeline stage** (input → atomize → regionize → region_graph → seed → layout → corridor → final), i.e. the geometry build-up for a single layout. NOT a search-candidate animation — the Search Orchestrator is deferred (Pipeline §4.1), so there is no candidate sequence to animate. This maps 1:1 onto the existing 8 stage renderers (S08-D3). |
| **S08-D5** | SVG tests structural, not byte-golden | Assert: valid XML; exactly N layer `<g>` groups in the right order with the right `layer-NN-name` classes; expected element presence/counts per layer (≥1 footprint polygon; role-fill `<polygon>`s present with palette colors; grid lines present); empty `<g>` for absent layers. **No byte-golden** SVG — float formatting + attribute order make them brittle, and the existing viz suite (`test_viz_final`) is already smoke/structural, not pixel-golden (consistent with the GEOS-golden caution). The Pipeline §5.1 phrase "lines up with golden" is read as **structural** golden. gif: smoke (written, non-empty, frame count). |
| **S08-D6** | One palette source of truth | Today colors live in **two** places: `viz/stages/final.py` `ROLE_COLORS` (matplotlib, 7-class) and proto3's `palette.py` `LAYER_COLORS` (mm-era, different keys). Step 08 creates one `viz/palette.py` (`LAYER_ORDER` + role/layer colors + `GRID_SPACING` in meters + label font) as the **single source**; both the matplotlib renderers and the SVG renderer import from it (`final.py` drops its local `ROLE_COLORS` table). Prevents the SVG and PNG paths from drifting apart. |
| **S08-D7** | `run()` unchanged — SVG rides `on_stage` | Step 08 touches **no** pipeline code. The `on_stage` hook + `StageOutput` (Step 07, S07-D3) are exactly the consumer seam SVG needs. An `SvgRunWriter` (an `on_stage` callback, sibling to `DebugRunWriter`) renders each stage payload to SVG; `write_debug_run` gains SVG/GIF emission gated on `RunConfig.debug_artifacts`. `run()` stays pure (no I/O, `on_stage=None` default). Keeps the v1-closing change a pure additive viz layer — the regression argument behind S08-D1. |

Decisions expected to emerge *during* build (recorded as **S08-D8+** when they
land): the final layer list/order (4.2); the `debug_artifacts` selector shape
(`bool` → `frozenset[str]` of `{"json","png","svg","gif"}`, or `bool` + render-
options — 4.5); the `make_gif` entry signature (run-id dir vs fresh run; frame
duration / loop); per-stage SVG vs one cumulative-reveal SVG for the debug path.

---

## 3. Directory structure (indicative target state)

```text
src/room_layout/
  viz/
    __init__.py        # MODIFIED: export render (SVG) + make_gif + palette names
    palette.py         # NEW: single source — LAYER_ORDER + colors (meters) + font (S08-D6)
    svg.py             # NEW: canonical layered SVG renderer (S08-D2) — render()
    gif.py             # NEW: make_gif() — PNG-frame pipeline-progression stitch (S08-D3/D4)
    stages/
      final.py         # MODIFIED: import ROLE_COLORS from palette (drop local table — S08-D6)
  debug_run.py         # MODIFIED: SvgRunWriter (on_stage→SVG) + SVG/GIF emit on debug_artifacts (S08-D7)
  schema/
    run_config.py      # MODIFIED: debug_artifacts selector extended (bool → richer — 4.5)

tests/
  test_viz_svg.py      # NEW: structural SVG tests (S08-D5)
  test_viz_gif.py      # NEW: gif smoke (S08-D5)
  test_palette.py      # NEW: palette completeness (7 roles, layer order) — may fold into svg test
  test_debug_run.py    # MODIFIED: SVG/GIF artifact emission under debug_artifacts

pyproject.toml         # MODIFIED: viz extra += pillow (S08-D3 / DoD-7)
legacy/step07/         # NEW (4.1): 007_Step07_*.md moved here (proto3:D016 H011)
```

Module split (one `svg.py` vs an `svg/` package; `gif.py` vs folding into
`svg.py`; whether `SvgRunWriter` lives in `debug_run.py` or a new `viz/trace.py`)
is finalized at the work items; the layout above is indicative.

---

## 4. Work items

Bottom-up (dependency order): palette first (the shared vocabulary), then the
SVG renderer, then the gif + the trace wiring, then tests + close. Each item is
one commit (proto3:D015). Mirrors into Tracker §1 (proto3:D016).

| # | Work item | Verify |
|---|---|---|
| **4.1** | Kickoff — Plan + Tracker land + `git mv 007_Step07_*.md → legacy/step07/` (proto3:D016 H011) + Progress Tracker (Step 08 opened) | docs review; `legacy/step07/` populated; tree staged |
| **4.2** | `viz/palette.py` (NEW) — single source of truth: `LAYER_ORDER` (our ~12 stack, S08-D2), role/layer colors (meters), `GRID_SPACING` (m), label font; **finalize the layer list/order here** | palette imports clean; LAYER_ORDER covers our stages; 7 roles colored |
| **4.3** | `viz/stages/final.py` (MOD) — import `ROLE_COLORS` from `palette`; drop the local table (S08-D6) | `test_viz_final` still green; no duplicate color table |
| **4.4** | `viz/svg.py` (NEW) — `render(floor_layout, *, stages…) -> .svg`: layered `<g>` groups (S08-D2), meters + Y-flip + viewBox + 5% pad + display-scale; footprint + grid + anchors + role-fill rooms + corridor + labels; absent layers = empty `<g>` | structural test (4.7); renders a fixture to valid SVG |
| **4.5** | `debug_run.py` (MOD) — `SvgRunWriter` (on_stage→per-stage SVG); `write_debug_run` emits SVG when `RunConfig.debug_artifacts` selects it; **extend `debug_artifacts`** selector (4.x decision) — `run()` untouched (S08-D7) | a debug run with svg-selected writes `NN_<stage>.svg`; `run()` signature unchanged |
| **4.6** | `viz/gif.py` (NEW) — `make_gif()`: pipeline-progression frames from the matplotlib renderers (input→…→final) stitched via `pillow` (S08-D3/D4); `pyproject` viz extra += `pillow` | renders a fixture to a non-empty multi-frame `.gif` |
| **4.7** | Tests — structural SVG (`test_viz_svg.py`: layer order/count/classes, footprint, role-fill, grid) + gif smoke (`test_viz_gif.py`) + palette completeness + `test_debug_run` artifact emission (S08-D5) | new viz tests green; full suite green |
| **4.8** | Close — README Status + Tracker + Progress Tracker + Pipeline status synced to **v1 ships**; S08-D series finalize; ruff (check + format) + pytest green; `--no-ff` merge to `main` | CI green; merged; v1 tagged-as-shipped in docs |

---

## 5. 의도적으로 하지 않는 것 (out of scope)

| Item | Why / where |
|---|---|
| SVG → raster → GIF (cairosvg / svglib) | Rejected at S08-D3. `make_gif` uses the existing matplotlib PNG renderers (pillow stitch); SVG is the canonical *static* artifact only. No SVG-raster dependency in v1. |
| Search-candidate / search-path animation | Search Orchestrator is deferred (Pipeline §4.1); there is no candidate sequence. GIF animates the single-layout **pipeline progression** only (S08-D4). |
| proto3's `spine` / `role-scores` / `slots` layers | Dropped at S08-D2 — no corresponding stage in our seed-first + post-hoc-carve pipeline. Re-deriving the stack avoids permanently-empty dead layers. |
| Interactive / web SVG (hover, toggles, JS) | v1 ships static `.svg` files. Layer `<g>` groups are class-tagged (re-derived from proto3), so interactivity is a *later* CSS/JS add-on, not v1. |
| Door glyphs on the SVG | `LabeledRoom.doors` is `None` in v1 (Pipeline §2.4); the `doors` layer has no data, so it is not in our re-derived stack (S08-D2). Re-add when corridor carving emits door positions. |
| Byte-golden SVG regression | Rejected at S08-D5 (float/attr-order brittle). Tests are structural. |
| Multi-floor SVG composition / sheet layout | `run()` is single-floor per call (Step 10, D001). v1 renders one `LabeledFloorLayout`; multi-floor sheet assembly is post-v1. |
| Wall-thickness / centerline-to-inner-face rendering | v1 contract is centerline (Pipeline §2.4); the renderer draws centerline polygons as-is. The inset is a separable output post-transform (Progress Tracker §5.2), not a renderer concern. |

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| "Port proto3 `viz/svg.py`" undersells the work (it is a skeleton) | Surfaced at S08-D2 / §0. The plan scopes the *real* work (implement our layers against meters + our schema), not a mechanical copy. The DoD (§1) is written to that reality. |
| Layer stack churn — picking the wrong 12 layers early forces rework | The list is **finalized at 4.2** (not front-loaded), after the palette consumer is concrete; §3.1-style stage→layer mapping is the guide. Empty-group contract means adding/removing a layer is localized to `LAYER_ORDER` + one draw fn. |
| `debug_artifacts: bool` is too coarse for "emit svg but not png/gif" | 4.5 extends it (likely `frozenset[str]` of `{"json","png","svg","gif"}`); the field is already flagged for Step-08 extension in its own docstring. Recorded as S08-D8 when fixed. |
| `make_gif` couples to matplotlib (the dev-bridge we are demoting) | Accepted and deliberate (S08-D3): matplotlib stays a *dev/gif* helper, not the canonical *static* path. The canonical artifact (SVG) has no matplotlib dependency. Keeps `pillow` the only new dep (no cairosvg). |
| Palette merge breaks `test_viz_final` (final.py loses its `ROLE_COLORS`) | 4.3 is its own commit with `test_viz_final` as the gate; the merge is a pure import redirect (same 7 colors), so a regression is immediately visible. |
| SVG Y-flip / meters scaling bugs (proto3 was mm) | Unit conversion is explicit (meters in, no mm); stroke widths re-scaled to meters; a structural test (4.7) checks the footprint polygon's transformed coordinates land inside the viewBox. |

---

## 7. Next-Step linkage

Step 08 is the **final v1 Step**. On close, `run()` works end-to-end on single-
floor apartments **with the canonical SVG viz path** (+ a pipeline-progression
GIF), and the matplotlib renderers are demoted to a development helper. **v1
ships** (Pipeline §5.1 ship gate).

Post-v1 (Pipeline §5.2), independent of each other:

- **Step 09** — ResearchBIM adapter (`adapters/researchbim.py`): drop-in for the
  `ResearchBIM_synthetic-bim` Stage 4 entry point (`Building` / `Storey`
  mutation translation).
- **Step 10** — Multi-floor orchestrator: wraps per-floor `run()` with vertical-
  anchor alignment + per-floor program allocation + cross-floor validation
  (D001 / D004). Multi-floor SVG sheet composition would land with it.
