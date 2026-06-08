# 007 Step 07 — Entry Point + Labeling Plan

Status: Completed — **merged to `main`** (`68e8df2`, `--no-ff`, 2026-06-03) after external + adversarial review response (`0c03b69`)
Type: Step plan
Branch: `step07-entrypoint` (D005 — triggers fired: **integration** [joins the
03/04 geometry half + 05/06 program half] + **regression risk** [first `run()`
driven over the 33 geometry goldens; a polygonization/labeling bug could
surface as golden drift]. Step 04 + Step 05, the analogous integration Steps,
both branched; only the small Step 06 stayed on `main`.)
Last updated: 2026-06-03

---

## 0. Purpose

Step 07 is **the join**. It assembles the public entry point (D001):

```python
def run(shape: ShapeInput, program: ProgramRequest, *, seed: int) -> LabeledRoomLayout
```

wiring the **geometry half** (Step 03/04: atomize → atom_graph → regionize →
region_graph → growth → corridor) to the **program half** (Step 05/06:
admission gates + `expand_program`), then adds the **labeling** stage
(Pipeline §3.8) and the cluster the earlier Steps deferred here.

The key framing — Step 07 is **not mere wiring**. Step 04 deliberately
stopped at a region-based `CorridoredLayout` (S04-D2): its `rooms` carry
`GrownRoom.region_ids` (region-id *sets*), **not polygons**. So the
substantive NEW work beyond the wire-up is:

1. **Polygonization** (S04-D2 deferred): region-id sets → room / corridor
   `shapely.Polygon`s.
2. **Labeling** (§3.8): recover the authoritative 7-class `role` / `usage`
   and compute `area_m2`.
3. **The deferred cluster** (Progress Tracker §5.1): `vertical_circulation`
   anchor fixed-room re-insertion, the per-room post-growth area/dim check,
   the `check_multi_floor_feasibility` call site, and the
   `valid=False ⇒ non-empty failure_records` invariant.

After Step 07, v1's functional core is complete (`run()` end-to-end on
single-floor apartments). Step 08 (canonical SVG viz) is the last v1 Step.

Cross-references:

- `docs/000_Pipeline_Overview.md` §2 (contract types), §3.6–3.8 (growth /
  corridor / labeling stages), §5.1 (Step 07 DoD).
- `docs/000_Architecture_Decisions.md`:
  - **D001** — pure-function `run()` contract; per-floor outer loop.
  - **D004** — 7-class `Role`; `vertical_circulation` anchor binding.
  - **D006** — output directory convention; `on_stage` hook + `StageOutput`
    + `manifest.json` land **here** (Step 07), canonical render at Step 08.
  - **proto3:D018** — unified `LabeledRoomLayout(valid=…)`; `valid=False`
    ⇒ non-empty `failure_records`.
  - **proto3:D023** — required-only area/cardinality summation.
- `legacy/step04/004_Step04_AlgorithmCore_Plan.md` — S04-D2 (terminal
  `CorridoredLayout`, polygonization deferred here), S04-D3 (growth is
  target-agnostic), S04-D4 (anchor fixed-room re-insertion deferred here).
- `legacy/step05/005_Step05_ProgramLayer_Plan.md` — S05-D6 (multi-floor
  feasibility hoisted to building-level / Step 07).

---

## 1. Definition of Done

```text
Step 07 closes when:

1. run(shape, program, *, seed) -> LabeledRoomLayout assembled (D001). Pure
   function, per-floor outer loop. on_stage callback hook threaded
   (default None = pure, no I/O — S02-D11 / D006).

2. Polygonization (S04-D2 deferred): CorridoredLayout region-id sets →
   LabeledRoom.polygon + LabeledFloorLayout.corridor_polygons, via
   unary_union of the constituent region polygons. Disconnected-union
   (MultiPolygon) handling decided at the work item (4.2 / S07-D5).

3. Labeling stage (Pipeline §3.8): each grown room → LabeledRoom — the
   authoritative 7-class role/usage recovered via GrownRoom.name ==
   SpaceUnitSpec.id (growth collapsed roles to Cell's 4-class), area_m2
   computed, usage carried through untouched (never guessed — S06-D3).

4. vc anchor re-insertion (S04-D4): vertical_circulation rooms get their
   polygon from the linked VerticalAnchor.footprint_polygon, emitted as a
   fixed LabeledRoom with anchor_id. Growth already excludes them
   (program_adapter _EXCLUDED_INPUT_ROLES).

5. Per-room post-growth area/dim check: a grown room below its OWN
   area_min_m2 / min_dimension_m is rejected (the "1.5 m² room") — distinct
   from Step 05's AGGREGATE admission. Emits a FailureRecord.

6. Failure path: valid=False ⇒ non-empty failure_records, upheld by run()
   (proto3:D018, not constructor-enforced — output.py docstring).
   check_multi_floor_feasibility gets its call site (S05-D6, building-level).

7. Trace infra (D006): StageOutput dataclass + on_stage hook + JSON
   serializer + manifest.json writer + outputs/debug_runs/<run_id>/ layout
   (+ minimal RunConfig for the manifest config field). Canonical SVG
   renderer + make_gif() deferred to Step 08 (S07-D3).

8. Viz (S01-D10): a final LabeledRoomLayout matplotlib dev-bridge renderer
   (polygonized rooms role-colored + usage labels + corridor polygons + vc
   anchors). + viz/__init__.py off-by-one doc fix (it says "Step 07 (SVG
   visualization)"; canonical SVG is Step 08).

9. Test corpus BOTH (S07-D2):
   (A) the 33 Cell cases driven through run() -> golden LabeledRoomLayout
       (program synthesized per case from its growth_fixture);
   (B) realistic apartment fixtures (shape + ProgramRequest) + their goldens
       + failure-injection (infeasible program -> valid=False with the right
       FailureRecord codes).

10. xfail: the 2 Step-07-targeted PoCs reviewed — corridor single-component
    (case_33 bridge-carve) + K>seedable-regions graceful failure. The other
    3 (B5/B6/C10 latent geometry) stay xfail (no 33-case trigger).

11. ruff (BOTH check AND format) + full pytest green (conda IfcOpenHouse,
    GEOS 3.14.1); Plan/Tracker closed; S07-D series finalized; merged
    --no-ff to main.
```

---

## 2. 결정 기록

Decisions locked during Step 07 planning (chat discussion 2026-06-02).
Predecessor decisions referenced as `S0N-Dxx` / `proto3:Dxxx`.

| # | Topic | Decision |
|---|---|---|
| **S07-D1** | Branch | Work on `step07-entrypoint`, merge `--no-ff` at close. D005 triggers fired: **integration** (joins four module areas — geometry 03/04 + program 05/06) and **regression risk** (the first `run()` over the 33 geometry goldens — a polygonization/labeling defect can show as golden drift; a branch makes rollback a delete). Step 04 and Step 05 (the analogous joins) both branched; Step 06 (small, mostly-new-files) stayed on `main`. |
| **S07-D2** | Test corpus = **both** | (A) Extend the existing 33-case golden harness *through* `run()` to a golden `LabeledRoomLayout` per case — regression continuity on top of the layout/seed/corridor digests, deterministic (region assignments are already pinned); the per-case program is synthesized from its `growth_fixture` RoomSpec set. (B) Author a small set of realistic apartment fixtures (`ShapeInput` + `ProgramRequest`) + goldens + failure-injection — the DoD's "valid apartment" intent + the failure path. Rationale for both: (A) alone is geometry stress-shapes with synthetic programs (no "is this a sane apartment?" signal); (B) alone lacks the 33-case regression web. The Pipeline §5.1 DoD line "6 apartment fixtures" predates the 33-case corpus — reconciled here as (A)+(B), not (B)-only. |
| **S07-D3** | Trace seam: Step 07 vs Step 08 | `on_stage` hook + `StageOutput` + JSON serializer + `manifest.json` writer land in **Step 07** (D006 as written). The hook is **invasive** — it threads every stage call site inside `run()`, so it MUST land *with* `run()`; retrofitting later re-touches every stage (same "land the ripple once" logic D004 used for `vertical_circulation`). Default `on_stage=None` keeps `run()` pure. The canonical SVG renderer + `make_gif()` are a pure `StageOutput` *consumer* (addable anytime) → **Step 08** (the viz Step). Note: the trace infra is *orthogonal* to the functional DoD (goldens compare `run()`'s return value, not disk artifacts) — so within the Step it is lower-priority than 4.2–4.6, but the hook seam is designed into `run()` from 4.6. |
| **S07-D4** | Viz seam | A final `LabeledRoomLayout` **matplotlib dev-bridge** renderer lands in **Step 07** (S01-D10 "viz at every Step"). The existing six stage renderers (`input`/`atomize`/`regionize`/`seed`/`layout`/`corridor`) cover the geometry pipeline up through the region-based `CorridoredLayout`; the **polygonized + labeled** final layout has no renderer yet. The canonical 12-layer SVG path is **Step 08**. + the `viz/__init__.py` off-by-one doc bug ("Step 07 (SVG visualization)" → Step 08) is fixed at kickoff. |
| **S07-D5** | Polygonization disconnected-union policy | Decided during 4.2 from a probe over the 33 goldens: **0/137 rooms** produce a disconnected region union (growth absorbs only *adjacent* regions). A room's union is therefore expected to be a single `Polygon` — `polygonize_room` raises `GeometryFailure` (`ROOM_DISCONNECTED` / `ROOM_EMPTY`) on violation rather than silently taking the largest piece (honest-fix; `run()` catches → `valid=False`); no speculative repair logic. Corridors differ: the carved set is legitimately multi-component (**4/33** — case_04/10/32/33) and `corridor_polygons` is plural, so `polygonize_corridors` returns one `Polygon` per component. A new third sibling exception family `GeometryFailure` carries the `FailureRecord`. |
| **S07-D6** | Where `run()` gets `TargetRules` | The D001 signature `run(shape, program, *, seed)` carries no rules, but the admission gates need `TargetRules` (density / cardinality / single-floor). `run()` resolves them **from `program.target_type`** via a `{typology: rules_path}` registry + `load_target_rules`. v1 ships apartment only, so a non-apartment `target_type` (a valid Literal with no JSON yet) returns `valid=False` with a `NO_TARGET_RULES` record (graceful — never raise out, ③). The registry generalises when non-apartment rules are authored (S06-D5). Also (impl notes): `StageOutput` + the `on_stage` hook land in 4.6 (with `run()`), not 4.7 — the hook is invasive (S07-D3); a polygonize `GeometryFailure` yields an empty floor (no partial-room recovery — 0/137, honest-fix). |

Decisions expected to emerge *during* build (recorded as **S07-D7+** when they
land): how/whether `expand_program` binds a `vertical_circulation` anchor; the
`RunConfig` field set; the exact module split (one `labeling.py` vs a small
package).

---

## 3. Directory structure (indicative target state)

```text
src/room_layout/
  __init__.py          # MODIFIED: export run()
  run.py               # NEW: run(shape, program, *, seed, on_stage=None) — the join (D001)
  schema/
    run_config.py      # NEW (minimal): RunConfig (D006 manifest `config`)
    trace.py           # NEW: StageOutput dataclass (D006)
  stages/
    polygonize.py      # NEW: CorridoredLayout region-sets → polygons (S04-D2, 4.2)
    labeling.py        # NEW: GrownRoom → LabeledRoom (§3.8) + per-room gate
                       #      + vc anchor re-insertion (4.3/4.4/4.5; split TBD)
  trace/               # NEW: JSON serializer + manifest writer + debug_runs writer (4.7)
    __init__.py
  viz/
    __init__.py        # MODIFIED: off-by-one doc fix (S07-D4)
    stages/
      final.py         # NEW: final LabeledRoomLayout renderer (S07-D4) — name TBD

tests/
  test_run.py                    # NEW: run() end-to-end (corpus A + B)
  test_polygonize.py             # NEW
  test_labeling.py               # NEW
  test_trace.py                  # NEW
  fixtures/apartment_*.json      # NEW: realistic apartment fixtures (corpus B)
  golden/<case>/run.json         # NEW: golden LabeledRoomLayout per 33 case (corpus A)
```

Module split (polygonize / labeling separate vs combined, `trace/` package vs
module) is finalized at the work items; the layout above is indicative.

---

## 4. Work items

Bottom-up (dependency order): build the standalone pieces (polygonize →
label → anchor/gate) first, assemble `run()`, then trace / viz / tests.
Each item is one commit (proto3:D015). Mirrors into Tracker §1 (proto3:D016).

| # | Work item | Verify |
|---|---|---|
| **4.1** | Kickoff — Plan + Tracker land + `git mv` Step 06 docs → `legacy/step06/` + `viz/__init__.py` off-by-one doc fix (S07-D4) + Progress Tracker (Step 07 opened) | docs review; tree staged |
| **4.2** | `stages/polygonize.py` (NEW) — `CorridoredLayout` region-id sets → room `Polygon` + `corridor_polygons` (`unary_union`); MultiPolygon/hole policy (S07-D5) | area-conservation test vs region-set areas |
| **4.3** | Labeling (§3.8) — grown room → `LabeledRoom`: 7-class role/usage recovery (`name == id`), `area_m2`; assemble `LabeledFloorLayout` | labeling unit tests; role/usage round-trip |
| **4.4** | vc anchor re-insertion (S04-D4) — `vertical_circulation` polygon = `VerticalAnchor.footprint_polygon`; fixed `LabeledRoom` + `anchor_id` | synthetic-anchor fixture test |
| **4.5** | Per-room post-growth gate — reject a room below its own `area_min`/`min_dim` (1.5 m²); emit `FailureRecord` | rejection test; distinct from Step 05 aggregate |
| **4.6** | `run.py` (NEW) — the `run()` join (D001): per-floor loop, geometry + program + 4.2–4.5; `on_stage` hook threaded; `valid=False ⇒ failure_records` (proto3:D018); `check_multi_floor_feasibility` call site (S05-D6) | `run()` returns a valid `LabeledRoomLayout` on a fixture |
| **4.7** | Trace infra (D006) — `StageOutput` + JSON serializer + `manifest.json` writer + `outputs/debug_runs/<run_id>/` + minimal `RunConfig` | a debug run writes `NN_<stage>.json` + manifest |
| **4.8** | Final-layout renderer (S01-D10) — matplotlib: polygon rooms role-colored + usage labels + corridor polygons + vc anchors | renders a fixture to PNG |
| **4.9** | Test corpus A — 33 cases through `run()` → golden `LabeledRoomLayout` (program synthesized from each `growth_fixture`) | 33 run-goldens green |
| **4.10** | Test corpus B — realistic apartment fixtures + goldens + failure-injection (infeasible → `valid=False` + codes) | apartment run-goldens + failure codes |
| **4.11** | xfail resolution — corridor single-component (case_33 bridge-carve) + K>seedable graceful failure; the other 3 (B5/B6/C10) stay latent | xfails flipped or re-justified |
| **4.12** | Close — README Status + Tracker + Progress Tracker sync + S07-D series finalize + `--no-ff` merge to `main` | CI green; merged |

---

## 5. 의도적으로 하지 않는 것 (out of scope)

| Item | Why / where |
|---|---|
| Canonical 12-layer SVG renderer + `make_gif()` | **Step 08** (S07-D3/D4). Step 07 ships only the matplotlib dev-bridge final renderer + the `StageOutput`/JSON trace it consumes. |
| Multi-floor orchestration (cross-floor anchor alignment, per-floor program allocation, cross-floor validation) | **Step 10** (D001). `run()` processes one floor at a time; `check_multi_floor_feasibility` gets only its **call site** here, not the orchestrator. |
| ResearchBIM adapter (`Building`/`Storey` mutation) | **Step 09**. |
| Door positions on room↔corridor boundaries | Deferred — `LabeledRoom.doors` stays `None` in v1 (Pipeline §2.4); corridor carving does not yet emit door positions. |
| The 3 latent geometry xfails (B5 atom loss / B6 disconnected-union / C10 3-way overlap) | Fixed when a real input triggers them (Step 07+); none is hit by the 33 goldens. |
| role↔usage auto-mapping | Not built (S06-D3). `usage` is carried through from `SpaceUnitSpec`, never guessed from `role`. |
| Area-aware growth (consuming `area_target_m2`) | No consumer (S04-D3 / S06-D2); growth stays target-agnostic. Step 07 reads only `area_min`/`min_dim` (per-room gate). |
| Wall-thickness clear-area inset (centerline → inner-face room polygons) | v1 contract is **centerline** (Pipeline §2.4, ResearchBIM-aligned), wall thickness ignored. A *separable post-transform* on the output (uniform → inward `buffer(-t/2)`; per-wall → wall-graph subtraction), or a downstream IFC concern (`IfcWall` thickness → derived `IfcSpace`) — never ripples into growth/regionize/labeling (all centerline). See Progress Tracker §5.2. |

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| Polygonization yields a **MultiPolygon** (disconnected room) — `LabeledRoom.polygon` is singular | Decide at 4.2 (S07-D5): largest-piece + `FailureRecord`, or a repair. Related to the B6 xfail. Not triggered by the 33 goldens (grown rooms are region-connected), but a hand-authored apartment program could hit it. |
| `run()` over the 33 cases drifts the existing goldens (the D005 regression trigger) | The branch isolates it. The layout/seed/corridor digests already pin the geometry half; only the NEW polygonize/label layer is unproven, and its golden is added fresh (no prior contract to break). Area conservation (4.2) catches silent geometry loss. |
| `on_stage` hook retrofit cost if deferred | Threaded into `run()` from 4.6 (S07-D3); `default None` keeps the core pure. Not deferred. |
| Corpus-A program synthesis — the 33 cases carry no natural `ProgramRequest` | Derive each program from its `growth_fixture` RoomSpec set (the inverse of `program_adapter`); document the synthesis in 4.9. The 33 are a **geometry** regression web, not "realistic apartments" — that signal is corpus B's job (4.10). |
| `expand_program` can't produce a `vertical_circulation` room (needs `anchor_id`, which `{role:count}` can't carry) | apartment.json requires no vc → moot today (Progress Tracker §5.1). 4.4 decides anchor binding if a vc-requiring fixture is authored; corridor's analogous trap is already blocked (S06-D6). |

---

## 7. Next-Step linkage

Step 07 completes v1's **functional core**: `run()` produces a valid
`LabeledRoomLayout` end-to-end on single-floor apartments, with the failure
path and the anchor / per-room / connectivity cluster resolved.

**Step 08** (SVG visualization) is the final v1 Step — the canonical 12-layer
SVG renderer + `make_gif()`, consuming the `StageOutput` trace this Step
lands (D006). After Step 08, **v1 ships**. Steps 09 (ResearchBIM adapter) and
10 (multi-floor orchestrator) are post-v1 and independent (Pipeline §5.2).
