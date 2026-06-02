# 005 Step 05 — Program Layer Port Plan

Status: Completed (pending no-ff merge to `main`)
Type: Step plan
Branch: `step05-programlayer` (D005 — regression risk: this Step is the
first real consumer of `SpaceUnitSpec`'s area fields and reshapes the
Step 02 schema artifact + regenerates the 33 golden inputs)
Last updated: 2026-06-02

---

## 0. Purpose

Step 05 lands the **program admission layer** — the pre-growth checks that
decide *whether a program can be laid out on a floor at all*, before any
geometry runs. It ports proto3's `stage01_program` + `stage02_gate` and the
4 domain gates (`constraints/gates.py`) onto the new schema.

Guiding split (S05-D2), settled in chat 2026-05-30: **Step 05 owns the gate
machinery + the rule *type*; Step 06 owns the rule *values + loading*.**
The gates are pure functions that take primitive domain values by injection
(`density_factor`, `requires_single_floor`, …); the `TargetRules` dataclass
that groups those values is defined here (its first consumer is `stage01`),
but the JSON loader / adapter / multi-typology system that *produces*
populated `TargetRules` instances is Step 06. Tests hand-construct small
`TargetRules` literals.

This Step is also where the `SpaceUnitSpec` area fields get their **first
real use** — and that use surfaced a schema mismatch (S05-D1): growth is
target-agnostic (S04-D3), so `area_target_m2` is consumed by *nobody* today,
while `area_min_m2` (the field the gates actually need) was optional. The
fields are realigned: `area_min_m2` becomes required, `area_target_m2` is
demoted to optional and documented as a diffusion-priority hook for a
possible future area-aware growth pass (no committed Step — may never land).

Step 05 stops at the **admission verdict** — `stage02` is fail-only (D020):
it accepts the program unchanged or raises a `DomainGateFailure`. Wiring the
gates into the per-room post-growth check (1.5 m² room rejection) and the
`run()` join is **Step 07** (labeling, Pipeline §3.8). The two halves
(03→04 geometry, 05→06 program) meet there.

After Step 05 closes:

- `from room_layout.constraints.gates import check_min_area, ...` imports
  cleanly; each gate is a pure `(...) -> None` raising the matching
  `DomainGateFailure` subclass.
- `from room_layout.schema.target import TargetRules` — a frozen value
  bundle with `density_factor` / `min_cardinality` / `requires_single_floor`.
- `stages/stage01_program.py` runs the required-only **cardinality** gate
  over one floor's `list[SpaceUnitSpec]` and returns that list unchanged on
  success (S05-D5 — no separate `ProgramInstance` type; nothing to
  concretize since `area_min_m2` is now required). Structural + cross-ref
  validation is **not** repeated here — it is already owned by
  `SpaceUnitSpec.__post_init__` + `validators.validate_input` (S05-D8).
- `stages/stage02_gate.py` computes footprint area / bbox from a
  `FloorShape` and runs the two floor-scoped gates (`check_min_area` /
  `check_min_dim`), unpacking `TargetRules` (S05-D6 — the building-level
  `check_multi_floor_feasibility` is the Step 07 caller's job).
- The 33 golden `input.json` are regenerated with the realigned schema
  (`area_target_m2: null`, the placeholder heuristic dropped); region-id
  digest goldens are unchanged (input shape changes, growth output does not).

Cross-references:

- `docs/000_Pipeline_Overview.md` §3.8 — labeling runs the gates
  post-growth; this Step lands the gate functions, Step 07 wires the
  per-room check.
- `docs/000_Architecture_Decisions.md`:
  - **D001** — external contract (`run()` join is Step 07).
  - **D004** — 7-class `Role` + required-only cardinality (proto3:D023).
  - **D005** — solo-mode workflow (justifies branching).
  - **proto3:D020** — gates are fail-only; repair is a later Step.
  - **proto3:D023** — required-only summation (optional spaces don't count).
- `004_Step04_AlgorithmCore_Plan.md` §2 S04-D3 — target-agnostic growth
  (why `area_target_m2` has no consumer yet, the premise S05-D1 acts on).

---

## 1. Definition of Done

```text
Step 05 closes when:

1. schema/program.py — SpaceUnitSpec area fields realigned (S05-D1):
   - area_min_m2: required (default removed; the gate's primary input)
   - area_target_m2: float | None = None (demoted) + docstring naming it
     a diffusion-priority hook for a possible future area-aware growth
     pass (live field, not dead; no committed Step)
   - min_dimension_m: optional, unchanged (Step 07 per-room dim check)
   - __post_init__: MINIMAL value guards only (S05-D wart-min): area_min ≥ 0;
     area_target ≥ area_min when both set. No NaN/inf hardening (honest-fix).

2. schema/target.py (NEW) — TargetRules frozen dataclass:
   density_factor / min_cardinality[Role] / requires_single_floor.
   __post_init__ structural guards (density_factor > 0, counts ≥ 0).
   NO JSON loader, NO adapter (Step 06). Hand-constructed in tests.
   Re-exported from schema/__init__.

3. schema/failure.py — ProgramInstantiationFailure added (the rest of the
   DomainGateFailure hierarchy already landed in Step 02).

4. constraints/gates.py (NEW) — 4 pure gate functions, primitive injection,
   m units (proto3 was mm — unit swap is the port adjustment):
   - check_min_area(specs, *, footprint_area_m2, density_factor)
   - check_min_dim(specs, *, footprint_bbox_short_side_m)
   - check_multi_floor_feasibility(*, n_floors, requires_single_floor)
   - check_access_schema(...)  ← documented no-op stub (no AccessPolicy in
     current schema; activation = Step 09-10)
   each raises the matching DomainGateFailure subclass; returns None on pass.

5. stages/stage01_program.py (NEW) — required-only **cardinality** gate
   over one floor's list[SpaceUnitSpec]. Takes rules: TargetRules. Returns
   the list unchanged on success (S05-D5). No role-default fill (area_min
   required). Structural/cross-ref validation is NOT here — owned by
   __post_init__ + validate_input (S05-D8).

6. stages/stage02_gate.py (NEW) — fail-only orchestration: derives
   footprint area + bbox short side from a single FloorShape, calls the two
   FLOOR-scoped gates (check_min_area, check_min_dim) by unpacking rules.
   Returns the specs unchanged on accept. The building-level
   check_multi_floor_feasibility gate is hoisted to the Step 07 run()
   caller (S05-D6 — different altitude), not called here.

7. Tests: each gate unit-tested with inline primitives (pass + each fail
   branch); stage01/stage02 with small hand-built TargetRules;
   ProgramInstantiationFailure + DomainGateFailure round-trip through
   FailureRecord.

8. Golden regen: cell_fixtures_to_json.py drops the area_target heuristic
   (→ null) + area_min role-miss fallback; 33 input.json regenerated;
   region-id digest goldens verified unchanged.

9. Viz: NO new viz this Step — admission gates are a non-geometric layer.
   Gate pass/fail badges on the layout render are a Step 07 concern.

10. ruff clean; full pytest green under the canonical runtime
    (conda IfcOpenHouse, GEOS 3.14.1); Plan/Tracker closed; S05-D1..D7
    finalized; merge --no-ff to main (proto3:D015).
```

---

## 2. 결정 기록

Decisions locked during Step 05 planning (chat discussion 2026-05-30).
Predecessor decisions referenced as `S04-Dxx` / `proto3:Dxxx`.

| # | Topic | Decision |
|---|---|---|
| **S05-D1** | Area-field realignment | `SpaceUnitSpec`'s area fields get their first real consumer here, which exposed a mismatch: growth is target-agnostic (S04-D3) so `area_target_m2` is read by **nobody**, yet it was required while `area_min_m2` — the field the gates need — was optional. **Realign**: `area_min_m2` → required (gate primary input); `area_target_m2` → `float \| None = None`, **kept** (not dropped) and documented as a **diffusion-priority hook for a possible future area-aware growth pass** (which would weight expansion by it). No committed Step owns that pass yet — it may never land. Rationale for keeping over dropping (chat 2026-05-30): a "required-but-unused" field is a genuine wart, but the value plausibly returns as diffusion priority — `Optional` removes the wart while preserving the hook at near-zero churn. If the pass never materializes, the optional field costs nothing. The 33 goldens already carry valid `area_min_m2`, so the required promotion needs no data backfill — only the fixture generator's `area_target` placeholder (`footprint/num_rooms`, an honest fake) is dropped to `null`. |
| **S05-D2** | Step 05 ↔ Step 06 boundary | **Step 05 = gate machinery + rule *type*; Step 06 = rule *values + loading*.** Gates are pure functions taking primitive domain values by injection (leaf functions depend only on what they use — `check_min_area` takes `density_factor: float`, not a `rules` object). The `TargetRules` dataclass that groups those values is defined **now** (a type is defined where first needed; `stage01` is the first consumer), but only as a hand-constructable bundle. The JSON loader / `TargetAdapter` / multi-typology registry that *populates* `TargetRules` from `data/target_rules/<t>.json` is **Step 06**. This refines Pipeline §5.1's one-liner ("TargetRules carry to Step 06") into a type/value split. |
| **S05-D3** | `TargetRules` fields | Three fields only: `density_factor` (float, area-gate capacity), `min_cardinality` (`dict[Role, int]`, cardinality gate), `requires_single_floor` (bool, multi-floor gate). proto3's `default_min_area_m2` map is **omitted** — it existed for role-default fill, which S05-D1 eliminates (`area_min_m2` now required, nothing to fill). Fewer fields than proto3's `TargetRules`; Step 06 adds loading, not necessarily more fields (revisit if a real consumer appears). |
| **S05-D4** | Gate units & access stub | Gates ported from proto3 with **mm → m unit swap** (new schema is m: `area_min_m2`, `min_dimension_m`; proto3 was `min_dimension_mm`). All 4 gate *functions* land in `constraints/gates.py`; of these `stage02` wires the two floor-scoped ones (area + dim — see S05-D6 for why multi-floor is hoisted), and `check_access_schema` is a **documented no-op stub** (current schema has no `AccessPolicy` concept; activation Step 09-10 — honest-fix: stub over a speculative guard). |
| **S05-D5** | No `ProgramInstance` type | proto3 split `ProgramRequest` (input) → `ProgramInstance` (concretized output of fill). Our schema makes `area_min_m2` required, so Stage 01 has **nothing to concretize** — it gates and returns its input unchanged (option b). A separate `ProgramInstance` type would be an empty wrapper. Cluster / access separation, if ever needed, can introduce it then. **Note (per S05-D8):** the concrete signature is `run(specs: list[SpaceUnitSpec], *, rules) -> list[SpaceUnitSpec]` (one floor's specs in/out), not `ProgramRequest` in/out — the caller (Step 07 `run()`) extracts `floor_programs[level]`. |
| **S05-D6** | Stage 02 = floor-scoped gates only (area + dim) | Revised during 4.7 (chat 2026-06-02). `stage02` takes a single `FloorShape`, derives `footprint_area_m2` + bbox short side (shapely union of parts), and runs the **two floor-scoped** gates (`check_min_area`, `check_min_dim`). It is fail-only (proto3:D020) and returns the specs unchanged on accept. **`check_multi_floor_feasibility` is intentionally NOT called here** — it is a *building*-level check (is the whole building single-floor?), a different altitude from stage02's *floor*-level question (does this floor hold this program?). proto3 bundled it into stage02 only because it assumed `floors[0]`; we hoist it to the building-level caller (Step 07 `run()`), which is the natural owner of `n_floors`. The gate function already exists (4.5); only its call site moves. Keeps stage02's signature to one `FloorShape` (no `ShapeInput`/`n_floors` leakage). |
| **S05-D7** | Golden regen scope | The 33 `input.json` are regenerated (S05-D1 schema change: `area_target_m2` 25.0-placeholder → `null`). The **region-id digest goldens are asserted unchanged** — input *shape* changes but growth is target-agnostic so its output cannot move. This is the regression guard for S05-D1: if a digest golden shifts, the "target-agnostic" claim is false. Generator (`cell_fixtures_to_json.py`) also adds an `area_min` fallback for roles outside Cell's 4-role `role_min_areas` table (defensive; current goldens only use the 4 roles). |
| **S05-D8** | Stage 01 responsibility = cardinality only | Decided during 4.6 (chat 2026-06-02). proto3's Stage 01 bundled structural (empty/invalid id, role), duplicate-id, and cardinality checks. In this repo the first two are **already owned** by `SpaceUnitSpec.__post_init__` (Step 02 structural) and `validators.validate_input` (Step 02 cross-ref — duplicate id is checked **cross-floor** there, more correctly than a per-floor re-check). So `stage01_program.run(specs, *, rules)` owns **only** the rules-based required-only cardinality gate, and returns `specs` unchanged on pass (S05-D5). proto3 re-checked structure "to be callable in isolation"; dropped as YAGNI insurance — `run()` always calls `validate_input` first (honest-fix, single source of truth). Diverges from proto3 because proto3 lacked our separate Step 02 cross-ref layer. |

---

## 3. Directory structure (target state after Step 05)

Step 05 adds a new `constraints/` package + one schema module + two stage
modules. Flat `stages/` continues (S04-D6).

```text
src/room_layout/
  schema/
    program.py       # MODIFIED: area-field realignment (S05-D1)
    target.py        # NEW: TargetRules (S05-D3)
    failure.py       # MODIFIED: + ProgramInstantiationFailure (S05-D5 path)
    ...
  constraints/       # NEW package
    __init__.py
    gates.py         # NEW: 4 pure gate functions (S05-D4)
  stages/
    stage01_program.py   # NEW: cardinality gate (S05-D5 / S05-D8)
    stage02_gate.py      # NEW: fail-only gate orchestration (S05-D6)
    ...                  # (Step 03/04 modules unchanged)

scripts/
  cell_fixtures_to_json.py   # MODIFIED: area_target → null, area_min fallback

tests/
  test_schema_program.py     # MODIFIED: realigned fields
  test_schema_serialize.py   # MODIFIED: area_min=None case → area_target=None
  test_schema_target.py      # NEW
  test_constraints_gates.py  # NEW
  test_stages_stage01_program.py  # NEW
  test_stages_stage02_gate.py     # NEW
  golden/*/input.json        # REGENERATED (33)
```

---

## 4. Work items

Schema-foundation-first order (dependency-driven): schema reshape → pure
gates (fewest deps) → stages (gate consumers) → integration + regen last.
Mirrors into Tracker §1 (proto3:D016).

| # | Work item | Verify |
|---|---|---|
| **4.1** | Plan + Tracker land + `git mv` Step 04 docs → `legacy/step04/` + `docs/000_Progress_Tracker.md` stale-text cleanup (Step 04 merge already done) | docs review; working tree staged |
| **4.2** | `schema/program.py` area-field realignment (S05-D1) — `area_min_m2` required, `area_target_m2` optional + diffusion-priority docstring, minimal `__post_init__` guards; update `test_schema_program.py` / `test_schema_serialize.py` (goldens NOT touched yet — serialize tests carry inline values) | schema tests pass |
| **4.3** | `schema/target.py` (NEW) — `TargetRules` frozen dataclass + `__post_init__` guards (S05-D3) + `schema/__init__` re-export + `__all__`; `test_schema_target.py` (hand-built + serialize round-trip) | target tests pass |
| **4.4** | `schema/failure.py` — `ProgramInstantiationFailure` (S05-D5) + `test_schema_failure.py` extension (FailureRecord round-trip) | failure tests pass |
| **4.5** | `constraints/gates.py` (NEW) — 4 pure gates (S05-D4): area / dim / multi-floor active + access no-op stub; `test_constraints_gates.py` (inline primitives, pass + each fail branch) | gate tests pass |
| **4.6** | `stages/stage01_program.py` (NEW) — required-only cardinality gate over one floor's specs, returns them unchanged (S05-D5 / S05-D8); `test_stages_stage01_program.py` | stage01 tests pass |
| **4.7** | `stages/stage02_gate.py` (NEW) — footprint area/bbox from FloorShape + 3-gate fail-only orchestration (S05-D6); `test_stages_stage02_gate.py` | stage02 tests pass |
| **4.8** | Generator + golden regen (S05-D7) — `cell_fixtures_to_json.py` (`area_target` → null, `area_min` role-miss fallback); regenerate 33 `input.json`; **assert region-id digest goldens unchanged** | 33 inputs regen; digests stable; full pytest green |
| **4.9** | Step close — `docs/000_Progress_Tracker.md` (Step 05 closed) + Plan/Tracker close + S05-D1..D7 finalize + `git merge --no-ff step05-programlayer` → `main` | CI green; tracker updated |

---

## 5. 의도적으로 하지 않는 것 (out of scope)

| Item | Why deferred / where |
|---|---|
| TargetRules JSON loader / `TargetAdapter` / `data/target_rules/<t>.json` / multi-typology | **Step 06** (S05-D2 — values + loading). Step 05 ships the type only. |
| Per-room post-growth area/dim check (the 1.5 m² room rejection) | **Step 07** labeling (Pipeline §3.8). Step 05 lands the gate functions; Step 07 wires them per grown room. The `check_min_*` here are the **aggregate admission** gates (Σ required min ≤ capacity), not the per-room check. |
| `run()` join / `LabeledRoomLayout` assembly | **Step 07** (D001). |
| `check_access_schema` activation + `AccessPolicy` schema | **Step 09-10** (S05-D4 — no AccessPolicy concept yet). |
| Multi-floor area aggregation across floors | Deferred with the multi-floor outer loop (D001). `stage02` is single-floor (S05-D6). |
| `check_multi_floor_feasibility` **call site** (the gate function ships in 4.5) | **Step 07** `run()` — building-level altitude owns `n_floors` (S05-D6). The function is built + unit-tested here; only its invocation is hoisted. |
| Area-aware growth (consuming `area_target_m2` as diffusion priority) | Possible future pass, **no committed Step** (S05-D1 — the hook the demoted field reserves; may never land). |
| `usage` field population / propagation | Currently null in all goldens; Step 07 labeling concern. |

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| Required-promotion of `area_min_m2` silently breaks a golden input missing the field | Scanned (chat 2026-05-30): all 33 inputs already carry valid `area_min_m2`. serialize's missing-required-field reject (serialize.py) makes any gap fail loud, not silent. |
| Golden regen accidentally shifts a region-id digest (would mean growth is NOT target-agnostic) | 4.8 asserts digests unchanged as an explicit regression guard. A shift fails the Step, surfacing a false S04-D3 premise rather than hiding it. |
| Gate unit confusion (proto3 mm vs new m) ports a wrong threshold | S05-D4 unit swap is explicit; gate tests use m-unit inline values matched to footprint m² (no mm anywhere in the new gates). |
| Aggregate-gate vs per-room-check conflation (reviewer expects 1.5 m² rejection here) | §5 + S05-D6 state explicitly that Step 05 is **admission** (pre-growth, aggregate); per-room rejection is Step 07. |

---

## 7. Next-Step linkage

Step 05 delivers the program-layer half. The two pipeline halves
(03→04 geometry, 05→06 program) are parallelizable (Pipeline §5.3) and
**join at Step 07**:

- **Step 06** (Target rules) consumes `schema/target.py`'s `TargetRules`
  type and adds the JSON loader + adapter + per-typology rule files —
  turning hand-built test literals into production-loaded rules.
- **Step 07** (`run()` + labeling) is where: `stage01`/`stage02` run as the
  program-side entry; the gate functions get a **second binding** as the
  per-room post-growth check; `vertical_circulation` anchor rooms re-insert
  (S04-D4 deferred); `corridor` regions polygonize; the `CorridoredLayout`
  becomes a `LabeledRoomLayout`. The Step-04-deferred anchor/connectivity
  cluster lands here too.
