# 008 Step 08 — SVG Visualization Tracker

Status: In progress (on `step08-svg-viz`)
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
| **4.4** | `viz/svg.py` (NEW) — layered SVG `render()`: footprint + grid + anchors + role-fill + corridor + labels; meters + Y-flip + viewBox | ☐ | — |
| **4.5** | `debug_run.py` (MOD) — `SvgRunWriter` + SVG/GIF emit on `debug_artifacts`; extend selector; `run()` untouched (S08-D7) | ☐ | — |
| **4.6** | `viz/gif.py` (NEW) — `make_gif()` PNG-frame pipeline-progression stitch (pillow); `pyproject` += pillow | ☐ | — |
| **4.7** | Tests — structural SVG + gif smoke + palette completeness + debug-run artifact emission (S08-D5) | ☐ | — |
| **4.8** | Close — README + Progress + Pipeline synced to **v1 ships**; S08-D finalize; ruff + pytest green; `--no-ff` merge | ☐ | — |

---

## 2. Definition of Done checklist (Plan §1)

- ☐ 1. Canonical SVG renderer (`viz/svg.py`) — layered `<g>`, empty-group contract, meters + Y-flip + viewBox + pad + scale
- ☐ 2. Layer stack re-derived from our pipeline (~12, no proto3 dead layers) — finalized at 4.2
- ✅ 3. Single palette source (`viz/palette.py`); `final.py` reads it (duplicate table removed) — `73d6c19` / `1ccc563`
- ☐ 4. `make_gif()` — pipeline-progression GIF from matplotlib PNG frames (pillow)
- ☐ 5. `RunConfig.debug_artifacts` opt-in wiring (`SvgRunWriter`); `run()` unchanged
- ☐ 6. Tests structural (layer order/counts/classes, role-fill, grid), not byte-golden; gif smoke
- ☐ 7. `pyproject` viz extra += `pillow`; no cairosvg / SVG-raster dep
- ✅ 8. Step 07 docs archived → `legacy/step07/` (H011); Progress Tracker Step 08 opened (`29eb39a`)
- ☐ 9. ruff (check + format) + full pytest green; docs synced to "v1 ships"; merged `--no-ff`

---

## 3. Notes / decisions during execution

(Filled as work items land — drifts, surprises, sub-decisions S08-D8+.)

- **4.2 — layer order locked as the Plan §2 indicative 12** (no change):
  `grid, footprint, atoms, regions, region-graph, anchors, seeds, grown,
  corridor, rooms, labels, failure`. The S08-D2 list survived contact with the
  palette consumer, so it stands without an S08-D8 revision. `role_color()` is
  **tolerant** (fallback, never raise) — a renderer is a post-`run()` consumer
  and must not crash a debug view (contrast proto3's raising
  `role_to_palette_key`, a pre-validation tool). `PART_COLORS` deliberately
  stays in `_helpers` (matplotlib-debug-only, not canonical role/layer vocab).
