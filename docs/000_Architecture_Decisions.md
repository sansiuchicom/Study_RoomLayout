# 000 Architecture Decisions

Status: Canonical decision record
Scope: accepted decisions for `Study_RoomLayout`, invariant vs replaceable choices, and the inherited-decision audit from the two predecessor repos
Last updated: 2026-05-24

---

## 0. Purpose

This document records accepted decisions for `Study_RoomLayout`.

Use this file to answer:

- What has already been decided?
- What is an architecture invariant?
- What is only a first-pass implementation choice?
- Why was the decision made?
- What should be changed only with deliberate review?

Canonical framework and pipeline definitions live in `000_Pipeline_Overview.md`.
Current implementation status lives in `000_Progress_Tracker.md`.

---

# 1. Decision status labels

| Status | Meaning |
|---|---|
| **Accepted** | Current working decision. Use unless explicitly revised. |
| **Replaceable** | Current first-pass choice, but not a framework invariant. |
| **Deferred** | Known issue or future decision, not required immediately. |
| **Rejected** | Decision considered and intentionally not used. |

---

# 2. Architecture invariants vs replaceable choices

To be defined as decisions land. Predecessor invariants (proto3 D006 / D007 / D011)
are explicitly under audit — see §4.

---

# 3. Accepted decisions

## D001 — External contract: pure-function `run(shape, program, *, seed) -> LabeledRoomLayout`

Status: Accepted
Type: Architecture invariant
Date: 2026-05-24

Decision:

The single entry point is a pure function:

```python
def run(shape: ShapeInput, program: ProgramRequest, *, seed: int) -> LabeledRoomLayout
```

Full type sketches live in `000_Pipeline_Overview.md` §2. This decision
fixes the *shape* of the contract; field-level refinement is allowed
during implementation.

Sub-choices recorded here (each replaces or extends `proto3:D003` /
`proto3:D012` / `proto3:D018`):

- **`ShapeInput` is a list of floors with anchor list** (option A-1 in
  the C-series review). No discriminated `SingleFloor | MultiFloor`
  union — single-floor case is `len(floors) == 1` + empty anchors.
  Carries `proto3:D003`'s "floor-rooted from start" intent into the new
  repo without committing to multi-floor algorithm work in v1.
- **Footprint parts are preserved, never unioned at the input
  boundary.** Each `FloorShape` carries `list[ShapePart]` exactly as the
  caller (PlanBIM Stage 1 massing or test fixture) authored them — a
  main rect plus rotated wings, mirror extensions, curved cuts, etc.
  The union is computed downstream when needed and is **not** the
  canonical input form. This lets the algorithm read each part's
  orientation directly from its exterior edges (Cell `part_theta()`
  helper) instead of running a detection heuristic on a unioned polygon.
  Reversing this decision would break Cell Phase 3 (`atomize`) and
  Phase 5 (`regionize`), both of which iterate parts per-orientation.
- **`ProgramRequest` is floor-scoped** (option B-2). `floor_programs:
  dict[int, list[SpaceUnitSpec]]` lets multi-floor typologies (house,
  hotel) express per-floor program rules without orchestrator
  workarounds. Single-floor v1 uses one dict entry.
- **`SpaceUnitSpec` carries `role` (required) and `usage` (optional,
  pass-through)** (option D in the C3 review, with sub-options a1
  free-form `usage: str` and b2 `expand_program()` helper external to
  the core entry point). Algorithm reads `role`; `usage` is carried
  through to `LabeledRoom.usage` untouched. Typology-specific role↔usage
  mapping lives in `target_rules/<typology>.json` (`proto3:D021`).
- **Hybrid γ adapter pattern**. Core stays pure-function and
  typology- / external-pipeline-agnostic. ResearchBIM `Building` /
  `Storey` mutation integration lives in `adapters/researchbim.py`,
  not in v1 scope.
- **Output is unified `LabeledRoomLayout(valid: bool, ...)`** carrying
  the `proto3:D018` principle. Field set differs from the proto3
  sketch — see Pipeline §2.3.

Reason:

- Multi-floor *schema reach* from day one is cheap (list of length 1).
  Designing schema as single-floor and retrofitting multi-floor later
  would force a breaking change.
- Floor-scoped program avoids "which floor does this bedroom go on?"
  orchestrator guesswork — the caller already has typology context.
- `role` / `usage` split lets the core algorithm stay typology-agnostic
  (`proto3:D022` spirit) while still producing output the downstream
  IFC / facade / MEP stages can use directly.
- Hybrid γ keeps the core decoupled from ResearchBIM's evolving data
  model. Adapter is cheap to add when the integration is scoped.

---

## D002 — Seed-first room growth with corridor carving (replaces spine-first)

Status: Accepted
Type: Architecture invariant
Date: 2026-05-24
Replaces: `proto3:D007` (spine-first), `proto3:D011` (access-preserving growth)

Decision:

The internal pipeline is:

```text
ShapeInput
  → atomize          (per-territory cells, 50% merge rule — Cell Phase 3)
  → atom_graph                                             (Cell Phase 4)
  → regionize        (~3 m² hierarchical atom clusters — Cell Phase 5)
  → region_graph                                           (Cell Phase 6)
  → region partition growth   (seed-first room growth — Cell Phase 7)
  → corridor carving (Stage 1 hub-radial A* + Stage 2 detour — Cell Phase 8)
  → labeling         (role assignment, validation)
  → LabeledRoomLayout
```

Access is **not preserved during growth**. Growth fills the floor from
seed rooms greedily; the corridor carving pass restores connectivity
afterward. Hub seed = corridor carving root.

Vocabulary drop:

- `hub` survives as a Role (carving root) but **not as a pre-growth
  hypothesis layer**.
- `spine` / `trunk` / `branch` / `stub spine` / `branch slot` — all
  dropped. Not part of this repo's vocabulary.

Reason:

- `archive/celllayout/` Phase 1–8 produced apartment-grade layouts
  under this model across 6 apartment fixtures. The seed-first model
  is the validated path; spine-first was never implemented past
  proto3 Stage 02.
- Post-hoc corridor carving is conceptually simpler than pre-growth
  spine hypothesis generation and aligns with the way ResearchBIM
  Stage 4 thinks about Core / circulation (Core placed first, room BSP
  fills the rest).

First-pass implementation: as shipped in `archive/celllayout/algorithm/
celllayout_tf/`. Replaceable in principle; not a framework invariant
beyond "seed-first growth + post-hoc carving."

---

## D003 — Triple-layer geometry: atom / region / room (replaces dual-layer)

Status: Accepted
Type: Architecture invariant
Date: 2026-05-24
Replaces: `proto3:D006` (region / atom dual layer; region = architectural territory)

Decision:

Geometric primitives form three layers:

| Layer | Typical size | Role |
|---|---:|---|
| `atom` | ~0.3 m² | finest geometric primitive (Cell Phase 3) |
| `region` | ~3 m² | atom cluster, **purely geometric** (Cell Phase 5) |
| `room` | variable | architectural role assigned (Cell Phase 7+) |

Architectural role (`public` / `private` / ...) lives on the **room**
layer. The region layer is geometric only — it has no `kind` field, no
role hint, no architectural meaning.

Compared to `proto3:D006`:

- proto3 `Region` (carrying role candidates like `public-candidate`) ≈
  new repo's **`Room`** layer.
- proto3 `Atom` ≈ new repo's `Atom` (semantically the same; numerical
  defaults come from Cell `DimensionPolicy`, not `proto3:D019`).
- The new `Region` layer (~3 m² geometric cluster) is a layer
  **proto3 did not have**.

Reason:

- Cell Phase 5 (`regionize`) demonstrated the value of an intermediate
  geometric cluster layer: it enables hierarchical slab-cutting
  (T1a / T1b / T2 / T3) and stable seeding for growth (Phase 7), neither
  of which a region-only or atom-only model produced cleanly in proto3.
- Separating "geometric clustering" from "architectural meaning" makes
  both layers replaceable in isolation: a future repartition algorithm
  can change region semantics without touching role assignment, and a
  future role assignment scheme can change without touching the
  partition.

Numerical defaults (carried from Cell `DimensionPolicy`):

- `geometry_snap = 0.01` m
- `module_quantum = 0.05` m
- `target_atom_size = 0.3` m (per-side)

`proto3:D019`'s mm-based per-family proportional sizing parameters do
not apply.

---

## D004 — v1 Role taxonomy: 7-class functional roles

Status: Accepted
Type: Architecture decision
Date: 2026-05-24

Decision:

```python
Role = Literal[
    "public", "private", "service", "wet",
    "hub", "corridor", "vertical_circulation",
]
```

`Role` is a *functional class* driving algorithm behavior (growth
priority, adjacency rules, anchor binding). Concrete room types
(`"living"`, `"bedroom"`, `"guestroom"`, ...) live on the `usage`
field, not on `Role`. The 6-class subset (excluding
`vertical_circulation`) was validated through `archive/celllayout/`
Phase 1–8 fixtures; `vertical_circulation` is added at v1 inception so
the schema vocabulary is locked before multi-floor work begins.

| Role | Description | Algorithm behavior |
|---|---|---|
| `public` | living / lobby / large gathering | large area target; exterior preferred; central position |
| `private` | bedroom / study | small–medium area; peripheral position OK |
| `service` | kitchen / utility / mechanical | medium area; plumbing + ventilation; prefers `public` adjacency |
| `wet` | bathroom / laundry | small area; full water tolerance; PS-shaft adjacency preferred |
| `hub` | entry / foyer | corridor carving root (Phase 8 hub-radial A* seed) |
| `corridor` | circulation | **output** of corridor carving; not pre-seeded |
| `vertical_circulation` | stair landing / elevator door | **anchor-locked room** — polygon fixed by linked `VerticalAnchor`, not grown |

**Anchor binding**. `vertical_circulation` rooms are 1:1 linked to a
`VerticalAnchor` via `SpaceUnitSpec.anchor_id` /
`LabeledRoom.anchor_id`. Their polygon is determined by the anchor's
`footprint_polygon` — algorithm growth treats the polygon as a
forbidden region; the room itself is emitted as a fixed polygon in the
output.

**Anchors without a room**. `VerticalAnchor` instances with
`host_role = None` (`ps_shaft`, `eps_shaft`, `duct_shaft`) are
forbidden regions only — no `LabeledRoom` is emitted for them.

**Deferred role candidates**:

| Candidate | Status | Activation trigger | v1 absorption |
|---|---|---|---|
| `storage` | Deferred | only if `private` growth rejects very-small rooms (closet / pantry / mechanical) | use `role="private"` + small `area_target_m2` + `usage="closet"` |
| `outdoor` | **Permanently excluded** | never | balcony / terrace expressed via `ShapePart` metadata or footprint subtraction (Stage 1 massing responsibility), not as a `LabeledRoom` |

Reason:

- `vertical_circulation` is added at v1 inception (despite multi-floor
  algorithm being deferred per D001) because the touch points —
  `Role` Literal, `target_rules/*.json`, `anchor.host_role`,
  `SpaceUnitSpec.anchor_id`, `LabeledRoom.anchor_id` — ripple across
  the codebase. Landing them once now is cheaper than retrofitting
  them later when multi-floor lands.
- `storage` is held back because Cell Phase 1–8 has not exercised
  very-small (≲ 1 m²) rooms. If `private` defaults reject them, a
  dedicated role is added; otherwise the lighter absorption suffices.
- `outdoor` is excluded because the algorithm grows rooms *inside the
  footprint*. Outdoor space sits on the footprint boundary or outside
  it, which is a Stage 1 (massing) concern, not Stage 4 (room layout).

---

## D005 — Solo-mode workflow: default to main, branch only on size / risk triggers

Status: Accepted
Type: Repo / VCS convention
Date: 2026-05-25
Amends: `proto3:D015` (per-Step branch + per-work-item commit + no-squash merge)

Decision:

`proto3:D015`'s per-Step-branch requirement is **demoted to a
guideline** for this repo's solo-work context. Default behavior is to
work directly on `main` with atomic commits. Branch only when the Step
meets at least one of these triggers:

| Trigger | Reason |
|---|---|
| Expected commit count > 5 | Limits work-in-progress noise on `main` |
| Regression risk (changes existing validated behavior) | Easy rollback via branch deletion if a port goes wrong |
| Integration work (joins multiple module areas) | Mid-Step pivots are more likely; isolation reduces blast radius |
| Mid-Step design pivot plausible | Same |

The remaining `proto3:D015` provisions **carry unchanged**:

- **Per-work-item commit**: each Plan §4 work item is its own commit,
  regardless of where it lands.
- **No-squash merge**: when a Step *does* branch, `git merge --no-ff`
  preserves the commit cluster.
- **Commit message prefix style** (`feat:` / `fix:` / `refactor:` /
  `docs:` / `chore:`).

`proto3:D016` (per-Step Plan + Tracker companion docs) is **unchanged
and unconditional** — Plan / Tracker apply regardless of branching
choice. The amendment is solely about branch policy.

Step 01 (Project skeleton) is the first application of this decision —
none of the four triggers fire (scaffold work, no regression risk,
single-module scope, no design pivot expected), so Step 01 proceeds on
`main`.

Per-Step branch / no-branch choice is recorded in each Step's Plan §2
(decision table) as a per-Step decision (`S0N-D…`), citing the trigger
that fired or noting that none did.

Reason:

- The chief value `proto3:D015` extracted — *reviewable merge commit
  clusters per Step* — depends on PR review. Solo work has no PR
  review, so this value is weaker.
- The remaining values (WIP isolation, easy rollback, plan↔commit
  mapping) still apply, but only when the Step is large or risky
  enough that they're worth the overhead. The four triggers above
  identify those Steps.
- proto3 itself made Step 01 an exception to D015 (precedent for
  on-main Step 01). This decision generalizes the principle:
  proto3:D015 was correct for a multi-developer or reviewed-work
  context; for solo work it is overhead-dominant on small Steps.

---

## D006 — Output directory convention

Status: Accepted
Type: Cross-cutting / repo convention
Date: 2026-05-25
Carries: `proto3:D014` (debug outputs out of version control)

Decision:

Three categories of generated output, each with a dedicated location:

| Category | Location | Committed? | Lifetime |
|---|---|---|---|
| Test golden artifacts | `tests/golden/<fixture_name>/` | ✅ Yes | versioned with code (regression contract) |
| Per-run debug artifacts | `outputs/debug_runs/<run_id>/` | ❌ No (`proto3:D014` carry) | per-run, ephemeral |
| One-off viz / reports | `outputs/viz/` | ❌ No | ephemeral |
| Experimental / exploratory | `experiments/notebooks/` (jupyter) or `experiments/runs/` (CLI sandbox) | ❌ No | ephemeral |

The `outputs/`, `experiments/`, and `tests/golden/` parent directories
exist as `.gitkeep` placeholders from Step 01. Subdirectories within
them are created at runtime by the producing code.

### Per-stage layout within `outputs/debug_runs/<run_id>/`

Each stage's output is persisted as `NN_<stage_id>.{json,png}`, where
`NN` is the stage index (two-digit, zero-padded). Lexicographic sort
then equals pipeline order. The final layout and the composite
animation land at the run root:

```text
outputs/debug_runs/seed42_2026-05-25T14-30-00/
├── manifest.json                  # run metadata (see below)
├── 00_input.json                  # ShapeInput + ProgramRequest serialized
├── 01_atomize.json
├── 01_atomize.png
├── 02_atom_graph.json
├── 02_atom_graph.png
├── 03_regionize.json
├── 03_regionize.png
├── 04_region_graph.json
├── 04_region_graph.png
├── 05_growth.json
├── 05_growth.png
├── 06_corridors.json
├── 06_corridors.png
├── 07_labeling.json
├── 07_labeling.png
├── final.json                     # LabeledRoomLayout serialized
├── final.png                      # canonical final viz
└── pipeline.gif                   # 01–07 PNGs composed as GIF frames
```

### `manifest.json` schema

```json
{
  "seed": 42,
  "fixture_name": "apt_06_2bed",
  "git_commit": "1afc368",
  "config": {},
  "started_at": "2026-05-25T14:30:00Z",
  "ended_at":   "2026-05-25T14:30:03Z",
  "duration_ms": 3142,
  "package_version": "0.1.0"
}
```

Field notes:

- `fixture_name`: nullable — `null` when input is an ad-hoc (non-fixture) shape.
- `git_commit`: nullable — `null` when the working tree is dirty or git
  state cannot be read.
- `config`: serialized `RunConfig` (Step 07 type; empty `{}` until then).
- All other fields are required and non-null.

The folder name (`<run_id>`) is kept short and sortable; the manifest
inside carries the full context. Anyone investigating a debug run can
trace back to the exact commit, seed, and config from `manifest.json`
without parsing the folder name.

### Run ID format

- **Default**: `seed<N>_<isoformat-utc-no-colons>` — e.g.,
  `seed42_2026-05-25T14-30-00`. Sorts chronologically; same code +
  same seed re-run produces a *new* folder (preserves history for
  diff).
- **Caller override**: `run_id: str | None = None` keyword on the
  debug-run CLI helper. When set, replaces the default folder name
  (useful for presentation snapshots or comparison demos).
- **Test golden** uses a different naming scheme — golden directories
  are named by fixture (`tests/golden/<fixture_name>/`) and contain the
  same stage-file layout, but with a minimal `manifest.json` pinning
  the expected `package_version` instead of run timing data. Golden
  files are *part of the spec*, not per-run trace.

### Implementation lands later

- **Step 07 (entry point + labeling)** — implements the `on_stage`
  callback hook, `StageOutput` dataclass, JSON serializers, and the
  `manifest.json` writer.
- **Step 08 (SVG viz)** — canonical PNG/SVG renderer per stage plus
  `make_gif()` composition helper. Adds `pillow` or `imageio` to the
  `viz` extra dep.
- **Step 03 (geometry port)** — brings Cell's matplotlib renderers as
  the development-bridge viz path until Step 08 ships canonical SVG.

Reason:

- `proto3:D014` says "debug outputs stay out of version control" but
  does not say *where they go*. This decision fills the gap with an
  explicit taxonomy so each output-producing Step knows the destination.
- Separating `tests/golden/` (committed regression contract) from
  `outputs/` (gitignored trace data) prevents accidental commits of
  per-run noise and accidental gitignore of golden tests.
- The `NN_<stage_id>` prefix makes a lexicographic file listing into
  a pipeline timeline — any debugger or viz tool just sorts files.
- `manifest.json` keeps folder names short while preserving full
  reproducibility context (commit, seed, config, timing).
- Per-stage outputs share their format between regression golden tests
  and `pipeline.gif` frames — single source of truth for "what each
  stage produced."

---

# 4. Inherited-decision audit (proto3 D001–D023)

The proto3 D-series is the framework decision record for the `archive/proto3/`
repo. Each decision is audited here for whether it carries into
`Study_RoomLayout`.

**Namespace**: this document's D-series (D001, D002, ...) is the new repo's
own namespace, restarted at D001. Proto3 decisions are referenced as
`proto3:DXXX`. Carryover decisions get new D numbers when §3 is populated.

**Verdict labels**:

- **Carry** — adopt as-is; the rationale survives unchanged.
- **Modify** — adopt with revisions; rationale partially survives. §4.2 lists the change.
- **Drop** — explicitly retire; rationale no longer applies. §4.2 lists what replaces it (if anything).
- **Defer** — relevant later (orchestrator / repair stages not built yet); revisit when those stages land.

## 4.1 Audit summary

| Proto3 ID | Topic | Verdict |
|---|---|---|
| `proto3:D001` | Step / Stage / Search Orchestrator / Cross-cutting / Target terminology | **Carry** |
| `proto3:D002` | `000_*` global docs + `001–014` Step doc naming | **Modify** |
| `proto3:D003` | apartment-first implementation, floor-rooted architecture | **Modify** |
| `proto3:D004` | `ProgramInstance` owns cardinality | **Carry** |
| `proto3:D005` | domain constraints are gates, not role scores | **Carry** |
| `proto3:D006` | region / atom dual layer | **Modify** |
| `proto3:D007` | floor-rooted spine-first candidate search | **Drop** |
| `proto3:D008` | Candidate Search is not a Stage | **Defer** |
| `proto3:D009` | pre-repair and post-repair validation | **Defer** |
| `proto3:D010` | failure-to-pruning backtracking | **Defer** |
| `proto3:D011` | access-preserving atom growth as invariant | **Drop** |
| `proto3:D012` | start with dataclasses for schema | **Carry** |
| `proto3:D013` | SVG-first visualization | **Carry** |
| `proto3:D014` | debug outputs out of version control | **Carry** |
| `proto3:D015` | per-Step branch + per-work-item commit + no-squash merge | **Modify** |
| `proto3:D016` | per-Step Plan + Tracker companion docs | **Carry** |
| `proto3:D017` | strict `Literal` validation in schema deserialization | **Carry** |
| `proto3:D018` | Stage 13 output assembly: unified `LayoutCandidate(valid=…)` | **Modify** |
| `proto3:D019` | per-family proportional atom sizing (D006 amendment) | **Drop** |
| `proto3:D020` | Stage 02 Domain Feasibility Gate design (4 gates) | **Carry** |
| `proto3:D021` | `TargetRules` + external JSON config | **Carry** |
| `proto3:D022` | generic `TargetAdapter` + 3-layer typology extensibility | **Carry** |
| `proto3:D023` | required-only cardinality and area summation | **Carry** |

Verdict counts: **Carry 13 · Modify 4 · Drop 3 · Defer 3** (updated 2026-05-25 — `proto3:D015` reclassified Carry → Modify per D005).

## 4.2 Notes on Modify / Drop / Defer entries

Carry-as-is entries need no further note; they port directly when the
corresponding code (program layer, schema, viz, workflow) lands in `src/`.

### `proto3:D002` — Modify (docs path + Step count)

- Docs moved from repo root to `docs/000_*`. `src/` and `docs/` stay
  cleanly separated (mirrors the PlanBIM pattern).
- The `001–014` Step list was sized for proto3's full spine-first
  pipeline. The new pipeline already has `archive/celllayout/` Phase 1–8
  working code covering atomize → corridor carving, so the Step count and
  per-Step scope will shrink. New Step list deferred until pipeline §3 is
  finalized in `000_Pipeline_Overview.md`.

### `proto3:D003` — Modify (schema multi-floor-aware day-one, algorithm single-floor first)

Resolved 2026-05-24 with the new decision splitting "validated algorithm
scope" from "schema reach":

- **Apartment** is the first *validated algorithm* target.
  `archive/celllayout/` Phase 1–8 was exercised against apartment-unit-scale
  footprints (~50–100 m²) only.
- **Schema is multi-floor-aware from day one.** `ShapeInput` accepts a
  list of floor footprints with a reserved `vertical_anchors` slot
  (stair / elevator core positions that must align across floors). This
  preserves the *spirit* of `proto3:D003` ("floor-rooted architecture
  from start") even though no multi-floor target ships in v1.
- **Multi-floor orchestrator is an explicit deferred milestone.**
  v1 orchestrator either asserts `len(floors) == 1` or runs the
  single-floor algorithm once per floor without enforcing vertical
  anchor alignment. Per-floor program allocation, stair / core anchor
  propagation, and cross-floor validation belong to a later Step.
- **Building-scale footprint (~500–2000 m²) is also deferred** —
  `atomize` / `regionize` / corridor carving were never run beyond
  apartment-unit scale; graph size and tuning may need re-validation
  when the algorithm is asked to handle whole-building footprints.

### `proto3:D006` — Modify (semantics inverted; layer count grows to 3)

- The dual-layer *principle* survives, but the *semantics* shift:
  - proto3 `Region` = coarse **architectural territory** (carried
    role hints like `public-candidate`) — **this concept moves to the
    Room layer** in the new repo.
  - proto3 `Atom` ≈ Cell `Atom` (≈0.3 m² geometric primitive) —
    unchanged in spirit.
  - Cell `Region` is a **new intermediate layer** (~3 m² atom cluster)
    that proto3 did not have.
- Net: dual-layer becomes triple-layer (atom / region / room), and the
  word "region" is reassigned. Lands as the new repo's D003.

### `proto3:D007` — Drop (spine-first → seed-first growth + corridor carving)

- Spine-first was the proto3 framework invariant: hub → spine →
  branch slots → seeds → growth. The `archive/celllayout/` working code
  validated a seed-first alternative through Phase 1–8:
  seed-first room growth (Phase 7) + post-hoc corridor carving (Phase 8)
  produces apartment-grade layouts without explicit pre-growth spine
  hypothesis generation. Lands as the new repo's D002.
- All vocabulary from proto3:D007 (hub / trunk / branch / stub spine /
  branch slot) drops with it.

### `proto3:D008` — Defer (orchestrator not built yet)

- The Search Orchestrator distinction (Candidate Search ≠ Stage) is
  still a sound architectural call, but the new repo has zero
  orchestrator code today. Re-examine when first orchestrator scope
  is opened.

### `proto3:D009` — Defer (repair stages not built yet)

- Pre-repair / post-repair validation split is a useful architecture
  *if and when* a repair stage exists. `archive/celllayout/` does not
  yet have a repair stage; it ships `valid` layouts directly. Re-examine
  if a repair stage becomes scoped.

### `proto3:D010` — Defer (orchestrator concern)

- Failure-to-pruning belongs to the Search Orchestrator layer
  (`proto3:D008`). Defer with D008.

### `proto3:D011` — Drop (access invariant moves to corridor carving)

- proto3:D011 required atom growth itself to preserve access. In the
  new pipeline, seed-first room growth ignores access during growth,
  and the corridor carving pass (Cell Phase 8) restores connectivity
  afterwards. The *invariant* ("output layouts must have valid access")
  carries, but the *mechanism* ("growth itself must preserve access") drops.
- The first-pass greedy-multi-source growth implementation also drops
  with it; Cell's region-partition growth replaces it.

### `proto3:D018` — Modify (principle keeps; field set rebuilds)

- The "unified `LayoutCandidate(valid=True|False)` instead of split
  Valid / Invalid types" *design principle* carries.
- The exact field set
  (`validation_result` / `failure_records` /
  `debug_artifact_refs` / `provenance` / `output_artifacts`) was sized for
  the proto3 spine-first pipeline. The new pipeline's output type
  (`LabeledRoomLayout`, working name) needs a fresh field-set review
  against what `archive/celllayout/` actually produces
  (`LayoutFixture` / `GrowthResult` / `CorridoredLayout`).

### `proto3:D015` — Modify (per-Step branch demoted to guideline for solo work)

Reclassified 2026-05-25 from Carry to Modify when D005 landed:

- The **per-Step branch requirement** is demoted to a guideline.
  Default is `main`; branch only when one of D005's four triggers fires.
- The **per-work-item commit** and **no-squash merge** provisions
  carry unchanged.
- See D005 for full rationale and trigger criteria.

### `proto3:D019` — Drop (proto3-only amendment; superseded by Cell DimensionPolicy)

- D019 was the import contract for `src/proto3/geometry/`
  (v3.2 cell partition algorithm). That code is dead in proto3 — never
  called by any stage. The Cell/algorithm pipeline owns its own
  atom-sizing policy (`DimensionPolicy` with `target_atom_size=0.3 m`,
  `geometry_snap=0.01`, `module_quantum=0.05`) which has been validated
  through Phase 1–8 and is the canonical replacement. Drop both the
  `proto3:D019` parameter table and the `src/proto3/geometry/` code
  it referenced.

---

# 5. Decision history appendix

| Date | Decision | Change |
|---|---|---|
| 2026-05-24 | repo init | scaffold only — no decisions yet committed |
| 2026-05-24 | §4 audit | proto3 D001–D023 audited: Carry 14 · Modify 3 · Drop 3 · Defer 3 |
| 2026-05-24 | D001–D004 lock | Phase-1 D-series accepted — external contract, seed-first growth + corridor carving, triple-layer geometry, 7-class Role taxonomy |
| 2026-05-25 | D005 lock | Solo-mode workflow — default to `main`, branch only on size / risk triggers. `proto3:D015` audit verdict moved Carry → Modify (audit summary now Carry 13 · Modify 4 · Drop 3 · Defer 3). |
| 2026-05-25 | D006 lock | Output directory convention — 3 categories (test golden / debug runs / experiments), `NN_<stage_id>.{json,png}` per-stage layout, `manifest.json` schema, `seed<N>_<isoformat-utc>` run-id default. Carries `proto3:D014`. |
