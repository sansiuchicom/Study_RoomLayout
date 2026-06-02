# 006 Step 06 — Target Rules System Plan

Status: Completed (on `main`, no merge needed — D005 solo-mode)
Type: Step plan
Branch: `main` (D005 — triggers weak: mostly NEW files; no golden regen; the
only touch to shipped code is a non-breaking `TargetRules` field add)
Last updated: 2026-06-02

---

## 0. Purpose

Step 06 builds the **value + loading half** of the target-rules system —
the other side of the S05-D2 boundary:

> Step 05 = gate machinery + rule *type* (`TargetRules`);
> **Step 06 = rule *values + loading*** (JSON + adapter + caller helper).

Step 05 defined `TargetRules` as a hand-constructed type with no source.
Step 06 makes it real: a per-typology JSON file (`apartment.json`), a strict
loader, a single generic `TargetAdapter`, and an `expand_program()` helper
that turns a simple `{role: count}` request into a full `ProgramRequest`.

The guiding split (proto3:D022): **typology identity lives in data (JSON),
not in code.** One generic `TargetAdapter` drives every typology; adding a
new one is a JSON file, not a subclass. Ported faithfully from proto3's
`target/` package, with two reconciliations forced by Step 05 decisions
(see §2): `default_min_area_m2` returns to `TargetRules` but as the
**expand-program seed** (not a stage01 fill — S05-D1 stands), and the schema
is ours (`ShapeInput`/`ProgramRequest`, not proto3 `BuildingInput`).

This Step is non-geometric (like Step 05) — no new viz. It does not wire
`run()` (Step 07) and consumes no growth/corridor output.

Cross-references:

- `docs/000_Pipeline_Overview.md` §5.1 (Step 06 DoD), §2.2 (`expand_program`
  outside `run()`), §4.2 (Target term).
- `docs/000_Architecture_Decisions.md`:
  - **D001** — `role` (algorithm) / `usage` (human pass-through) split; the
    role↔usage decision this Step refines (S06-D3).
  - **D004** — 7-class `Role` (the `min_cardinality` / `default_min_area_m2`
    key space).
  - **D005** — solo-mode workflow (justifies staying on `main`).
  - **proto3:D021** — `TargetRules` + external JSON config (Carry).
  - **proto3:D022** — single generic `TargetAdapter` + 3-layer extensibility
    (Carry).
- `legacy/step05/005_Step05_ProgramLayer_Plan.md` §2 — S05-D1 (area-field
  realignment; why `default_min_area_m2` was removed) / S05-D2 (the boundary
  this Step completes) / S05-D3 (`TargetRules` 3-field starting point).

---

## 1. Definition of Done

```text
Step 06 closes when:

1. schema/target.py — TargetRules gains default_min_area_m2: dict[Role, float]
   (S06-D1). Semantics: per-typology standard floor area per role — the
   SOURCE expand_program reads to fill SpaceUnitSpec.area_min_m2. NOT a
   stage01 fill fallback (S05-D1 stands — stage01 still never fills). Loader
   validates it as a full Role-keyed map.

2. target/rules_loader.py (NEW) — load_target_rules(path) -> TargetRules.
   Strict validation: required keys / types / Role keys / density_factor in
   (0,1] / non-negative cardinality / finite numbers (NaN/inf rejected at
   THIS JSON boundary — the honest place; resolves the S05 review #7 defer,
   S06-D4). Ported from proto3 + default_min_area_m2 kept.

3. target/adapter.py (NEW) — TargetAdapter(rules_path): single generic class,
   NO per-typology subclasses (proto3:D022 / S06-D5). Validates at
   construction (via loader), exposes target_rules() + target_type. Adapted
   to our schema (no proto3 BuildingInput.load_fixture coupling).

4. data/target_rules/apartment.json (NEW) — real apartment values:
   density_factor, requires_single_floor, min_cardinality,
   default_min_area_m2 (full Role map).

5. data/target_rules/README.md (NEW) — 3-layer extensibility model
   (L0 engine / L1 JSON params / L2 future strategy) ported from proto3.

6. target/expand_program.py (NEW, fresh design — no proto3 original) —
   expand_program(counts: dict[Role,int], target_type, *, rules, level=1)
   -> ProgramRequest:
   - {role: count} → SpaceUnitSpec list
   - id = f"{role}_{i}" (1-based per role)
   - area_min_m2 = rules.default_min_area_m2[role]  (S06-D1)
   - area_target_m2 = None  (S06-D2 — meaning left open until a consumer)
   - usage = None  (S06-D3 — no role↔usage auto-mapping; usage is set by the
     user/caller at labeling/BIM, never guessed from role)
   - required = True

7. pyproject — package-data so data/target_rules/*.json + README ship in
   wheel/sdist (proto3 precedent; adapter's default path must resolve from
   an installed package).

8. Tests: loader (each reject branch) + adapter + expand_program +
   apartment.json loads cleanly + expand_program output passes
   stage01_program (cardinality) and stage02_gate (area/dim).

9. Viz: NO new viz (non-geometric, like Step 05).

10. ruff (BOTH `check` AND `format --check`) + full pytest green (conda
    IfcOpenHouse, GEOS 3.14.1); Plan/Tracker closed; S06-D1..D6 finalized.
```

---

## 2. 결정 기록

Decisions locked during Step 06 planning (chat discussion 2026-06-02).
Predecessor decisions referenced as `S05-Dxx` / `proto3:Dxxx`.

| # | Topic | Decision |
|---|---|---|
| **S06-D1** | `area_min` owner = typology | `area_min_m2` is a **building-standard floor** ("how small can a `private` room be and still be usable"), which is domain knowledge the typology owns — not something a caller specifies per call. So `TargetRules` regains `default_min_area_m2: dict[Role, float]` (a full Role map), and `expand_program` reads it to fill each `SpaceUnitSpec.area_min_m2`. This does **not** reopen S05-D1: stage01 still never fills (a directly-built `SpaceUnitSpec` must supply `area_min_m2`, which is required). The map's consumer is `expand_program` (a seed for fresh specs), not a None-fallback in stage01. Symmetric with `min_cardinality` / `density_factor` already on `TargetRules` — all per-typology domain constants. |
| **S06-D2** | `area_target` meaning stays open | `expand_program` sets `area_target_m2 = None`. Tempting to define it now as "user's per-room preferred size", but it has **no consumer** (growth is target-agnostic, S04-D3; gates read only `area_min`). Fixing a meaning with no consumer risks being wrong when the real consumer (a future area-aware growth pass) arrives. Keep the Step 05 stance: optional hook, meaning deferred to whoever first reads it. expand simply leaves it unset. |
| **S06-D3** | No role↔usage auto-mapping | `expand_program` sets `usage = None`. The `usage` field stays (it is the D001 human-label / BIM-output slot on both `SpaceUnitSpec` and `LabeledRoom` — needed downstream). But there is **no automatic role→usage guess** (e.g. `private`→`"bedroom"`): it doesn't affect layout (algorithm reads only `role`), it is frequently wrong (a `private` room may be a study), and for BIM a guessed label is actively harmful (IFC needs accurate space names). usage is set by the user/caller at labeling/BIM time, never inferred. D001's "role↔usage mapping lives in target_rules JSON" is a *location reservation*, not a mandate to build auto-mapping now; revised here. (Diverges from the Pipeline §5.1 DoD line "Role↔usage mapping table lands here" — that line is corrected at this kickoff.) |
| **S06-D4** | finite checks at the JSON boundary | NaN/inf guards live in `rules_loader` (the external JSON input edge), not in the `TargetRules`/`SpaceUnitSpec` dataclasses. This resolves the Step 05 review #7 NaN-bypass defer at the honest place: a hand-built dataclass is a trusted code path (honest-fix, no speculative dataclass hardening — S05-D1 spirit), but a JSON file is untrusted external input and must fail loud. proto3's loader already did this (`_is_finite_number`); ported. |
| **S06-D5** | single generic `TargetAdapter` | One concrete `TargetAdapter(rules_path)` class for all typologies; no `ApartmentAdapter`/`HotelAdapter` subclasses (proto3:D022). Typology identity is the JSON `target_type` field. Adding a typology = a JSON file (+ a default-path registry entry when one exists). proto3's `load_fixture` is **not** ported (4.4 option 가) — this repo splits input into `ShapeInput` + `ProgramRequest`, no combined fixture object; the adapter is a pure validated-rules provider (`__init__(rules_path)` + `target_rules()`). Algorithm variants, if ever needed, become L2 strategy plugins (3-layer model, README) — typology-agnostic, not adapter subclasses. Not built now (YAGNI). |
| **S06-D6** | No `target_type` on `TargetRules` / adapter | Decided during 4.4 (chat 2026-06-02). proto3 mirrored `target_type` onto `TargetRules` so `load_fixture` could match a fixture's declared typology. We drop both `load_fixture` (S06-D5) and the field: **nothing downstream reads `target_type` to branch** — `ProgramRequest.target_type` is validated only as a Literal (`program.py`), never matched against rules; the gates ignore it. A "rules-vs-requested typology" cross-check would guard a non-existent v1 risk (a mismatched label yields a correct layout, just a wrong tag) → speculative, dropped (honest-fix). `expand_program` stamps the caller's `target_type` straight onto the `ProgramRequest` (info not lost); a real consumer can add the field + check when one appears. Keeps 4.2's `TargetRules` untouched (no schema churn). |

---

## 3. Directory structure (target state after Step 06)

```text
src/room_layout/
  schema/
    target.py        # MODIFIED: + default_min_area_m2 (S06-D1)
  target/            # NEW package
    __init__.py      # re-export load_target_rules / TargetAdapter / expand_program
    rules_loader.py  # NEW: load_target_rules + strict validation (S06-D4)
    adapter.py       # NEW: TargetAdapter single generic class (S06-D5)
    expand_program.py# NEW: {role: count} → ProgramRequest (S06-D1/D2/D3)
  data/
    target_rules/    # NEW
      apartment.json # NEW: real apartment values
      README.md      # NEW: 3-layer extensibility model

pyproject.toml       # MODIFIED: package-data ships data/target_rules/*

tests/
  test_schema_target.py        # MODIFIED: default_min_area_m2
  test_target_rules_loader.py  # NEW
  test_target_adapter.py       # NEW
  test_target_expand_program.py# NEW
```

Note: `target/` (the rules system) is a sibling of `stages/` (the pipeline),
matching proto3's `target/` vs `stages/` split — rules are config, not a
pipeline stage.

---

## 4. Work items

Foundation-first (dependency order): schema → loader → adapter → data →
expand → packaging. Mirrors into Tracker §1 (proto3:D016).

| # | Work item | Verify |
|---|---|---|
| **4.1** | Kickoff — Plan + Tracker land + `git mv` Step 05 docs → `legacy/step05/` + canonical fixes (Pipeline §5.1 DoD: drop "Role↔usage mapping table" + "anchor host_role slot"; Arch Decisions L90-91: role↔usage = location reservation, not auto-guess) + Progress Tracker | docs review; tree staged |
| **4.2** | `schema/target.py` — add `default_min_area_m2: dict[Role, float]` (S06-D1) + `__post_init__` guard (full Role map? non-negative) + `test_schema_target.py` update | target tests pass |
| **4.3** | `target/rules_loader.py` (NEW) — `load_target_rules` + strict validation (S06-D4: keys/types/Role/density (0,1]/cardinality≥0/finite) + `test_target_rules_loader.py` (each reject branch) | loader tests pass |
| **4.4** | `target/adapter.py` (NEW) — `TargetAdapter` single generic (S06-D5) + `target/__init__` exports + `test_target_adapter.py` | adapter tests pass |
| **4.5** | `data/target_rules/apartment.json` + `README.md` (NEW) — real values + 3-layer model; assert it loads via 4.3 | apartment.json loads clean |
| **4.6** | `target/expand_program.py` (NEW) — `expand_program` (S06-D1/D2/D3) + `test_target_expand_program.py` (incl. output passes stage01 + stage02) | expand tests pass |
| **4.7** | `pyproject.toml` package-data — ship `data/target_rules/*` in wheel/sdist; verify the adapter default path resolves | build includes data |
| **4.8** | Close — Plan/Tracker close + `docs/000_Progress_Tracker.md` + S06-D1..D6 finalize (on `main`, D005) | CI green; tracker updated |

---

## 5. 의도적으로 하지 않는 것 (out of scope)

| Item | Why / where |
|---|---|
| `run(shape, program, *, seed)` entry point | **Step 07** (D001). Step 06 ships `expand_program` (a program *builder*), not the pipeline driver. |
| role↔usage **auto-mapping** (`private`→`"bedroom"` etc.) | **Not built** (S06-D3). `usage` is user/caller-set at labeling/BIM; never guessed. The `usage` field itself stays (D001 output slot). |
| `area_target_m2` meaning / consumer | Deferred (S06-D2). expand sets `None`; a future area-aware growth pass defines it (no committed Step). |
| anchor / `host_role` wiring | **Not a Step 06 concern.** The schema (`VerticalAnchor.host_role` + `_KIND_TO_HOST_ROLE`) landed in **Step 02**; its *use* (fixed-room re-insertion) is **Step 07** (S04-D4). proto3's target system never referenced anchors. The Pipeline §5.1 DoD "anchor host_role slot wired" line is removed at this kickoff. |
| Typologies beyond apartment (house/hotel/office/warehouse JSON) | Out of scope — apartment is the v1 typology. New ones are data-only adds (S06-D5) when scoped. |
| L2 strategy plugin registry | Future (proto3:D022 / README 3-layer) — introduced when a typology needs a genuinely different algorithm variant. |
| External-pipeline rules override channel (partial-merge) | Future (proto3 Plan Def-1) — when a scan-to-BIM pipeline integration is scoped. |

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| `default_min_area_m2` re-add read as reopening S05-D1 (role-default fill) | S06-D1 is explicit: the map's consumer is `expand_program` (seeds fresh specs), NOT stage01 (which still never fills). Doc + a test that stage01 on a directly-built spec with no fill still behaves as Step 05. |
| `expand_program` output silently fails the gates it should pass | 4.6 verifies expand output round-trips through `stage01_program` + `stage02_gate` on a real footprint — the builder must produce admissible programs. |
| package-data path doesn't resolve once installed | 4.7 verifies the adapter default path loads from the installed package (proto3 hit this; `[tool.setuptools.package-data]`). |
| Canonical-doc drift (DoD lines now contradict S06-D3 + anchor finding) | Fixed AT kickoff (4.1), not deferred — Pipeline §5.1 + Arch L90-91 corrected in the same commit. |

---

## 7. Next-Step linkage

Step 06 completes the program/target half. **Step 07** (`run()` + labeling)
is the join, where: `expand_program` / `stage01` / `stage02` become the
program-side entry; the growth/corridor half (Step 03/04) meets it; `usage`
gets set on output rooms; `check_multi_floor_feasibility` gets its call site;
and the Step-04-deferred anchor/connectivity cluster (incl. `host_role`
fixed-room re-insertion) lands.
