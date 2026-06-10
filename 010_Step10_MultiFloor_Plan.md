# 010 Step 10 — Multi-Floor Orchestrator Plan

Status: Completed — **merged to `main`** (`382966c`, `--no-ff`, 2026-06-10) after external review response; S10-D1..D13
Type: Step plan
Branch: `step10-multifloor` (D005 — triggers fired: **integration** [`run()`
restructured into a per-floor body + cross-floor pre/post passes] + **regression
risk** [the single-floor **apartment** path must stay byte-identical over the 33
geometry goldens + corpus B; a restructure defect would surface as golden
drift]. Same shape as Step 04/05/07.)
Last updated: 2026-06-08

---

## 0. Purpose

Step 10 lifts `run()` from **single-floor** to **multi-floor**, activated by the
first multi-floor target: **house** (D001 / Pipeline §5.2). It is the last
multi-floor **capability** piece — *not* the live integration: actually plugging
the output into the downstream **ResearchBIM synthetic-BIM** Stage 4 needs the
`Building ↔ ShapeInput` / `LabeledRoomLayout → storey.rooms` adapter, which is
**Step 09** (S10-D9). Step 10 makes `run()` multi-floor and shapes its input to
map 1:1 from `Building`, so Step 09 is a thin layer.

**The key framing — most of multi-floor is already done.** A pre-planning spike
(throwaway — it **monkeypatched `_RULES_PATH_BY_TYPE["house"]` to a `/tmp/house.json`
with `requires_single_floor=false`**, since the shipped `run()` only knows
apartment and blocks multi-floor at `check_multi_floor_feasibility`) ran a
3-floor house — and a 3-floor house with a 2nd-floor courtyard hole — through
`run()`'s per-floor body: both returned `valid=True`, 0 failures, with the
shared stair re-inserted on every floor and rooms growing around the courtyard.
That registry + typology gap is exactly what 10.2 lands for real. The reason it
works at all: the geometry half (atomize → growth → carve → labeling) is
**per-floor independent**, `run()` already loops `for floor in shape.floors`,
`anchors_on_floor` already filters anchors per floor, and
`_check_anchor_footprint_containment` already validates the anchor footprint
against **every** floor in its `floor_range`. The schema is multi-floor-aware
(per-floor `FloorShape`, global `SpaceUnitSpec.id` uniqueness,
`PROGRAM_FLOOR_NOT_IN_SHAPE`).

So the substantive NEW work is **not geometry** — it is the cross-floor /
building-level concerns the per-floor loop currently skips, plus the typology:

1. **A multi-floor typology** — `house.json` (`requires_single_floor=false`); the
   `check_multi_floor_feasibility` gate currently rejects every multi-floor run
   because apartment is the only shipped typology (single-floor).
2. **Building-level cardinality** — apartment checks cardinality *per floor*; a
   house needs the kitchen/living to exist *building-wide*, not on every floor.
3. **Vertical-circulation continuity** — that the vertical anchors collectively
   connect **all** floors into one reachable stack (trivial for one shared core,
   real for N partial-range cores).
4. **Multi-floor fixtures + goldens** — none exist (all single-floor today).

**The consumer drives the input model (ResearchBIM alignment).** This output is
destined for `ResearchBIM_synthetic-bim`'s Stage 4 (`run_s04_core_bsp` →
`storey.rooms`). Their data model maps cleanly onto ours (both **meters, CCW,
centerline**):

| ResearchBIM (`/workspace/ResearchBIM_synthetic-bim`) | room_layout |
|---|---|
| `Building` | `ShapeInput` |
| `Storey { level, storey_height, footprint }` | `FloorShape { level, floor_to_floor_height, parts }` |
| `Footprint { polygon }` (single, CCW, **no holes** today) | `FloorShape.parts=[ShapePart]` (superset: multi-part + holes) |
| `Building.core { stair_polygon, ps_polygon?, eps_polygon? }` (per-building) | `ShapeInput.vertical_anchors: list[VerticalAnchor]` (N anchors, `floor_range`) |
| `Storey.rooms: list[Room{ polygon, usage }]` | `LabeledFloorLayout.rooms: list[LabeledRoom{ polygon, role, usage }]` |

So the Step 10 input model is designed **to match `Building`/`Storey`** — but is
**not narrowed to it**: room_layout keeps the full footprint model (multi-part +
holes), because ResearchBIM's "simple polygon only" is *their* current limitation
("revisit in Target C/D"), and our adapter is forward-compatible (pass-through).
The live `Building ↔ ShapeInput` adapter is **Step 09** (deferred until
ResearchBIM's footprint passing lands); Step 10 uses **hand-built fixtures** of
two kinds (kept distinct — review #9): a **current-ResearchBIM-translatable** set
(single simple footprint per floor, one shared core — a literal `Building`
today), and a **forward-compatible** courtyard-floor fixture that exercises
room_layout's superset (holes) — *not* a today-ResearchBIM input, but the shape
ResearchBIM's Target C/D will eventually send.

Cross-references:

- `docs/000_Pipeline_Overview.md` §2.1 (multi-floor-aware `ShapeInput`, anchors),
  §3 (per-floor pipeline), §5.2 (Step 10 activation trigger).
- `docs/000_Architecture_Decisions.md`: **D001** (per-floor loop; multi-floor
  orchestration deferred), **D004** (`vertical_circulation` anchor binding).
- `legacy/step05/...` — S05-D6 (`check_multi_floor_feasibility` building-level
  gate landed there; its real multi-floor body is **here**).
- `legacy/step07/...` — the never-crashes composition `run()` must preserve; the
  anchor-containment validator (review #2) already loops all floors.
- `/workspace/ResearchBIM_synthetic-bim/src/synthetic_bim/data_model/`
  (`building.py`, `storey.py`, `footprint.py`, `core.py`, `room.py`) +
  `stages/s04_core_bsp/__init__.py` — the consumer's model + Stage 4 entry.

---

## 1. Definition of Done

```text
Step 10 closes when:

1. house typology (10.2): data/target_rules/house.json (requires_single_floor=
   false; cardinality_scope="building" (S10-D13); role-level min_cardinality;
   full default_min_area_m2 Role map), registered in run()'s _RULES_PATH_BY_TYPE.
   The 4-role model fits a residential house (spike: hub=landing/living,
   private=bedroom, wet=kitchen/bath, service=utility, vc=stair) — at the ROLE
   level (it does not pin specific usages — S10-D11).

2. Building-level cardinality (10.3): when cardinality_scope=="building"
   (S10-D13 — a TargetRules field, NOT requires_single_floor), min_cardinality is
   checked over the SUM across floors (role-level — ≥1 wet / hub / private
   building-wide; it does NOT guarantee a kitchen exists — S10-D11). scope==
   "per_floor" (apartment) is the exact per-floor path — BYTE-IDENTICAL. Emits a
   ProgramInstantiationFailure. Per-floor area/dim gates stay per-floor.

3. Vertical continuity (10.4, S10-D6): the floors that actually EMIT a vc room
   (floor has a vc spec whose anchor covers it — vc_rooms is spec-gated) must form
   one connected vertical run over the building's occupied levels — else
   VERTICAL_CIRCULATION_DISCONTINUOUS. Defined on emitted rooms, not raw anchor
   floor_ranges (#5). Vertical-only: horizontal reachability between same-floor
   cores is NOT asserted (access topology is deferred v1-wide — #6). Anchor
   all-floor containment already exists (verified, reused).

4. vc-only / growable-less floor is VALID (10.6, S10-D12): building cardinality
   lets a floor through with no growable rooms (a pure circulation / stair floor);
   it emits only its fixed vc rooms (growth skipped). run() skips the geometry
   block for a growable-less floor (so program_to_fixture — which still raises on
   no-growable-rooms — is never called) — closing the latent never-crashes gap
   (prior review #10) that building cardinality now makes reachable. Empty floor
   program (no specs at all) policy decided at 10.6.

5. run() restructure (10.5, S10-D2): the per-floor body extracted to _run_floor;
   run() = cross-floor PRE pass (cardinality + continuity — both program/anchor-
   based, no layout needed) → per-floor loop (unchanged). NO vague "completeness"
   POST pass (#7 — there is no cross-floor fact only knowable post-layout in v1).
   Pure, never-crashes (proto3:D018) preserved. Single-floor apartment path
   BYTE-IDENTICAL (33 goldens + corpus B unchanged).

6. Multi-floor fixtures + goldens (10.7): (a) a current-ResearchBIM-translatable
   3-floor house (single simple footprint/floor + one shared core) + (b) a
   forward-compatible courtyard-floor variant (holes — room_layout superset, not
   a today-ResearchBIM input, #9) + (c) a discontinuity failure-injection. Every
   floor carries floor_to_floor_height (multi-floor REQUIRES per-floor height —
   #10; a 1-floor None stays valid). Goldens (GEOS 3.14.1); input maps 1:1 from
   Building/Storey (S10-D8/D9).

7. Viz (S01-D10, S10-D10): per-floor SVG/GIF reused as-is (already per-floor); a
   stacked multi-floor SVG sheet is out of scope (Step 09/later).

8. ruff (check + format) + full pytest green (conda IfcOpenHouse, GEOS 3.14.1);
   apartment goldens byte-identical; Plan/Tracker closed; S10-D series finalized;
   merged --no-ff to main.
```

---

## 2. 결정 기록

Decisions locked during Step 10 planning (chat discussion 2026-06-08), several
grounded in throwaway spikes + a survey of the ResearchBIM consumer. Predecessor
decisions referenced as `S0N-Dxx` / `proto3:Dxxx`.

| # | Topic | Decision |
|---|---|---|
| **S10-D1** | Branch | Work on `step10-multifloor`, merge `--no-ff` at close. D005 triggers: **integration** (`run()` gains cross-floor passes) + **regression risk** (apartment path must stay byte-identical). |
| **S10-D2** | Orchestrator = **evolve `run()`**, not a new entry | `run()` already loops `for floor in shape.floors`, so D001's "wraps per-floor `run()`" is satisfied by `run()` *being* the wrapper. Extract the per-floor body to `_run_floor`; add a cross-floor **PRE** pass (building cardinality + vc continuity — both program/anchor-based). **No POST pass** (#7 — no cross-floor fact is only knowable post-layout in v1). Rejected: a separate `run_building()` entry (would duplicate the loop + split the contract). |
| **S10-D3** | First multi-floor typology = **house** | Residential, fits the 4-role model cleanly (spike-verified: landing/living→hub, bedroom→private, kitchen/bath→wet, utility→service, stair→vc). `house.json` with `requires_single_floor=false`. Hotel/office (repetitive / non-residential) deferred — flagged in Step 06 as possibly not fitting 4-role. |
| **S10-D4** | Program allocation = **caller-supplied, validate only** | The caller decides which spaces go on which floor (`ProgramRequest.floor_programs`, per D001 §2.2). Step 10 **validates** the allocation is building-feasible; it does NOT auto-allocate a building program across floors (no consumer; YAGNI). |
| **S10-D5** | Cardinality scope = **building-level for a house** | apartment checks `min_cardinality` per floor; a house checks it over the **sum across floors** (a house needs its required rooms *building-wide*, not on every floor). The scope is selected by a `TargetRules` field, **not** by `requires_single_floor` (S10-D13 — they are different axes). The check is **role-level only** (does not guarantee a specific *usage* like a kitchen — S10-D11). Per-floor **area/dim** gates stay per-floor (genuinely per-room/floor). Single-floor (apartment) stays byte-identical. |
| **S10-D6** | Vertical-circulation **vertical continuity** (on emitted vc rooms) | The floors that actually **emit a vc room** — a floor with a `vertical_circulation` spec whose `anchor_id` covers it (`vc_rooms` only emits when the *floor's* program carries the spec — verified) — must form one connected vertical run over the building's occupied levels (consecutive levels bridged) — else `VERTICAL_CIRCULATION_DISCONTINUOUS`. Defined on emitted rooms, **not** raw anchor `floor_range`s (an anchor can span a floor whose program omits the vc spec → no stair there, S10-review #5). It is **vertical-only**: it does *not* assert horizontal reachability between two cores on the same floor — that is the access-topology concern deferred v1-wide (`check_access_schema` no-op, `doors=None`); named "continuity", not "reachability" (#6). Trivial for one shared core; real for N partial cores (S10-D7). Anchor-in-every-floor *containment* already exists (`_check_anchor_footprint_containment` loops the range — verified, reused). |
| **S10-D7** | **N anchors**, not one | `ShapeInput.vertical_anchors` is a list — design for N stairs/elevators/shafts (ResearchBIM R2 adds ps/eps shafts; large buildings have multiple stairs). Test with one shared core first. This is *why* S10-D6 (continuity) is real, not negligible. |
| **S10-D8** | **Full footprint model** kept (not narrowed to "simple") | room_layout already handles multi-part + holes (case_33; spike: 3-floor + 2nd-floor courtyard → `valid=True`). ResearchBIM's `Footprint` forbids holes *today* ("revisit Target C/D") — that's the consumer's limitation, not ours. Keep the full model so the adapter is forward-compatible; add a courtyard multi-floor fixture to lock it in. |
| **S10-D9** | Input model **aligned to ResearchBIM `Building`/`Storey`**; live adapter = Step 09 | The multi-floor input is designed to map 1:1 from `Building`(`storeys`, per-storey `footprint`, shared `core`) so the future `Building ↔ ShapeInput` adapter is a thin translation. The **live adapter is Step 09** (deferred until ResearchBIM's footprint passing is implemented); Step 10 uses **hand-built fixtures modeling the `Building` shape**. |
| **S10-D10** | Viz = **reuse per-floor** | The Step 08 SVG/GIF renderers already operate per `LabeledFloorLayout` (per floor). Multi-floor reuses them as-is (one SVG/GIF per floor). A stacked/sheet composition is deferred (Step 09 / later). |
| **S10-D11** | house cardinality = **role-level**, no usage guarantee (review #3) | `min_cardinality` counts **roles** (`wet`/`hub`/`private`/…), not usages. Because `wet`=kitchen+bath and `hub`=landing+living, `wet≥1` is satisfied by a bathroom alone and `hub≥1` by a landing alone — so role cardinality **cannot guarantee a specific usage** (a kitchen). v1 keeps role-level and **states this limitation**; usage is a caller pass-through (S06-D3), so a usage-level cardinality rule is a separate future mechanism (§5), not Step 10. |
| **S10-D12** | A **vc-only / growable-less floor is valid** + never-crashes (review #8) | Building-level cardinality (S10-D5) lets a floor through admission with no growable rooms (e.g. a circulation-only mezzanine / pure stair floor). That floor emits only its **fixed vc rooms** (no growth). `program_to_fixture` raises `ValueError` on no-growable-rooms — which would escape `run()` (it catches only `DomainGate`/`Geometry` failures). The fix is at the **`run()` level**: it detects a growable-less floor and skips the geometry block (so `program_to_fixture` is never called), emitting just the fixed vc rooms — **closing the latent never-crashes gap** (prior external-review #10, now *reachable* via building cardinality). `program_to_fixture` itself is **unchanged** (it correctly raises on misuse; `run()` simply no longer reaches it with no growable rooms). |
| **S10-D13** | `TargetRules.cardinality_scope` field (review #4) | The cardinality scope (`"per_floor"` \| `"building"`) is an **explicit `TargetRules` field**, decoupled from `requires_single_floor` — they are different axes (a future hotel can be multi-floor *and* want a bathroom/service room **per floor**). apartment=`per_floor` (byte-identical), house=`building`. The gate branches on this field, not on floor count. |

Decisions expected to emerge *during* build (recorded as **S10-D14+** when they
land): the continuity algorithm (interval-union vs graph over occupied levels);
whether `_run_floor` returns a small per-floor result struct or appends in place;
the `house.json` cardinality/area values + provenance grade; the
`cardinality_scope` default for typologies with no rules yet.

---

## 3. Directory structure (indicative target state)

```text
src/room_layout/
  run.py                 # MODIFIED: _run_floor extraction + cross-floor PRE pass (S10-D2; no POST)
  data/target_rules/
    house.json           # NEW: multi-floor typology (requires_single_floor=false + cardinality_scope, S10-D3)
  schema/
    target.py            # MODIFIED: TargetRules.cardinality_scope field (S10-D13)
    failure.py           # MODIFIED: VERTICAL_CIRCULATION_DISCONTINUOUS code
  constraints/
    gates.py             # MODIFIED: building-vs-per-floor cardinality on cardinality_scope (S10-D5/D11)
    multi_floor.py       # NEW (or in gates): vc vertical continuity on emitted vc rooms (S10-D6)
  stages/
    # (program_adapter.py UNCHANGED — `run()` skips a growable-less floor before
    #  calling program_to_fixture, which still raises on misuse; S10-D12)

tests/
  test_house_typology.py       # NEW (actual): house.json load + single/multi-floor + building cardinality
  test_multi_floor_gates.py    # NEW (actual): vc continuity + vc-only/empty floor + trace
  test_golden_house.py         # NEW (actual): 3-floor + courtyard + discontinuity goldens + geometry invariants
  golden/house_*/run.json       # NEW: multi-floor goldens (GEOS 3.14.1)
  # fixtures are IN-CODE (like corpus B), no tests/fixtures/ dir
```

Module split (vc continuity in `gates.py` vs a new `multi_floor.py`)
is finalized at the work items; the layout above is indicative.

---

## 4. Work items

Bottom-up: typology → building-level gates → run() restructure → fixtures →
close. Each item is one commit (proto3:D015). Mirrors into Tracker §1.

| # | Work item | Verify |
|---|---|---|
| **10.1** | Kickoff — Plan + Tracker land (Step 08 docs already archived → `legacy/step08/` in `9483640`) | docs review |
| **10.2** | `house.json` typology (S10-D3) — `requires_single_floor=false` + `cardinality_scope="building"` (S10-D13) + role-level `min_cardinality`; register in `_RULES_PATH_BY_TYPE`; confirm 4-role fit | loads via `load_target_rules`; multi-floor gate no longer rejects house |
| **10.3** | `TargetRules.cardinality_scope` field (S10-D13) + **building-level** role cardinality (S10-D5/D11); gate branches on the field | building-cardinality unit tests; **33 apartment goldens unchanged** (scope=`per_floor`) |
| **10.4** | vc **vertical continuity** (S10-D6) on **emitted vc rooms** (vc-spec ∩ anchor coverage; not raw `floor_range`); `VERTICAL_CIRCULATION_DISCONTINUOUS` | continuity tests incl. a gap-injection (N partial cores) + a spec-omitted-floor case |
| **10.5** | `run()` restructure (S10-D2) — `_run_floor` extraction + cross-floor **PRE** pass (cardinality + continuity); **no POST** (#7); never-crashes preserved | **apartment goldens + corpus B byte-identical**; multi-floor house runs |
| **10.6** | vc-only / growable-less floor **valid** (S10-D12) — `run()` skips growth before `program_to_fixture` (emit fixed rooms); empty-floor policy | a vc-only floor returns valid (no crash); was the latent review-#10 path |
| **10.7** | Multi-floor fixtures + goldens (S10-D7/D8/D9, #9/#10) — (a) current-RB 3-floor house + (b) forward-compat courtyard variant + (c) discontinuity injection; per-floor heights | multi-floor run-goldens green; courtyard valid; height required when >1 floor |
| **10.8** | Viz (S10-D10) — confirm per-floor SVG/GIF render each house floor | renders 3 floors to SVG |
| **10.9** | Close — README + Progress + Pipeline sync; S10-D finalize; ruff + pytest green; `--no-ff` merge | CI green; merged |

---

## 5. 의도적으로 하지 않는 것 (out of scope)

| Item | Why / where |
|---|---|
| Live ResearchBIM adapter (`Building ↔ ShapeInput`, `LabeledRoomLayout → storey.rooms`) | **Step 09** (S10-D9). Deferred until ResearchBIM's footprint passing is implemented. Step 10 designs the input to map 1:1 so the adapter is thin; uses hand-built Building-shaped fixtures. |
| Auto program allocation (building program → per-floor split) | Caller-supplied (`floor_programs`, S10-D4 / D001). No auto-allocator — no consumer. |
| **Usage-level cardinality** (e.g. "≥1 kitchen", not just "≥1 wet") | S10-D11 (#3): cardinality is role-level; `usage` is a caller pass-through (S06-D3), not a constrained field. Pinning specific usages is a separate future mechanism (a usage-cardinality rule + making `usage` typed) — not Step 10. v1 states the role-level limitation honestly. |
| **Horizontal reachability** / full access topology (can you walk between two same-floor cores; door/corridor connectivity) | #6: v1's access topology is deferred building-wide (`check_access_schema` no-op, `LabeledRoom.doors=None`). S10-D6 validates **vertical** continuity only. Full reachability waits on the access/door upgrade (Pipeline §2.4). |
| Hotel / office / warehouse multi-floor typologies | house first (S10-D3). Non-residential typologies' 4-role fit is unresolved (Step 06 flag) — separate work. |
| Stacked multi-floor SVG **sheet** composition | Per-floor SVG/GIF reused (S10-D10). A building elevation/sheet view is Step 09 / later. |
| Massing / footprint **generation** | The consumer's (ResearchBIM Stage 1) job. room_layout *receives* per-floor footprints; it does not generate them. |
| Cross-floor **geometry** coupling (slab alignment, structural columns, stair geometry) | Floors are geometrically independent given the anchors (verified). Step 10 adds cross-floor *validation*, not cross-floor geometry. Stair/slab/columns are ResearchBIM stages. |
| Elevator-vs-stair behavioral distinction | Both are `vertical_circulation` anchors; v1 treats them identically (continuity only). |

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| `run()` restructure drifts the **apartment** goldens (the D005 regression trigger) | `_run_floor` extracts the per-floor body **verbatim**; the cross-floor passes are no-ops for single-floor (one floor → continuity trivial, building cardinality == per-floor). 33 goldens + corpus B are the gate at 10.5. |
| house 4-role fit breaks on a real residential program | De-risked by the spike (3-floor house valid). Residual: the "landing/hall as hub" modeling on bedroom floors — watch at 10.2/10.7; if the 4-role model genuinely can't express a floor, that surfaces as a separate role-model task (not silently forced). |
| Building-vs-per-floor cardinality split introduces an apartment edge case | apartment stays on the **exact** per-floor path (single floor ⇒ building sum == per-floor). Only `requires_single_floor=false` typologies take the building-level branch. |
| GEOS-pinned multi-floor goldens (the known #1 limitation) | Same caution as v1: goldens are GEOS 3.14.1; documented. Multi-floor digests are GEOS-stable (region-id based). |
| vc continuity corner cases (basements `level<0`, a stair skipping a floor, single-floor building) | Define continuity on the sorted set of occupied levels (consecutive in the building's level list, not raw integers — handles basements + gaps); single floor ⇒ trivially continuous. Cover with injection tests at 10.4. |
| Input model diverges from ResearchBIM, making the Step 09 adapter fat | The §0 mapping table is the contract; fixtures are authored *as* Building translations (S10-D8/D9). Any field that can't map is surfaced now, not at Step 09. |
| Building cardinality makes the `program_to_fixture` no-growable `ValueError` **reachable** → `run()` crashes out (the latent prior-review #10) | 10.6 (S10-D12) fixes it *with* the cardinality change in the same Step: a growable-less floor skips growth gracefully (emits fixed rooms), never raising. A regression test drives a vc-only floor through `run()` and asserts `valid` + no exception. |
| Role-level cardinality silently lets a kitchen-less "house" pass | Not hidden: S10-D11 states the limitation in the DoD + §5; the house fixtures still *include* a kitchen (realistic), and usage-level enforcement is explicitly deferred, not forgotten. |

---

## 7. Next-Step linkage

Step 10 completes the **multi-floor** capability for the **house** target —
`run()` produces a valid multi-floor `LabeledRoomLayout` with cross-floor
validation (building cardinality + vc vertical continuity), the input model
aligned to ResearchBIM's `Building`/`Storey`.

**Step 09** (ResearchBIM adapter) is the remaining integration piece: the live
`Building ↔ ShapeInput` / `LabeledRoomLayout → storey.rooms` translation,
activated when ResearchBIM's footprint passing lands. Because Step 10 designed
the input to map 1:1 (S10-D8/D9), Step 09 is a thin translation layer, not a
redesign. Hotel/office multi-floor typologies and a stacked SVG sheet are
independent later work.
