# 004 Step 04 — Algorithm Core Port Tracker

Status: Closed on branch — pending no-ff merge to `main`
Type: Step tracker
Branch: `step04-algorithmcore`
Last updated: 2026-05-29

Mirrors Plan §4 work items 1:1 in §1 checklist (per `proto3:D016`).

---

## 1. Plan §4 work items

- [x] **4.1** Plan + Tracker land + `git mv` Step 03 docs to `legacy/step03/` + §5 Step-map renumber (+1 shift) — commit `6b2c525`
- [x] **4.2** ~~Scaffold~~ **RETIRED** — Step 03 infra already covers it; `assert_golden` is generic, digest builders move to 4.11/4.13 (no empty stubs)
- [x] **4.3** `shape_gate.py` + unit tests (leaf, S03-D16) — 11 tests green, ruff clean
- [x] **4.4** `anchors.py` ① donut-hole preprocessing (`subtract_anchors` / `anchors_on_floor`) + 5 tests; validated via atomize/regionize — clean ~2–4 m² regions, no slivers around the hole (S04-D4/D5)
- [x] **4.5** `seed_placement.py` helpers (`SeedPlacement` / `region_degree` / `region_area` / `pick_top_centrality` / `_bfs_all_distances`) + 7 tests — commit `18994cc`
- [x] **4.6** `room_growth.py` result types (`GrownRoom`/`GrowthResult`) + `LayoutFixture`/`RoomSpec` (`GrowthRole` 4-class) + Cell `DEFAULT_ROLE_*` constants (S04-D3/D7) — 17 tests
- [x] **4.7** Port Cell `layout_fixtures.py` 33-case programs (manual seeds) → `growth_fixture.json` per case + `tests/_fixtures.py` loader (S04-D7 a1) — 35 tests
- [x] **4.8** `growth_cells.py` (`reflex_vertices_local` / `vertex_cells_of_piece` / `_assign_to_cells` / `_snap_to_region_edge` / `_guillotine_partition`) + 10 tests
- [x] **4.9** `growth_seed.py` (`auto_place_seeds_by_cells` — hub/coverage/fps) + 4 integration tests (distinct K seeds, no-public→no hub, K>0, determinism)
- [x] **4.10** `growth_absorb.py` (3-stage absorption, `shape_gate` consumer) + 8 tests + adversarial-verification workflow (0 confirmed issues)
- [x] **4.11** `growth_partition.py` (`region_partition_growth`, S04-D8 params) + `viz/stages/layout.py` + 33-case `layout.json` + `layout.png` sidecars + manual review ✓ (seed.json/seed.py → 4.12, consideration B)
- [x] **4.12** Auto-placement goldens — all 33 cases: `seed.json` (phase→region) + `layout_auto.json` + `seed.png`/`layout_auto.png` sidecars + `viz/stages/seed.py` (S04-D7); reviewed → hub-dominant imbalance logged as known v1 limitation
- [x] **4.13** corridor stack (6 modules: params/index/path/stage1/stage2/corridor, S04-D8) + `viz/stages/corridor.py` (connectivity overlay) + 33-case `corridor.json` (manual) **+ `corridor_auto.json` (auto, user add)** + `corridor.png`/`corridor_auto.png` sidecars; probe 33/33 + Cell byte-match; manual review ✓
- [x] **4.14** `program_adapter.py` (`program_to_fixture`, S04-D3) + 7 tests — incl. integration proof that case_01 via adapter == `to_auto_fixture` (same GrowthResult)
- [x] **4.15** ~~`anchors.py` ② fixed-room re-insertion + full anchor pipeline~~ **DEFERRED → Step 07** (scope split: anchors are the only non-Cell-port piece; fixed room is polygon-based = Step 07 labeling. `subtract_anchors` (4.4) stays as a tested forward helper.) — see Plan §7 anchor/connectivity cluster
- [x] **4.16** Demo CLI extension — `viz/demo.py` adds seed/layout/corridor stages (production/auto path via `program_to_fixture`) → `outputs/step04/`; verified case_33 all-stages + case_05 corridor
- [x] **4.17** Step close — `docs/000_Progress_Tracker.md` updated + close commit; `git merge --no-ff` → `main` pending user OK

---

## 2. Definition of Done checklist

_Mirrors Plan §1 — checked off at Step close._

---

## 3. Notes / decisions during execution

- 2026-05-29 — Kickoff. S04-D1..D5 locked in Plan §2 (chat discussion).
  Step-map renumbered +1 (Algorithm core inserted as Step 04; Program /
  Target / Entry / SVG shifted to 05–08; deferred adapter / multi-floor
  to 09–10). §5.3 dependency graph rewired: 04 now depends on 03
  (consumes Region / graphs), parallel with the 05→06 program/target
  line.
- S04-D6 (flat vs nested `stages/`) resolved → **flat** (Cell-faithful,
  zero churn on shipped Step 03 modules).
- 2026-05-29 — **4.2 retired** (execution finding): Step 03 already ships
  `stages/` / `viz/stages/` / `tests/golden/` + a *generic* `assert_golden`
  (digest dicts work as-is, per atomize). Nothing to scaffold; per-stage
  digest builders move to 4.11 / 4.13 with their stages. Empty stubs avoided.
- 2026-05-29 — **4.3 `shape_gate.py`** ported (faithful; imports swapped to
  `_helpers` + `regionize.Region`). `count_reflex_vertices` /
  `_reflex_of_union` unchanged. 11 unit tests (known-good values mined from
  Cell `test_shape_gate.py`, S03-D11). Green + ruff clean.
- 2026-05-29 — **4.4 `anchors.py` ① donut-hole** (`subtract_anchors` +
  `anchors_on_floor`). New to this repo (S04-D4). Subtracts applicable
  anchor footprints from the floor; `from_shapely`/`polygon_parts` handle
  hole + split generically. 5 tests (interior→hole area 96, atomize skips
  hole, spanning→2 parts, floor_range filter, no-op identity). **Realism
  geometry check**: holed floor regionizes into clean ~2–4 m² regions with
  no slivers (centered hole 32 regions / corner notch 31) — wrap-around at
  the room level still pending growth (4.11).
- 2026-05-29 — **4.5 `seed_placement.py`** ported (faithful; `region_area`
  via `to_shapely`, `Iterable` from `collections.abc` per repo ruff). 7
  tests on a synthetic line graph (degree, area tie-break, BFS distances,
  unreachable). Green + ruff clean.
- 2026-05-29 — **4.6 `room_growth.py`** ported (faithful types + validations).
  Cell's 4-class `Role` renamed **`GrowthRole`** to avoid clashing with the
  7-class public `schema.Role` (identifier-only change; algorithm untouched).
  `GrownRoom.role` is the collapsed 4-class label, not the output source of
  truth (Step 07 recovers role/usage from `name = SpaceUnitSpec.id`, S04-D3).
  Cell's `DEFAULT_ROLE_MIN_AREAS` / `DEFAULT_ROLE_ASPECT_RANGES` ported here
  (used by both the 33-case golden fixtures and the adapter). 17 tests.
- 2026-05-29 — **4.7 33-case growth fixtures**. Found: Step 03's
  `cell_fixtures_to_json.py` already wrote `input.json` (shape + 7-class
  `ProgramRequest`) but **dropped manual seeds** → input.json is the *auto*
  path. So added `scripts/cell_growth_fixtures_to_json.py` emitting a
  separate `growth_fixture.json` per case (Cell `LayoutFixture` verbatim,
  manual seeds + role tables) for the (a1) algorithm-faithful goldens;
  `input.json` left as the auto/adapter path input. `tests/_fixtures.py`
  loader + 35 tests (all 33 load; case_01 matches Cell). Manual/auto split
  now physical: `growth_fixture.json` (manual, 4.11) vs `input.json.program`
  (auto, 4.12/4.14).
- 2026-05-29 — **4.8 `growth_cells.py`** ported (faithful; only geometry-helper
  imports swapped, inline `Counter` hoisted, `piece: ShapePart` annotated).
  reflex-vertex cell decomposition + aspect-minimizing guillotine partition.
  Sole deps are `_helpers` (no other stage). 10 tests: rect→0 reflex / L→1
  reflex at (2,2); rect→1 cell / L→3 cells (area 12 conserved); cell assign
  by `covers`; snap to region edge in-range / midpoint fallback; guillotine
  1-seed + 2-seed vertical split. Also made `_helpers.rotate_radians`
  **generic** (`TypeVar` bound `BaseGeometry` + internal `cast`) so rotate
  preserves the concrete geometry type — clears the `list[Polygon]` Pylance
  warning here + future rotate callers. Runtime-identical (CI = ruff + pytest,
  no type-check gate).
- 2026-05-29 — **4.9 `growth_seed.py`** ported (auto placement: hub →
  piece-coverage → load-balanced FPS extras). `shape`→`floor` rename
  (S03-D13); inline `_min_dist` closure lifted to module-level
  `_min_centroid_dist` (avoids loop-closure lint, behavior identical). 4
  integration tests over case_06 (K distinct valid seeds + hub-first;
  no-public → no hub phase; K>0 guard; **determinism** — same seeds across
  runs, critical for reproducibility). Broad auto golden coverage → 4.12.
- 2026-05-29 — **4.10 `growth_absorb.py`** ported (3-stage W10 absorption;
  sole `shape_gate._reflex_of_union` consumer). Adaptations: imports swapped +
  inline shape_gate import hoisted (no cycle), `to_shapely` for the union
  build, `shape`→`floor`. 8 tests (aspect helpers + case_06 integration:
  single-seed bulk absorb takes all under ∞ aspect; tight gate restricts).
  **Ultracode**: ran a 9-agent adversarial-verification workflow (faithfulness
  line-diff vs Cell / adaptation completeness / test correctness / edge-case
  hunt → independent skeptical verify of each finding) — 5 raw findings, **0
  confirmed** (all were the sanctioned adaptations, correctly refuted).
- 2026-05-29 — **4.11 `growth_partition.py`** (orchestrator: seeds → vertex-cell
  allocation → 3-stage absorb → `GrowthResult`). **S04-D8** materialized:
  signature takes `regions` + `region_graph` (atoms/policy dropped — verified
  unused in the Cell body; territories resolved internally). `shape`→`floor`,
  unused Cell imports dropped, `room_growth` import hoisted.
  + `viz/stages/layout.py` (rooms by color, seed ★, leftovers hatched).
  De-risk **probe** over all 33 manual fixtures: 0 seed-resolution failures
  (risk A), 0 nondeterminism (risk D), sane assignment (29/33 full; 29/31/33
  leave 1–3 corridor-candidate leftovers). Golden driver extended →
  `test_layout_golden` × 33 (region-id digest: seed_region_id + sorted
  membership + area + unassigned + diagnostics) + `layout.png` sidecars.
  **Verification workflow** (10 agents: faithfulness line-diff / S04-D8
  atoms-policy-drop safety / golden digest) — 7 raw findings, **0 confirmed**.
  Manual review: 4 representative cases inspected (flat / cross / circle /
  donut+wing-with-holes-and-leftovers) all architecturally sound; user
  approved. Full suite **503 passed + 3 xfail**, ruff clean.
  NB (consideration B): the 33-case `layout.json` rides on Cell's **hand-placed
  manual seeds** (4.7) — it validates the partition/absorb *algorithm given
  good seeds*, NOT auto seed-placement quality. The phase-colored seed renderer
  + `seed.json` + auto-driven goldens are 4.12. User noted auto placement may
  look *more* natural — to be eyeballed at 4.12.
- 2026-05-29 — **4.12 auto-placement goldens** (all 33, user upgraded scope
  from "subset" → "all"). `viz/stages/seed.py` (phase-colored seed markers);
  `to_auto_fixture` (strips manual seeds → `auto_seed=True`); driver +
  `test_seed_golden` (phase→region_id digest) + `test_layout_auto_golden` ×33
  + `seed.png`/`layout_auto.png` sidecars. Auto probe: 33/33 success, 0
  nondeterminism, sane phase sequences. **Finding (answers "is auto more
  natural?"): NO** — auto is hub-dominant (case_01 public 69 m²; case_06
  public 57 m² + a 6 m² room) vs balanced manual. Root: central hub + FPS
  corners + target-agnostic growth (S04-D3). Faithful Cell behavior, not a
  port bug (Cell's showcase used manual seeds too). Decision: commit auto
  goldens as the faithful v1 baseline; imbalance = known limitation, fix
  (area-aware growth / room size limits) deferred (Plan §5). Full suite **569
  passed + 3 xfail**, ruff clean.
- 2026-05-29 — **4.13 corridor stack** (Phase 8, Step 04 terminal output S04-D2).
  6 modules ported (corridor_params / index / path / stage1 / stage2 / corridor);
  S04-D8: `carve_corridors` + `_build_region_index` take regions+region_graph
  (no recompute); shape→floor. Probe: 33/33 carve, 0 nondeterminism, **Cell
  live byte-match 0 mismatch**. Both Stage 1 (hub-radial base) + Stage 2 (detour
  shortcut) confirmed live — Stage 2 evaluates every case but only commits when
  detour ratio > threshold 2.0 (only case_33 fires: ratio 4.0 around the donut
  hole). corridor.json (manual) + **corridor_auto.json (auto, user requested
  end-to-end auto path)** + sidecar PNGs. `viz/stages/corridor.py` with a
  **connectivity overlay** (solid base/shortcut/hub adjacency + dotted
  via-room-entrance bridges) — added after a user catch: shortcuts DO attach to
  hub/corridor at their entrance endpoints (e.g. case_33 path 36→hub … 14→base);
  my first carved-regions-only trace had wrongly implied disconnection. case_22
  "missing room" was a tab20 palette confusion (space_3/4 same hue), not data —
  all rooms present; palette→tab10 deferred (user skipped).
- 2026-05-29 — **Deferred-gap PoC added** (after user investigation): PHASE8
  §11 goal "corridor single connected component" is unmet — a Stage 2 shortcut
  attaches via a room entrance (Cell §4.6, faithful), so case_33's
  base∪shortcut∪hub isn't one adjacency component. Investigated thoroughly:
  Cell git history shows no add-then-remove of connection logic; the §11 item
  is an aspirational *goal* with no enforcing Cell test (only per-room
  `test_w2_every_room_single_component`). Pinned by `xfail` (strict)
  `tests/test_stages_corridor.py::test_corridor_network_is_single_component_case_33`
  + Plan §5 (when: Step 07 with access-guarantee; how: post-Stage-2
  bridge-carve, damage-guarded). User chose (a) defer over (b) implement-now —
  (b) would forfeit the Cell byte-match verification anchor.
- 2026-05-29 — **4.14 `program_adapter.py`** (`program_to_fixture`, S04-D3): new
  7-class `ProgramRequest` → Cell 4-class `LayoutFixture`. hub→public placed
  first (so `hub_room_index` lands on it); `vertical_circulation`/`corridor`
  excluded; `RoomSpec.name = SpaceUnitSpec.id` (identity preserved for Step 07);
  all seeds None → auto; `area_target`/`area_min`/`min_dimension` dropped
  (Step 07 gates, target-agnostic growth); role tables default to Cell
  constants (target_rules override = Step 06 hook). 7 tests; **integration
  proof**: case_01 via adapter (from_dict ProgramRequest) == `to_auto_fixture`
  → identical GrowthResult, so the production input path
  (input.json.program → adapter → growth) matches the auto goldens.
- 2026-05-29 — **4.15 deferred → Step 07** (user decision). Rationale: anchors
  are the only non-Cell-port piece of Step 04 (new design, no Cell cross-check,
  0 of 33 goldens), and the fixed `vertical_circulation` room is polygon-based —
  it only becomes a real `LabeledRoom` at Step 07 labeling (Pipeline §2.4/§3.8
  already say labeling sources it from the anchor footprint). So Step 04 closes
  as a clean **faithful-port baseline** (4.3–4.14, all Cell byte-matched) plus
  `subtract_anchors` (4.4) as a tested forward helper. The fixed-room
  re-insertion + full anchor-aware pipeline + first anchor fixture join the
  **Step 07 anchor/connectivity cluster** (with corridor-single-component +
  access-guarantee) — Plan §7. S04-D4 revised in place.
- 2026-05-29 — **Pre-implementation re-review** (code-verified). Findings
  folded into Plan: **(#1)** all 33 Cell fixtures use *manual* seeds but
  the new schema is auto-only → S04-D7 strategy (a1): manual-seed goldens
  for algorithm match + separate auto coverage (4.9 / 4.12). **(#2)** Cell
  growth recomputes atomize/regionize internally → S04-D8: take Step 03
  outputs as params. **(#3)** `room_growth.py` also ports
  `LayoutFixture`/`RoomSpec` (not just result types) — §3 corrected.
  **(#4)** adapter sets `RoomSpec.name = SpaceUnitSpec.id` for 7→4 role
  collapse + Step 07 identity recovery — S04-D3 extended. **(#5)** §4
  reordered: adapter moved late (4.14), Cell fixture port added (4.7).
  **(#6)** anchor `difference` not always a clean hole — S04-D4 note;
  interior-first. Verified OK: atomize hole-exclusion works
  (`test_atomize_hole_is_excluded`), so the donut-hole geometry is sound.

---

## 4. Close summary

Cell **Phase 6–8** + `shape_gate` ported to `src/room_layout/stages/`
(seed_placement / growth_seed / growth_cells / growth_partition /
growth_absorb / room_growth / shape_gate + corridor stack ×6), plus two
new-to-this-repo bridges: `program_adapter` (S04-D3) and
`anchors.subtract_anchors` (S04-D4 donut-hole half). Algorithm follows Cell,
interface follows the new schema (S04-D1); the terminal `carve_corridors`
emits a region-based `CorridoredLayout` (S04-D2 — labeling/`run()` is Step 07).

**Correctness anchor**: the ported growth + corridor are **byte-identical to
Cell live across all 33 cases** (manual-seed cross-check), plus two
adversarial-verification workflows (growth_absorb, growth_partition: 0
confirmed of 12 raw findings) and a 33-case auto probe. Goldens: layout /
seed / layout_auto / corridor / corridor_auto region-id digests (S04-D5) +
PNG sidecars; the adapter reproduces the auto path exactly
(`test_adapter_reproduces_auto_path_case_01`). Final: **643 passed + 4
xfailed** under GEOS 3.14.1; ruff clean.

Decisions S04-D1..D8 (Plan §2). Work items 4.1–4.14 + 4.16 done; **4.2**
retired (Step 03 infra), **4.15** (anchor fixed-room re-insertion) deferred
to Step 07 with the connectivity cluster (corridor single-component §11 +
access-guarantee).

Investigation outcomes (user-driven): algorithm confirmed identical to Cell
(not a stale port); auto seed placement is hub-dominant (faithful, area-
balance deferred); Stage 2 shortcut attaches via room entrances and PHASE8
§11 "single corridor component" was an unmet goal (xfail PoC pinned, fix
scheduled Step 07).

Commits: `6b2c525` (kickoff) … `73521b9` (4.16) + this close. Merge to `main`
pending user OK.
