# 008 Step 08 — SVG Visualization Tracker

Status: Completed — merged `--no-ff` to `main` (v1 ship gate, 2026-06-08)
Type: Step tracker
Branch: `step08-svg-viz`
Last updated: 2026-06-08

Companion to `008_Step08_SvgVisualization_Plan.md` (proto3:D016). §1 mirrors
Plan §4 1:1, adding Status + Commit. §2 mirrors Plan §1 (DoD). §3 records
drifts / sub-decisions (S08-D8+) as work lands.

---

## 1. Plan §4 work items

| # | Work item | Status | Commit |
|---|---|---|---|
| **4.1** | Kickoff — Plan + Tracker + `git mv 007_*.md → legacy/step07/` + Progress Tracker (Step 08 opened) | ✅ | `29eb39a` |
| **4.2** | `viz/palette.py` (NEW) — single source: `LAYER_ORDER` + colors (m) + grid/font; finalize layer list/order | ✅ | `73d6c19` |
| **4.3** | `viz/stages/final.py` (MOD) — import `ROLE_COLORS` from `palette`; drop local table (S08-D6) | ✅ | `1ccc563` |
| **4.4** | `viz/svg.py` (NEW) — layered SVG `render()`: footprint + grid + anchors + role-fill + corridor + labels; meters + Y-flip + viewBox | ✅ | `799b315` |
| **4.5** | `debug_run.py` (MOD) — `SvgRunWriter` + SVG/GIF emit on `debug_artifacts`; extend selector; `run()` untouched (S08-D7) | ✅ | `ec0072c` |
| **4.6** | `viz/gif.py` (NEW) — `make_gif()` PNG-frame pipeline-progression stitch (pillow); `pyproject` += pillow | ✅ | `4b0e288` |
| **4.7** | Tests — structural SVG + gif smoke + palette completeness + debug-run artifact emission (S08-D5) | ✅ | `6facbdd` |
| **4.8** | Close — README + Progress + Pipeline synced to **v1 ships**; S08-D finalize; ruff + pytest green; `--no-ff` merge | ✅ | _(this commit)_ |

---

## 2. Definition of Done checklist (Plan §1)

- ✅ 1. Canonical SVG renderer (`viz/svg.py`) — layered `<g>`, empty-group contract, meters + Y-flip + viewBox + pad + scale (`799b315`)
- ✅ 2. Layer stack re-derived from our pipeline (~12, no proto3 dead layers) — finalized at 4.2 (`73d6c19`)
- ✅ 3. Single palette source (`viz/palette.py`); `final.py` reads it (duplicate table removed) — `73d6c19` / `1ccc563`
- ✅ 4. `make_gif()` — pipeline-progression GIF from matplotlib PNG frames (pillow) (`4b0e288`; 7 frames, seed stage omitted)
- ✅ 5. `RunConfig.debug_artifacts` opt-in wiring (`SvgRunWriter`); `run()` unchanged (`ec0072c`)
- ✅ 6. Tests structural (layer order/counts/classes, role-fill, grid), not byte-golden; gif smoke (`6facbdd`)
- ✅ 7. `pyproject` viz extra += `pillow`; no cairosvg / SVG-raster dep (`4b0e288`)
- ✅ 8. Step 07 docs archived → `legacy/step07/` (H011); Progress Tracker Step 08 opened (`29eb39a`)
- ✅ 9. ruff (check + format) + full pytest green; docs synced to "v1 ships"; merged `--no-ff`

---

## 3. Notes / decisions during execution

(Filled as work items land — drifts, surprises, sub-decisions S08-D8+.)

- **S08-D9 (4.5) — `SvgRunWriter` renders only the `labeling` (final) stage.**
  The canonical SVG (`viz/svg.render`) consumes a `LabeledFloorLayout`; that is
  the v1 deliverable. Rendering the geometry-debug stages (atoms / regions /
  region-graph / growth / corridor) to SVG would duplicate the existing
  matplotlib dev-bridge (which also feeds `make_gif`, 4.6) and would be
  half-doable at best (growth / corridor carry region-id *sets*, not polygons —
  they need cross-stage region geometry). So v1 draws the final layered SVG per
  floor and leaves the 6 debug layers as empty `<g>` (the empty-group contract
  makes lighting them a localized post-v1 add). Also: `RunConfig.debug_artifacts`
  went `bool → tuple[str, ...]` (`("json","svg")`) — a real second format (SVG)
  now exists, so the selector is not speculative.
- **S08-D8 (4.4 follow-up) — footprint drawn as the part UNION, not per-part.**
  Found via a user viz review of `case_33`: a phantom rectangle "box" appeared
  over the rooms. Root cause — the footprint arrives as *overlapping design
  primitives* (Pipeline §2.1 "parts preserved, not unioned": `case_33` = body
  `(0,0)-(12,10)` + wing `(8,5)-(15,9)`, overlapping 16 m²), and `_draw_footprint`
  outlined *each* part, painting the internal overlap seam as a box that matched
  no room boundary. Fix: outline `unary_union(parts)` (true building perimeter;
  evenodd preserves the donut hole). 4/5 sample cases had ≥2 parts and were all
  affected. (My first read — "two same-role rooms' shared border" — was wrong;
  corrected after point-containment + path-count diagnosis showed no overlap /
  no extra path, only the 2-part footprint.)
- **4.2 — layer order locked as the Plan §2 indicative 12** (no change):
  `grid, footprint, atoms, regions, region-graph, anchors, seeds, grown,
  corridor, rooms, labels, failure`. The S08-D2 list survived contact with the
  palette consumer, so it stands without an S08-D8 revision. `role_color()` is
  **tolerant** (fallback, never raise) — a renderer is a post-`run()` consumer
  and must not crash a debug view (contrast proto3's raising
  `role_to_palette_key`, a pre-validation tool). `PART_COLORS` deliberately
  stays in `_helpers` (matplotlib-debug-only, not canonical role/layer vocab).

---

## 4. Close summary

Step 08 (SVG visualization) complete on `step08-svg-viz` — 8 work items —
**the v1 ship gate** (Pipeline §5.1). Merged `--no-ff` to `main`. **v1 ships.**

**Delivered:** the canonical visualization path. `viz/palette.py` (single
vocabulary, S08-D6) + `viz/svg.py` (`render()` — 12 ordered named `<g>` layers
**re-derived from our pipeline**, S08-D2; Y-flip + viewBox + meters; footprint =
part union; role-fill rooms + corridor + labels + optional anchors) +
`viz/gif.py` (`make_gif()` — 7-frame pipeline-progression via matplotlib +
`pillow`, S08-D3/D4) + `SvgRunWriter` & `RunConfig.debug_artifacts`
`bool→tuple` selector (S08-D7/D9). `run()` is **untouched** — SVG rides the
Step-07 `on_stage` hook; matplotlib is demoted to a dev-bridge. `viz/__init__`
exports palette + `render` eagerly (matplotlib-free) and `make_gif` lazily, so
`import room_layout.viz` stays light.

**The honest framing held (S08-D2):** "port proto3 `viz/svg.py`" was really
*adopt its architecture, implement our layers* — proto3's file is a
footprint+grid skeleton that raised on real layers, in mm, against a different
schema. The 12-layer stack was re-derived (proto3's `spine`/`role-scores`/
`slots` dropped; our `corridor`/`rooms`/`labels` added).

**Decisions:** S08-D1 (branch on size+milestone), D2 (re-derive layer stack),
D3 (gif from matplotlib PNG, not SVG raster), D4 (gif = pipeline progression),
D5 (structural tests, not byte-golden), D6 (single palette), D7 (`run()`
untouched), D8 (footprint union — a viz review caught a phantom overlap-seam
box), D9 (`SvgRunWriter` renders only the final stage; geometry-debug stays
matplotlib).

**Pre-merge review (12 findings):** 1 fixed — `debug_artifacts` token
validation (#9, this branch). 11 triaged as **documented v1-accepted limits /
post-v1 deferrals** (not new defects): GEOS-pinned goldens (#1 — the 70 fails a
reviewer saw off-GEOS; green at 3.14.1), B5/B6/C10 xfails (#2), carve standalone
(#3), area-aware growth (#4), wall-thickness (#5), typology coverage (#6 — by
design), frozen-mutable (#7), NaN/inf (#8), helper `ValueError` vs never-crashes
(#10 — verified *currently unreachable*: the apartment cardinality gate blocks
both `program_to_fixture` `ValueError` paths before they're hit), provenance
(#11). #8 + #10 are cheap pre-v1 hardenings declined for now (out of Step-08
scope, unreachable on the shipped path).

**Verify:** 995 pytest + 4 xfail (conda `IfcOpenHouse`, GEOS 3.14.1); ruff
check + format clean. Structural SVG tests (not byte-golden, S08-D5) + gif
smoke + palette + token-validation.

**Not done (deliberate):** geometry-stage debug SVGs (S08-D9 — matplotlib
serves them; 6 SVG debug layers stay empty `<g>`, post-v1 extensible); SVG→GIF
rasterization (S08-D3); interactive/web SVG; multi-floor SVG sheets (Step 10).
Step 08 docs are archived at the next-Step kickoff (proto3:D016 H011) — there is
no next v1 Step, so they archive when Step 09/10 opens.
