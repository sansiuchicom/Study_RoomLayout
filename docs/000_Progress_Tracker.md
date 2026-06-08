# 000 Progress Tracker

Status: Current working status only
Scope: active work item, completed work, next actions, blockers
Last updated: 2026-06-02

---

## 0. Purpose

This file tracks current implementation progress.

It should stay short. It should not duplicate the full framework, full stage
list, or full decision record.

Canonical references:

```text
Framework / pipeline / terminology:
  000_Pipeline_Overview.md

Accepted decisions / rationale:
  000_Architecture_Decisions.md
```

---

# 1. Current status

```text
Step 08 (SVG visualization) **in progress** on `step08-svg-viz` (opened
2026-06-08; D005 — branch on size + milestone, S08-D1). The v1 **ship gate**
(Pipeline §5.1): a canonical layered-SVG renderer + `make_gif()` (pipeline-
progression GIF) consuming the Step-07 `on_stage`/`StageOutput` trace. `run()`
is untouched — additive viz on the existing hook (S08-D7). Layer stack re-
derived from our pipeline (S08-D2); proto3's `viz/svg.py` is a skeleton, so
the "port" is architecture-only. S08-D1..D7 in
`008_Step08_SvgVisualization_Plan.md` §2. Step 07 docs archived →
`legacy/step07/` (4.1 kickoff, proto3:D016 H011).

Step 06 (Target rules system) **complete** on `main` (2026-06-02, D005 —
stayed on main, weak triggers, no merge needed). Built the value+loading
half of the S05-D2 boundary:
- `schema/target.py` — `TargetRules` + `default_min_area_m2` full Role map
  (S06-D1) — the expand-program SEED, not a stage01 fill (S05-D1 intact).
- `target/rules_loader.py` (NEW) — thin JSON-boundary loader (file/parse/
  recursive-finite, S06-D4); domain invariants delegated to from_dict +
  `__post_init__`, re-raised with path (S06-D2가).
- `target/adapter.py` (NEW) — single generic `TargetAdapter` (S06-D5), no
  `target_type` field/property (S06-D6 — nothing branches on it) +
  `DEFAULT_APARTMENT_RULES_PATH`.
- `data/target_rules/apartment.json` + `README.md` (NEW) — real values +
  **citation-ready graded provenance** (private 7.0 Grade-B narrow-statute proxy;
  public/service/wet Grade-C; hub/vc Grade-D) + 전용률≠density_factor flag +
  3-layer model. For the paper.
- `target/expand_program.py` (NEW) — `{role:count}` → `ProgramRequest`
  (area_min from rules, area_target/usage None, target_type stamped).
- `pyproject` package-data ships the JSON+README (wheel verified).
730 pytest + 5 xfail; ruff check + format clean. DoD test: expand output
passes stage01 + stage02.

Step 05 (Program layer port) **merged to `main`** 2026-06-02
(`f3f4906`, --no-ff; 18 commits; branch deleted + pushed to origin).
Step 04 merged 2026-05-29 (`969c4f0`).

Step 05 delivered: the program **admission layer** (pre-growth: does a
program fit a floor at all?). Ported proto3 `stage01_program` +
`stage02_gate` + 4 domain gates onto the new schema.
- `constraints/gates.py` (NEW) — 4 pure gates, m units (S05-D4): area /
  dim / multi-floor active + access no-op stub. Domain scalars injected
  as primitives; `list[SpaceUnitSpec]` passed direct (option 가).
- `schema/target.py` (NEW) — `TargetRules` value bundle (S05-D3): 3
  fields (`density_factor` / `min_cardinality` / `requires_single_floor`).
- `stages/stage01_program.py` (NEW) — required-only cardinality gate only
  (S05-D8); returns specs unchanged (S05-D5, no `ProgramInstance`).
- `stages/stage02_gate.py` (NEW) — floor-scoped area + dim (S05-D6
  revised → 다: multi-floor is building-level, hoisted to Step 07).
- `schema/program.py` — area-field realignment (S05-D1): `area_min_m2`
  required (gate input); `area_target_m2` optional (diffusion-priority
  hook — growth is target-agnostic, S04-D3, so no consumer yet).
- `schema/failure.py` — `ProgramInstantiationFailure` (sibling, S05-D5).
- 33 golden `input.json` regenerated (S05-D7): `area_target` honest-fake
  → null; **region-id digests unchanged** — the empirical S04-D3
  target-agnostic regression guard.

Boundary (S05-D2): Step 05 = gate machinery + rule *type*; Step 06 =
rule *values + loading* (JSON/adapter). 690 pytest + 5 xfail (conda
`IfcOpenHouse`, GEOS 3.14.1); ruff clean. Pre-close adversarial review:
0 gate-logic bugs, 5 items fixed (`c5c06a4`).

Deferred to Step 07 — anchor/connectivity cluster (S04 carry: anchor
fixed-room re-insertion, corridor single-component xfail, access
guarantee) + program-side join: `check_multi_floor_feasibility` call
site, per-room post-growth area/dim check (1.5 m² rejection — distinct
from Step 05's aggregate admission), `run()`, `LabeledRoomLayout`.

D-series cumulative: D001-D006 accepted; proto3:D001-D023 audited;
S02-D1..D13 + S03-D1..D16 + S04-D1..D8 + S05-D1..D8 in their Step Plans;
S06-D1..D6 in `006_Step06_TargetRules_Plan.md` §2.

Step 07 (Entry point + labeling) **complete** on `step07-entrypoint`
(2026-06-03; D005 — branched, integration + regression-risk triggers).
**Merged to `main`** (`68e8df2`, `--no-ff`, 2026-06-03) after an external +
adversarial review response (`0c03b69` — never-crashes hardening + anchor/schema
validation).

The public `run(shape, program, *, seed) -> LabeledRoomLayout` (D001) works
end-to-end — the join of geometry (03/04) + program (05/06):
- `run.py` (NEW) — per-floor loop: validate_input → rules-from-`target_type`
  (S07-D6) → multi-floor gate → admission (stage01/02) → subtract_anchors →
  atomize/regionize/region_graph → growth → carve → orphan-corridor bridge →
  labeling → per-room gate → assemble. Failure composition: catch the raisers +
  collect the per-room records → `valid=False`, never crashes (proto3:D018);
  `on_stage` hook (pure default).
- NEW modules: `stages/polygonize.py` (S04-D2), `stages/labeling.py` (§3.8 +
  vc re-insertion S04-D4), `constraints/room_gate.py` (per-room 1.5 m² reject),
  `stages/corridor_bridge.py` (orphan dead-corridor → connected spine),
  `schema/{trace,run_config}.py`, `debug_run.py` (D006 trace persistence),
  `viz/stages/final.py` (S01-D10 renderer).
- S07-D1..D6. Test corpus (S07-D2): 33-case end-to-end run goldens (A) +
  authored apartment fixtures (B: anchored / admission-fail / per-room-fail).
  4.11 resolved the 2 Step-07 xfails (K>seedable graceful; corridor bridge).
  975 pytest + 4 xfail (conda `IfcOpenHouse`, GEOS 3.14.1); ruff clean.

Two findings recorded as deferred (post-v1, paper-grade): target-agnostic
growth can grow a realistic program *invalid* (`docs/000_area_aware_growth.md`)
+ wall-thickness clear-area inset (§5.2).
```

---

# 2. Completed

| Date | Item |
|---|---|
| 2026-05-24 | `git init` + README + MIGRATION_LOG |
| 2026-05-24 | Subtree merge `archive/proto3/` (history preserved) |
| 2026-05-24 | Subtree merge `archive/celllayout/` (history preserved) |
| 2026-05-24 | GitHub remote `origin` connected, `main` pushed |
| 2026-05-24 | `docs/000_*` scaffold |
| 2026-05-24 | proto3 D001–D023 inherited-decision audit |
| 2026-05-24 | D001–D004 contract lock + Pipeline §2 typed sketches |
| 2026-05-24 | Pipeline §3 internal flow + §4 terminology |
| 2026-05-24 | Pipeline §5 Step map (7 active + 2 deferred) |
| 2026-05-25 | D005 lock — solo-mode workflow (default `main`, branch on triggers) |
| 2026-05-25 | D006 lock — output directory convention (3-category + per-stage layout) |
| 2026-05-25 | Step 01 Project skeleton — completed (8 work-item commits + 1 side-fix; CI green) |
| 2026-05-25 | Step 02 Core schema port — completed (9 work-item commits incl. chore close; 92 pytest passing; ruff clean; latent 4.3 LinearRing.area bug surfaced + fixed in 4.6) |
| 2026-05-28 | Step 03 Geometry pipeline port — completed (territory / atomize / regionize / atom_graph / region_graph + dev-bridge viz + 33×3 goldens; 371 pytest passing under GEOS 3.14.1 (IfcOpenHouse); ruff clean; S03-D13..D16 course-corrections; shape_gate deferred to Step 04) |
| 2026-05-28..29 | Post-Step-03 review hardening (on `main`, 4 commits) — CI repinned to conda-forge + `geos=3.14.1` (regionize goldens are GEOS-version-sensitive); atom/region graph `neighbors`/`edge_between` made O(1) + atom edges keyed by `atom_id` not list index; `xfail` PoCs for three latent geometry bugs (B5 regionize Pass-B atom loss; B6 region shape↔atom_ids desync; C10 territory 3-way-overlap hole); pytest `pythonpath` += `src` (bare run w/o install); `to_dict`/`from_dict` skip `init=False` derived fields (the new graph indexes had broken `RegionGraph` serialization); README/tracker doc sync. 373 passing + 3 xfailed |
| 2026-05-29 | Step 04 Algorithm core port — completed + **merged to `main`** (`969c4f0`, --no-ff; 22 work-item commits; 4.15 anchor re-insertion deferred to Step 07). Cell Phase 6–8 (seed/growth/corridor) + shape_gate ported, **byte-identical to Cell live on all 33 cases**; + `program_adapter` (S04-D3) + `subtract_anchors` (S04-D4 donut-hole). layout/seed/auto/corridor goldens + PNG sidecars; 643 pytest + 5 xfail under GEOS 3.14.1; ruff clean. S04-D1..D8. Verified via 33-case Cell cross-check + 2 adversarial-verification workflows (growth_absorb, growth_partition: 0 confirmed). |
| 2026-06-02 | Step 05 Program layer port — completed on `step05-programlayer` (18 commits; 8 work items). `constraints/gates.py` (4 pure gates, m units) + `schema/target.py` (`TargetRules`) + `ProgramInstantiationFailure` + `stage01_program` (cardinality only, S05-D8) + `stage02_gate` (floor-scoped area+dim, S05-D6 revised). `area_min_m2` → required / `area_target_m2` → optional (S05-D1); 33 golden inputs regenerated, **region-id digests unchanged** (S04-D3 target-agnostic guard, S05-D7). S05-D1..D8. Pre-close adversarial review: 0 gate-logic bugs, 5 fixes (`c5c06a4`). 690 pytest + 5 xfail under GEOS 3.14.1; ruff clean. **Merged to `main` `f3f4906` (--no-ff); branch deleted + pushed.** Post-merge: review-driven density_factor upper bound + doc sync. |
| 2026-06-02 | Step 06 Target rules system — completed on `main` (D005, no merge; 7 work items, ~13 commits). `TargetRules.default_min_area_m2` (full Role map, S06-D1) + `target/rules_loader` (thin JSON-boundary + finite, S06-D4, domain delegated S06-D2가) + single generic `TargetAdapter` (S06-D5, no target_type S06-D6) + `apartment.json` + citation-ready graded provenance README + `expand_program` ({role:count}→ProgramRequest) + pyproject package-data (wheel verified). Canonical fixes at kickoff (Pipeline §5.1 DoD role↔usage + anchor slot; Arch L90-91). S06-D1..D6. DoD test: expand output passes stage01+stage02; apartment.json admits all 33 goldens. 730 pytest + 5 xfail; ruff check + format clean. apartment values from a verified search-LLM survey; non-apartment typologies surveyed separately (may not fit 4-role model — out of scope). |
| 2026-06-03 | Step 07 Entry point + labeling — completed on `step07-entrypoint` (12 work items; **merged to `main`** `68e8df2` `--no-ff` + external/adversarial review response `0c03b69`). The public `run()` (D001) end-to-end: `run.py` join + `polygonize` (S04-D2) + `labeling` (§3.8, 7-class role/usage recovery) + vc anchor re-insertion (S04-D4) + per-room `room_gate` (1.5 m² reject) + `corridor_bridge` (orphan dead-corridor → connected spine) + failure composition (proto3:D018, never crashes out) + `on_stage`/`debug_run` D006 trace + final-layout matplotlib renderer (S01-D10). S07-D1..D6. Corpus A (33 end-to-end run goldens) + B (authored apartment fixtures). 4.11 resolved the 2 Step-07 xfails (K>seedable graceful; corridor bridge). Geometry stays byte-identical to Cell (bridge is a post-step over the unchanged carve). 975 pytest + 4 xfail (GEOS 3.14.1); ruff clean. Review response (`0c03b69`): never-crashes hardening (GROWTH_OVERSUBSCRIBED / FLOOR_CONSUMED_BY_ANCHORS caught in `run()`) + anchor-footprint containment + ShapePart polygon-validity + non-vc `anchor_id` invariant. 2 deferred findings: area-aware growth (`docs/000_area_aware_growth.md`) + wall-thickness clear-area inset (§5.2). |

---

# 3. Next actions

**Step 08 (SVG visualization) in progress** on `step08-svg-viz` (opened
2026-06-08) — the v1 **ship gate** (Pipeline §5.1): the canonical layered-SVG
renderer + `make_gif()` (pipeline-progression), consuming the `StageOutput`
trace + `debug_run` layout Step 07 landed (4.6 / 4.7). `run()` untouched —
additive viz on the existing `on_stage` hook (S08-D7). Plan/Tracker:
`008_Step08_SvgVisualization_{Plan,Tracker}.md`; decisions S08-D1..D7.

Work order (Plan §4): 4.1 kickoff (done — Step 07 docs archived →
`legacy/step07/`, H011) → 4.2 palette → 4.3 final.py merge → 4.4 `svg.py`
renderer → 4.5 `SvgRunWriter` wiring → 4.6 `make_gif()` → 4.7 tests →
4.8 close (**v1 ships**).

(Step 07 complete + merged — see §1 / §2.)

(Open follow-up, not blocking: a search-LLM survey of house/hotel/office/
warehouse rules + US/EU/KR is in flight. Those typologies may not fit the
4-role model — evaluate on return; likely data-only `<typology>.json`
adds, S06-D5, or a deferred design.)

---

# 4. Blockers

_None._

---

# 5. Known issues / accepted limitations

Recurring review findings, recorded here so they are not re-discovered each
pass. Each is either an **intended defer** (lands in a named later Step) or an
**accepted limitation** (deliberately not fixed). Last consolidated 2026-06-02
(after two external reviews of Steps 05–06).

## 5.1 Intended defers → Step 07 (the join)

| Item | Where it lands |
|---|---|
| No public `run(shape, program, *, seed)` entry point | Step 07 — the geometry (03/04) + program (05/06) join. |
| Per-room post-growth area/dim check (rejects a grown room below its own `area_min` / the "1.5 m² room") | Step 07. Steps 05/06 do only **aggregate admission** (Σ fits), not per-room. |
| Growth ignores `area_min_m2` / `area_target_m2` / `min_dimension_m` (target-agnostic, S04-D3) | Consumed at Step 07 per-room check; `area_target` meaning open (S06-D2). |
| `stage02` area gate does not subtract anchor/shaft area (over-admits when cores are large) | Step 07 anchor cluster (anchor-aware capacity). No anchors in the 33 goldens, so untriggered today. |
| `vertical_circulation` rooms / `host_role` fixed-room re-insertion | Step 07 (S04-D4). |
| `check_multi_floor_feasibility` call site | Step 07 (S05-D6 — building-level). |
| `LabeledRoomLayout(valid=False)` ⇒ non-empty `failure_records` invariant not constructor-enforced | Step 07 `run()` must uphold it (proto3:D018). |
| `expand_program` cannot produce a `vertical_circulation` room (needs `anchor_id`, which `{role:count}` can't carry) → a typology requiring vc cardinality would be unsatisfiable via expand | Step 07 anchor work decides how expand binds anchors. corridor has the analogous trap, already blocked (S06-D6); vc is **not** blocked — latent. apartment.json doesn't require vc, so moot today. |

## 5.2 Intended defers → later / no committed Step

| Item | Where |
|---|---|
| 5 xfail latent geometry/algorithm bugs: regionize centroid-on-cut atom loss (B5) + disconnected-union area loss (B6); territory 3-way-overlap coverage hole (C10); growth `K > seedable regions` → `IndexError` not graceful; corridor network not guaranteed single-connected-component | Pinned `xfail` PoCs; none triggered by the 33 goldens. Addressed when a real input hits them (Step 07+). |
| `check_access_schema` is a no-op stub | Step 09–10 (S05-D4 — no `AccessPolicy` concept yet). |
| Non-apartment typologies (house/hotel/office/warehouse) | Data-only adds (S06-D5) when scoped; may not fit the 4-role model — needs evaluation. |
| Wall thickness → clear-area room polygons (centerline → inner-face inset) | Deferred — v1 contract is **centerline** (Pipeline §2.4, ResearchBIM-aligned); wall thickness is ignored. When needed it is a *separable post-transform* on the final polygons (uniform: inward `buffer(-t/2)`; per-wall: build the shared-edge wall graph → assign thickness → subtract wall solids) — or a downstream IFC concern (`IfcWall` thickness → derived `IfcSpace`). **Not** a core-pipeline change: growth / regionize / labeling all operate in centerline space. No committed Step; revisit when IFC clear-area or a wall-thickness input is scoped. |
| Realistic program → target-agnostic growth → per-room reject (a realistic apartment can grow `valid=False`; implausible proportions, e.g. kitchen > living) | Deferred — the real fix is **area-aware growth** (post-v1 Step; the consumer `area_target_m2`/S06-D2 reserved). Full analysis: solution space (A area-aware growth / B gate-split stopgap / C v1-do-nothing) + open sub-problems (living↔circulation boundary; area-min-risk growth priority) in `docs/000_area_aware_growth.md`. Golden-locked by `apt_undersized_room` (flips to `valid=True` when A lands). v1 keeps growth target-agnostic + the §4.5 gate as-is. |

## 5.3 Accepted limitations (deliberately not fixed)

| Item | Rationale |
|---|---|
| **Frozen dataclasses hold mutable `list`/`dict`** (`ShapeInput.floors` / `.vertical_anchors`, `ProgramRequest.floor_programs`, `TargetRules` dicts) — mutable after construction | Accepted (flagged in 3 reviews). The pipeline never mutates inputs; tightening every container to an immutable type is a cross-cutting schema overhaul with no demonstrated need (honest-fix / YAGNI). Revisit only if a real in-place-mutation bug appears. |
| `bool` accepted where `int` expected in `TargetRules.min_cardinality` via **direct** construction (`from_dict` rejects it) | Accepted. The dataclass is a trusted code path (S05-D1 spirit — no speculative dataclass hardening); untrusted JSON input is guarded by `from_dict` + the loader. (Note: `expand_program` *does* reject bool/float counts — that's a public caller-facing helper, M-13.) |
| Rules-vs-`target_type` mismatch allowed (apartment rules can build a `target_type="house"` request) | Accepted (S06-D6) — nothing downstream branches on `target_type`; a cross-check guards a non-existent risk. Add when a real per-typology consumer appears. |

## 5.4 Documentation / sourcing TODO (pre-publication)

| Item | Action |
|---|---|
| `apartment.json` value provenance is mostly non-primary: `private`=7.0 is Grade-B (narrow 도시형생활주택 statute used as a proxy — downgraded from A in the 2026-06-02 review); `public`/`service`/`wet` Grade-C (international analogue, no Korean per-room min); `hub`/`vc` Grade-D (estimate); `density_factor`=0.85 + cardinality Grade-B. The Korean regime is dwelling-level, not per-room. | Replace with primary 주택법/주택건설기준 text or label as estimates before citing. Full analysis + graded source table in `docs/000_typology_gate_applicability.md` (§5/§6); per-value flags in `data/target_rules/README.md` §2. |

## 5.5 Environment (not code)

| Item | Note |
|---|---|
| Full `pytest` fails (~66 golden tests) outside the canonical runtime | Goldens are GEOS-version-pinned; run under conda `IfcOpenHouse` (GEOS 3.14.1). Use `-k "not golden"` elsewhere. |
| CI Node.js 20 deprecation warning | GitHub Actions infra notice; builds pass until 2026-06-16. Bump action versions when convenient. |
