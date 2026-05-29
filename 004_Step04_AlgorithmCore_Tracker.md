# 004 Step 04 — Algorithm Core Port Tracker

Status: Active
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
- [ ] **4.8** `growth_cells.py` + unit tests
- [ ] **4.9** `growth_seed.py` (auto placement) + port Cell seed-placement tests (auto coverage, S04-D7)
- [ ] **4.10** `growth_absorb.py` (shape_gate consumer) + unit tests
- [ ] **4.11** `growth_partition.py` (params per S04-D8) + viz seed/layout + 33-case `seed.json`/`layout.json` + manual review
- [ ] **4.12** Auto-placement golden coverage — auto-driven cases, freshly-reviewed goldens (S04-D7)
- [ ] **4.13** corridor stack + viz corridor + 33-case `corridor.json` + manual review
- [ ] **4.14** `program_adapter.py` (S04-D3) + unit tests
- [ ] **4.15** `anchors.py` ② fixed-room re-insertion + host_role=None + full-pipeline anchor test (S04-D4)
- [ ] **4.16** Demo CLI extension (seed/layout/corridor → `outputs/step04/`)
- [ ] **4.17** Step close + `git merge --no-ff` → `main`

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

_TBD at Step close._
