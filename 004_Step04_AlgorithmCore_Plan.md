# 004 Step 04 — Algorithm Core Port Plan

Status: Active
Type: Step plan
Branch: `step04-algorithmcore` (D005 — regression risk + integration work:
new schema/anchor wiring touches the growth + carve half of the pipeline)
Last updated: 2026-05-29

---

## 0. Purpose

Step 04 lands the **growth-and-carving half** of the pipeline (Cell
**Phase 6–8**) plus `shape_gate` into `src/room_layout/stages/`, reusing
the Step 03 geometry outputs (`Region` / `AtomGraph` / `RegionGraph` /
`atoms`) as the growth substrate.

Guiding split (S04-D1): the **algorithm follows Cell faithfully**
(`archive/celllayout/` Phase 6–8), while the **interface follows the new
schema** (D001 `ProgramRequest` / `VerticalAnchor`, D004 7-class `Role`).
The gap between Cell's growth inputs and the new schema is bridged by a
small **program adapter** (S04-D3); Cell's growth/carve logic is ported
unchanged.

The pipeline's only genuinely new behavior versus Cell is **vertical
anchors** (S04-D4) — Cell's Phase 1–8 has no anchor concept. Anchors are
handled by a footprint **donut-hole** preprocessing step so the ported
geometry/growth stages stay anchor-blind.

The final `corridor` stage emits a `CorridoredLayout`-equivalent
(per-room region sets + corridor region sets + diagnostics). The
`LabeledRoomLayout` wrapping (polygonization, final role/usage,
`area_m2`, domain gates) belongs to **Step 07** (S04-D2).

After Step 04 closes:

- `from room_layout.stages import seed_placement, growth, carve_corridors,
  shape_gate` works.
- A `FloorShape` + `floor_programs[level]` (+ `vertical_anchors`) can be
  carried through seed placement → partition growth → corridor carving;
  intermediate outputs are typed Python dataclasses.
- Per-stage dev-bridge renderers (seed / layout / corridor) extend the
  Step 03 viz infrastructure.
- The Step 03 golden infrastructure carries through; only the stage list
  grows — region-id digest goldens for seed / layout / corridor on the
  same 33 Cell cases, plus new anchor fixtures.

Cross-references:

- `docs/000_Pipeline_Overview.md` §3 — per-stage operational view (this
  Step implements §3.6 region partition growth + §3.7 corridor carving).
- `docs/000_Architecture_Decisions.md`:
  - **D001** — external contract (`run()` join is Step 07; this Step
    stops at the pre-label growth/carve result).
  - **D002** — seed-first vs spine-first growth (the rationale this Step
    implements).
  - **D004** — 7-class `Role` + anchor binding (`vertical_circulation`
    anchor-locked rooms; `host_role=None` forbidden shafts).
  - **D005** — solo-mode workflow (justifies branching).
  - **D006** — output directory convention (`outputs/step04/` for
    dev-bridge PNG demo runs).
- `legacy/step03/003_Step03_GeometryPipeline_Plan.md` §7 — Step 04
  linkage (this Plan's origin).

---

## 1. Definition of Done

- `from room_layout.stages import seed_placement, growth, carve_corridors,
  shape_gate` imports cleanly.
- 33 Cell showcase cases reproduce **semantically equivalent** seed /
  layout / corridor outputs against region-id digest goldens (S04-D5),
  driven by the Step 03 golden infrastructure (`tests/_golden.py` +
  `tests/golden/<case>/`).
- The program adapter (S04-D3) maps `ProgramRequest.floor_programs[level]`
  (7-class `Role`) onto Cell's growth fixture; growth stays
  target-agnostic.
- Anchor handling (S04-D4): ≥1 new anchor fixture exercises the
  donut-hole preprocessing + `vertical_circulation` fixed-room
  re-insertion + `host_role=None` forbidden-only path.
- Dev-bridge viz: `viz/stages/seed.py` / `layout.py` / `corridor.py`
  render any case × stage into `outputs/step04/`.
- `ruff check .` + `ruff format --check .` clean; full `pytest` green
  under the canonical runtime (conda `IfcOpenHouse`, GEOS 3.14.1).
- `docs/000_Progress_Tracker.md` updated (Step 04 closed; Step 05
  kickoff); this Plan + Tracker `git mv`-d to `legacy/step04/` at the
  Step 05 §4.1 commit (proto3:D016 H011 deferred-archive pattern).

---

## 2. 결정 기록

Decisions locked during Step 04 planning (chat discussion 2026-05-29).
Predecessor decisions referenced as `S03-Dxx` / `proto3:Dxxx`.

| # | Topic | Decision |
|---|---|---|
| **S04-D1** | Scope & principle | Port Cell **Phase 6–8** (`seed_placement` / `growth_seed` / `growth_cells` / `growth_partition` / `growth_absorb` / `room_growth` / `corridor` + `corridor_*` ×5) + `shape_gate` (the reflex helper `growth_absorb` consumes, deferred from S03-D16). **Algorithm follows Cell faithfully; interface follows the new schema.** The two meet at a thin adapter (S04-D3), not by rewriting Cell's growth logic. |
| **S04-D2** | Step 04 ↔ Step 07 boundary | Step 04 stops at a `CorridoredLayout`-equivalent: per-room **region sets** + corridor region sets (base / shortcut / leftover) + diagnostics. Polygonization (region union → room polygon), final `Role` / `usage`, `area_m2`, `corridor_polygons`, and the `proto3:D020` domain gates are **Step 07** (Pipeline §3.8 labeling). Rationale: Cell's Phase 8 output (`CorridoredLayout`) is region-id based — it produces no per-room polygons and runs no gates — so the natural cut matches §3.8. (`legacy/step03` Plan §7's "corridor emits `LabeledRoomLayout`" was loose phrasing.) |
| **S04-D3** | Program adapter & target-agnostic growth | A `(FloorShape, floor_programs[level], vertical_anchors) → Cell growth fixture` adapter bridges the schemas. **Growth stays target-agnostic** (faithful Cell port): `area_target_m2` / `area_min_m2` / `min_dimension_m` are **not** consumed during growth — they feed the Step 07 gates only. Role mapping: `hub` role → Cell `public` placed first (Cell's hub = first `public` room, `hub_room_index`); `corridor` is never an input role (carving produces it; rejected by `SpaceUnitSpec.__post_init__`); `vertical_circulation` is not grown (S04-D4 — excluded from the fixture). Cell needs per-role **aspect ranges** as a hard gate (W12) but the new schema has no aspect concept → port Cell's per-role aspect-range **defaults as a constant table** (`DEFAULT_ROLE_ASPECT_RANGES` uniform `(1.0, 4.0)`; `DEFAULT_ROLE_MIN_AREAS` `{public:8, private:4, wet:2, service:3}`). A `target_rules` override is a Step 06 concern (no forward dependency). **Identity preservation**: the adapter sets `RoomSpec.name = SpaceUnitSpec.id`, so `GrownRoom` carries the program identity back — Step 07 recovers the authoritative 7-class `role` / `usage` from the id (Cell's `GrownRoom.role` is the collapsed 4-class label, not the output source of truth). |
| **S04-D4** | Anchors = footprint donut-hole | Anchors are pre-placed input (`VerticalAnchor.footprint_polygon`, "identical XY across `floor_range`") — v1 does **not** place them (D001 defers cross-floor alignment to Step 10; v1 is single-floor). A **preprocessing step subtracts anchor footprints from the `FloorShape`** (holes), then feeds the *unchanged* Step 03 stages — the geometry/growth pipeline stays anchor-blind (`ShapePart.holes` is already a first-class concept). Post-growth: `host_role="vertical_circulation"` (stair/elevator) → re-insert a **fixed room** (polygon = footprint, `anchor_id`-bound, role `vertical_circulation`); `host_role=None` (ps/eps/duct shaft) → **forbidden hole only, no room** (D004). **Access guarantee deferred** — a donut-hole can geometrically isolate the fixed room; corridor connectivity to anchor rooms is a documented v1 limitation, not built this Step. Chosen over a "forbidden tag threaded through seed/growth/carve" because the hole approach touches Cell's logic zero times. **Implementation note**: `difference(part, anchor)` is a clean interior hole only when the anchor sits strictly inside a part; a boundary-touching anchor produces a notch (exterior change) and a spanning anchor splits the part (MultiPolygon → multiple `ShapePart`s). The preprocessing handles the generic difference result; v1 validates the clean interior-hole case first (atomize hole-exclusion already covered by `test_atomize_hole_is_excluded`) and defers pathological anchor geometries. |
| **S04-D5** | Golden granularity | Region-id **digest** goldens (mirrors S03-D14): seed = phase → region_ids; layout = per-room region_id tuple + area; corridor = base / shortcut / leftover region_id sets + final room region_ids. Polygon-level golden is deferred to Step 07. Rationale: region-id digests are GEOS-stable (avoids the regionize GEOS 3.13/3.14 split that forced the CI pin) and capture the algorithm's decisions directly. **New anchor fixture(s) required** — the 33 Cell cases have zero anchors, so anchor wiring cannot be regression-covered by them. |
| **S04-D6** | Module layout | **Flat `stages/`** — all Phase 6–8 modules at the package root, no sub-packages. S03-D2 deferred the flat-vs-nested call to Step 04 ("revisit if the count passes ~10"); revisited here. Flat wins because (1) Cell's `celllayout_tf/` is flat → faithful port + minimal import rewrite, (2) zero churn on the already-shipped Step 03 modules, (3) the `growth_*` / `corridor_*` prefixes give visual grouping. Nesting stays an option for a post-Step-04 cleanup if the directory becomes unwieldy. |
| **S04-D7** | Seed-mode coverage | The 33 Cell fixtures **all carry explicit `seed_position`** (manual placement); the new-schema `SpaceUnitSpec` has none, so `run()` **always uses auto-placement** (`auto_place_seeds_by_cells`). Strategy **(a1)**: the 33-case goldens port Cell's manual seeds verbatim → exact Cell-match regression for growth / absorb / corridor. Auto-placement is covered **separately** — port Cell's seed-placement unit tests **plus** a small set of auto-driven golden cases with freshly-reviewed outputs (work items 4.9 / 4.12). Rationale: manual-seed goldens validate the *algorithm* faithfully, but the production path is *auto* — it must not be left golden-uncovered (caught in re-review 2026-05-29). |
| **S04-D8** | Growth consumes Step 03 outputs | Cell's `region_partition_growth` **recomputes** `atomize` / `regionize` / `build_region_graph` internally. The port instead **takes `atoms` / `regions` / `region_graph` as parameters** (computed once by the golden driver / Step 07 `run()`). Deliberate signature deviation from Cell — avoids double computation and realizes Plan §0's "reuse Step 03 outputs as substrate" (caught in re-review 2026-05-29). |

---

## 3. Directory structure (target state after Step 04)

Flat `stages/` per S04-D6. Step 04 adds 15 modules (13 Cell Phase 6–8
ports + 2 new-to-this-repo bridges) alongside the 7 Step 03 modules.

```text
src/room_layout/
  stages/
    # --- Step 03 (Phase 3–5, already landed) ---
    _helpers.py
    dimensions.py
    territory.py
    atomize.py
    atom_graph.py
    regionize.py
    region_graph.py
    # --- Step 04: Phase 6 (seed) ---
    seed_placement.py      # SeedPlacement + centrality / BFS helpers
    # --- Step 04: Phase 7 (growth) ---
    growth_seed.py         # cell-aware seed placement (hub / coverage / fps)
    growth_cells.py        # vertex cells + guillotine partition
    growth_partition.py    # entry: region_partition_growth → GrowthResult (takes atoms/regions/rg params, S04-D8)
    growth_absorb.py       # 3-stage leftover absorption (shape_gate consumer)
    room_growth.py         # result types: GrownRoom / GrowthResult
    shape_gate.py          # reflex helper (count_reflex_vertices) — S03-D16
    # --- Step 04: Phase 8 (corridor) ---
    corridor.py            # entry: carve_corridors → CorridoredLayout
    corridor_index.py      # region index + connectivity
    corridor_params.py     # tunables
    corridor_path.py       # A* path
    corridor_stage1.py     # hub-radial base corridor
    corridor_stage2.py     # detour shortcut
    # --- Step 04: new to this repo ---
    anchors.py             # S04-D4 donut-hole subtraction + fixed-room re-insertion
    program_adapter.py     # S04-D3 floor_programs[level] → Cell growth fixture
  viz/stages/
    # Step 03: input.py, atomize.py, regionize.py (+ region-graph overlay)
    seed.py                # NEW — seed placement markers
    layout.py              # NEW — grown rooms
    corridor.py            # NEW — corridor overlay
tests/
  golden/<case>/           # 33 Cell cases — Step 03 stage files + NEW:
    seed.json              #   digest: phase → region_ids (S04-D5)
    layout.json            #   digest: per-room region_ids + area
    corridor.json          #   digest: base / shortcut / leftover + room region_ids
  golden/anchor_*/         # NEW synthetic anchor fixtures (S04-D5)
  test_stages_seed_placement.py / _growth_* / _corridor* / _shape_gate.py
  test_stages_anchors.py / _program_adapter.py
outputs/step04/            # dev-bridge PNG demo runs (D006)
```

Notes:

- `room_growth.py` ports the result types (`GrownRoom` / `GrowthResult`)
  **and** Cell's internal growth contract (`LayoutFixture` / `RoomSpec`).
  `program_adapter.py` *builds* `LayoutFixture` from the new schema
  (S04-D3); the 33-case goldens build it from ported Cell fixture data
  (S04-D7). Growth consumes `LayoutFixture` unchanged.
- `corridor.py`'s `CorridoredLayout` is Step 04's terminal output
  (S04-D2); no `LabeledRoomLayout` here.
- Anchor fixtures live as their own golden case dirs (`anchor_*`) since
  the 33 Cell cases carry none.

---

## 4. Work items

Leaf-first port order (dependency-driven). Cross-cutting: every Phase 6–8
module that took Cell's `ShapeInput` switches to `FloorShape` (S03-D13);
this rename happens within each module's port, not as a separate item.
Mirrors into Tracker §1 (proto3:D016).

| # | Work item | Verify |
|---|---|---|
| **4.1** | Plan + Tracker land + `git mv` Step 03 docs → `legacy/step03/` + §5 Step-map renumber (+1 shift) | docs review; working tree staged |
| **4.2** | ~~Scaffold — `stages/` / `viz/stages/` stubs + `_golden.py` digest comparators~~ **RETIRED** — Step 03 already ships the dirs + golden infra, and `assert_golden` is **generic** (handles digest dicts, not just full geometry). The per-stage digest *builders* (seed / layout / corridor) live in the test driver and need their stages to exist → added with 4.11 / 4.13. No empty stubs (numbering preserved, cf. S03-D16's 4.11). | n/a |
| **4.3** | `shape_gate.py` (`count_reflex_vertices` / `_reflex_of_union`) + unit tests — leaf, no deps (S03-D16) | unit tests pass |
| **4.4** | `anchors.py` ① donut-hole preprocessing (`FloorShape` − anchor footprints → holed `FloorShape`; generic `difference`, S04-D4) + 1 new anchor fixture; **validate regions via existing Step 03 `atomize`/`regionize` + viz eyeball** (S04-D4/D5 validate-early) | anchor fixture → sane atoms/regions; PNG review |
| **4.5** | `seed_placement.py` (`SeedPlacement` + centrality / BFS helpers) + unit tests | unit tests pass |
| **4.6** | `room_growth.py` — `GrownRoom` / `GrowthResult` + `LayoutFixture` / `RoomSpec` (Cell-internal contract, S04-D7) + port Cell `DEFAULT_ROLE_MIN_AREAS` / `DEFAULT_ROLE_ASPECT_RANGES` constants (S04-D3) | unit tests pass |
| **4.7** | Port Cell `layout_fixtures.py` 33-case programs (manual seeds + role tables, S04-D7 a1) into `tests/golden/<case>/` fixture data | 33 fixtures build; round-trip |
| **4.8** | `growth_cells.py` (vertex cells + guillotine partition) + unit tests | unit tests pass |
| **4.9** | `growth_seed.py` (`auto_place_seeds_by_cells` — hub / coverage / fps) + unit tests **(port Cell seed-placement tests — auto coverage, S04-D7)** | unit tests pass |
| **4.10** | `growth_absorb.py` (3-stage leftover absorption; `shape_gate` consumer) + unit tests | unit tests pass |
| **4.11** | `growth_partition.py` (`region_partition_growth`, takes atoms/regions/rg params per S04-D8) + `viz/stages/seed.py` + `viz/stages/layout.py` + 33-case `seed.json` + `layout.json` digest goldens (manual seeds) + **manual review** | 33-case goldens match Cell; review checkpoint |
| **4.12** | Auto-placement golden coverage — small set of auto-driven cases (no manual seeds) with freshly-reviewed `seed` / `layout` goldens (S04-D7) | new goldens reviewed + stable |
| **4.13** | corridor stack — `corridor_params` / `corridor_index` / `corridor_path` / `corridor_stage1` / `corridor_stage2` + `corridor.py` (`carve_corridors` → `CorridoredLayout`) + `viz/stages/corridor.py` + 33-case `corridor.json` digest golden + **manual review** | 33-case goldens match Cell; review checkpoint |
| **4.14** | `program_adapter.py` (S04-D3) — `(FloorShape, floor_programs[level], vertical_anchors) → LayoutFixture`; `hub`→`public`-first, `vertical_circulation` excluded, `RoomSpec.name = SpaceUnitSpec.id`; aspect-default table + unit tests | adapter unit tests pass |
| **4.15** | `anchors.py` ② `vertical_circulation` fixed-room re-insertion (post-growth: polygon = footprint, `anchor_id`-bound) + `host_role=None` forbidden-only; **anchor fixture through full pipeline** (adapter → growth → carve → fixed-room) + tests (access guarantee deferred, S04-D4) | anchor full-pipeline test passes |
| **4.16** | Demo CLI extension — seed / layout / corridor renderers into `outputs/step04/` (D006) | CLI renders each case × stage |
| **4.17** | Step close — update `docs/000_Progress_Tracker.md` (Step 04 closed; Step 05 kickoff) + `git merge --no-ff step04-algorithmcore` → `main` | CI green; tracker updated |

Manual-review checkpoints (4.11 / 4.13) mirror Step 03's per-stage
golden review (S03-D9): a human eyeballs the digest + PNG sidecars for a
sample of the 33 cases before the golden is frozen.

---

## 5. 의도적으로 하지 않는 것

- **Polygonization + labeling** (region union → room polygon, final
  `Role` / `usage`, `area_m2`, `corridor_polygons` as `Polygon`,
  `LabeledFloorLayout` / `LabeledRoomLayout` assembly) → **Step 07**
  (S04-D2). Step 04 ends at region-set rooms + corridor region sets.
- **`run()` entry point + per-floor outer loop + `on_stage` callback** →
  **Step 07**. Step 04 stages are floor-scoped (S03-D13); the loop wraps
  them later.
- **Domain gates** (`proto3:D020`: `check_min_area` / `check_min_dim` /
  `check_access_schema` / `check_multi_floor_feasibility`) +
  `proto3:D023` required-only summation, and the consumption of
  `area_target_m2` / `area_min_m2` / `min_dimension_m` → **Step 05/07**
  (growth stays target-agnostic, S04-D3).
- **`ProgramRequest` construction / `expand_program()` / `target_rules`
  role↔usage fill** → **Step 05/06**. Step 04's adapter consumes a
  *given* `ProgramRequest`; it does not synthesize one.
- **Adding a `seed_position` field to the new schema** — not done. The
  production path is auto-placement (S04-D7); manual seeds live only in
  the ported 33-case golden fixture data.
- **Canonical SVG renderer + `pipeline.gif`** → **Step 08**; this Step's
  matplotlib renderers are the throwaway dev-bridge (carry S03-D4).
- **`ResearchBIM_synthetic-bim` adapter** → **Step 09**, post-v1.
- **Multi-floor orchestrator + cross-floor anchor alignment** →
  **Step 10**, post-v1. Anchors arrive pre-placed (S04-D4); v1 does not
  align them across floors.
- **Access guarantee** (corridor ↔ `vertical_circulation` room
  connectivity) → deferred, documented v1 limitation (S04-D4). The fixed
  anchor room may be geometrically isolated by its own donut-hole.
- **Pathological anchor geometries** (boundary-touching notch, part-
  splitting span, thin slivers) → interior-hole case first; weird cases
  deferred (S04-D4).
- **Wholesale Cell test porting** — new tests are written fresh against
  the new schema (carry S03-D11); Cell's seed / growth / corridor tests
  are mined selectively for known-good pinned values, not copied en masse.

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| **Auto-placement is the production path but the 33 Cell goldens are all manual-seed** (S04-D7) — `auto_place_seeds_by_cells` (~320 lines, the largest single algorithm in the port) is golden-uncovered by the showcase cases. Bugs there ship silently. | (a1): manual-seed goldens lock the growth/absorb/corridor algorithm to Cell; auto-placement gets dedicated coverage — port Cell's `test_seed_placement.py` (4.9) **plus** a small set of auto-driven golden cases with freshly-reviewed seed/layout outputs (4.12). Residual: auto-placed layouts get less eyeball scrutiny than the 33 manual ones — accept for v1, widen if `run()` integration (Step 07) surfaces issues. |
| **S04-D8 param-refactor divergence** — re-plumbing `region_partition_growth` to *take* `atoms`/`regions`/`region_graph` instead of recomputing them could subtly diverge from Cell's internal recompute (e.g. a different `policy` default), breaking the Cell-match goldens. | Before trusting any growth golden, assert the passed-in Step 03 outputs are byte-identical to Cell's internal recompute on the same case (both deterministic). Port the params change as a pure refactor first, goldens second. |
| **Anchor `difference` geometry** — punching a hole can leave thin strips / extra reflex corners that make region cuts messy, or split a part into a MultiPolygon. This echoes the C10 territory hole fragility (`test_stages_territory.py` xfail). | Validate the donut-hole on a real anchor fixture via atomize/regionize + PNG eyeball **early** (4.4), before any growth depends on it. Interior-hole case first; defer boundary-touching / spanning anchors (S04-D4). atomize hole-exclusion itself is already verified (`test_atomize_hole_is_excluded`). |
| **GEOS sensitivity** — seed/growth call shapely `centroid` / `covers` / `intersection`; results can drift across GEOS builds (the regionize goldens already forced a `geos=3.14.1` CI pin). | Goldens are **region-id digests** (S04-D5), not polygons — far more stable than coordinate comparison, since region membership rarely flips on sub-mm float drift. CI stays pinned to `geos=3.14.1` (canonical `IfcOpenHouse`). |
| **7→4 role collapse correctness** (S04-D3) — `hub`→`public`-first mapping + `RoomSpec.name = SpaceUnitSpec.id` identity recovery; a broken id round-trip would mislabel output roles at Step 07. | Adapter unit tests (4.14) assert the id round-trips and that the recovered 7-class role matches the input `SpaceUnitSpec`. `vertical_circulation` exclusion + re-insertion tested via the full-pipeline anchor fixture (4.15). |
| **Manual review burden** at 4.11 / 4.13 — eyeballing samples of 33 cases × (seed/layout, corridor) before freezing goldens; bad goldens lock in bugs. | Sample diverse cases (not exhaustive), per S03-D9 precedent — render PNG → eyeball → then commit JSON+PNG. Per-stage commit boundary = review boundary, so re-do scope stays contained. |
| **Golden + module volume** — Step 04 adds seed/layout/corridor goldens (×33) + anchor fixtures + 15 modules; Step 03 goldens already ~11 MB. | Digests are region-id lists (tiny); PNGs are the weight — keep dpi low (carry S03-D6). 15 flat modules navigable via `growth_*` / `corridor_*` prefixes (S04-D6). Revisit Git LFS for PNGs only if bloat grows. |
| **Branch lifetime** — Step 04 is larger than Step 03; longer drift from `main`. | Merge `main` into the branch every 1–2 work items; goldens land in their own commits so golden-rewrite noise is reviewable (carry from Step 03). |

---

## 7. Next-Step linkage

Step 04 close → **Step 05 (Program layer port)** kickoff. At Step 05's
§4.1 commit (proto3:D016 H011 deferred-archive pattern): `git mv
004_Step04_AlgorithmCore_Plan.md 004_Step04_AlgorithmCore_Tracker.md
legacy/step04/`, then write `005_Step05_ProgramLayer_Plan.md` + Tracker.
