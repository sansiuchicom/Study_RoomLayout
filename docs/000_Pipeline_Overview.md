# 000 Pipeline Overview

Status: Canonical global reference
Scope: `Study_RoomLayout` framework, external contract, internal pipeline, and
its position inside the PlanBIM synthetic-BIM pipeline
Last updated: 2026-05-24

---

## 0. Purpose

This document is the canonical overview for `Study_RoomLayout`.

It defines:

- the external contract (input / output) exposed to the PlanBIM pipeline,
- the internal stage flow that turns a footprint into a labeled room layout,
- the terminology that the rest of the docs and code must use consistently.

This file is not a daily tracker. Current work status belongs in
`000_Progress_Tracker.md`. Accepted design decisions and their rationale belong
in `000_Architecture_Decisions.md`.

---

# 1. Position in the PlanBIM pipeline

`Study_RoomLayout` is the **Stage 4 — Room Layout** component of the external
PlanBIM scan-to-BIM training-data pipeline. It is a pure function inside that
larger pipeline:

```text
... → Stage 3 (Wall) → Stage 4 (Room Layout, this repo) → Stage 5 (Facade) → ...
```

See the PlanBIM repo for the surrounding stages.

---

# 2. External contract

The single entry-point signature is:

```python
def run(
    shape: ShapeInput,
    program: ProgramRequest,
    *,
    seed: int,
) -> LabeledRoomLayout
```

Pure function, no in-place mutation. Adapter layers (e.g., a future
`adapters/researchbim.py`) translate between this contract and external
data models such as ResearchBIM's `Building` / `Storey` mutation pattern.
Adapters are not in v1 scope. See D001.

The type sketches below are *intent-level* — exact field names may be
refined when the code lands in `src/`. Coordinate unit is **meters (SI)**
throughout. Polygons are `shapely.Polygon`, CCW, centerline convention
(wall thickness ignored). These conventions align with ResearchBIM and
`ResearchBIM_customized-ifcopenshell`.

## 2.1 ShapeInput (input — geometry)

Multi-floor-aware from day one (D001 carries `proto3:D003`'s
"floor-rooted from start" intent into the new repo):

```python
@dataclass
class ShapeInput:
    name: str                               # required identifier (debug hygiene; S02-D7)
    floors: list[FloorShape]                # length 1 = single-floor v1
    vertical_anchors: list[VerticalAnchor]  # empty list when no anchors

@dataclass
class FloorShape:
    level: int                              # 0 ground, ≥1 above, ≤-1 basement
    parts: list[ShapePart]                  # caller-preserved decomposition (see below)
    floor_to_floor_height: float | None     # meters; required only when multi-floor

@dataclass(frozen=True)
class ShapePart:
    exterior: Ring                          # CCW vertex ring, meters
    holes: tuple[Ring, ...] = ()            # CW interior holes (shapely right-hand rule, IFC convention)
    # NOTE: no `theta` field. Per-part orientation is *inferred* from the
    # first non-degenerate exterior edge by a helper (`part_theta()` in
    # Cell/algorithm). Callers do not pre-compute orientation.

@dataclass
class VerticalAnchor:
    id: str
    kind: Literal[
        "stair_core", "elevator_shaft",
        "ps_shaft", "eps_shaft", "duct_shaft",
    ]
    footprint_polygon: Polygon              # identical XY across `floor_range`
    floor_range: tuple[int, int]            # inclusive (start_level, end_level)
    host_role: Literal["vertical_circulation"] | None
                                            # `None` for shafts with no walk-in room
                                            # (`ps_shaft`, `eps_shaft`, `duct_shaft`)
                                            # `"vertical_circulation"` for stair / elevator
```

**Parts preserved, not unioned.** The footprint of a floor is delivered
as a list of design-time primitives (`ShapePart`) — typically a main
rect plus rotated wings, mirror extensions, or curved cuts. The caller
(e.g., PlanBIM Stage 1 massing) already knows this decomposition;
preserving it lets the algorithm read each part's orientation from its
own edges with no detection / inference step. The union of parts is
computed downstream when needed (area checks, boundary tracing) but is
**never the canonical input form**. Receiving a single unioned polygon
would force the algorithm to recover orientation heuristically, which
the design explicitly avoids.

v1 algorithm asserts `len(floors) == 1` or processes one floor at a time
without enforcing cross-floor anchor alignment. Multi-floor orchestration
is a deferred Step (D001 / `proto3:D003` audit).

## 2.2 ProgramRequest (input — semantics)

Floor-scoped: the caller decides which spaces go on which floor. Single-
floor v1 uses one dict entry.

```python
@dataclass
class ProgramRequest:
    target_type: Literal[
        "apartment", "house", "hotel", "office", "warehouse",
    ]
    floor_programs: dict[int, list[SpaceUnitSpec]]
                                            # key = floor level

@dataclass
class SpaceUnitSpec:
    id: str
    role: Role                              # functional class — drives algorithm
    usage: str | None                       # concrete room type — pass-through only
    area_target_m2: float
    area_min_m2: float | None
    min_dimension_m: float | None
    required: bool                          # `proto3:D023` required-only summation
    anchor_id: str | None                   # required when `role == "vertical_circulation"`
                                            # links to `ShapeInput.vertical_anchors[i].id`

Role = Literal[
    "public", "private", "service", "wet",
    "hub", "corridor", "vertical_circulation",
]
```

Role taxonomy and the role / usage split: see D004. The algorithm reads
`role`; `usage` is carried through to the output untouched. Caller-side
typology rules (e.g., apartment role → usage default-fill) live in
`target_rules/<typology>.json` per `proto3:D021`, accessed via an
`expand_program()` helper (not part of `run()`'s signature).

## 2.3 LabeledRoomLayout (output)

Unified valid / invalid contract (`proto3:D018` principle carries):

```python
@dataclass
class LabeledRoomLayout:
    valid: bool
    floors: list[LabeledFloorLayout]        # 1:1 with `ShapeInput.floors`, same order
    failure_records: list[FailureRecord]    # must be non-empty when `valid=False`
    provenance: dict                        # search-path info (TBD typed)
    # Per-stage debug artifacts (PNGs / stage JSON) are NOT carried in
    # this output. `run()` is pure (no filesystem side-effects); stage
    # trace emission happens via the `on_stage` callback wired in
    # Step 07's entry point. See D006 for the file layout.

@dataclass
class LabeledFloorLayout:
    level: int
    rooms: list[LabeledRoom]
    corridor_polygons: list[Polygon]        # output of Cell Phase 8 corridor carve

@dataclass
class LabeledRoom:
    id: str                                 # matches `SpaceUnitSpec.id` when known
    polygon: Polygon                        # CCW, meters, centerline
    role: Role
    usage: str | None                       # carried over from `SpaceUnitSpec.usage`
    area_m2: float
    doors: list[Door] | None                # v1: always `None` (deferred)
    anchor_id: str | None                   # set when `role == "vertical_circulation"`
```

## 2.4 Conventions and deferred concerns

- **Coordinate unit**: meters everywhere. `proto3:D019` mm convention dropped.
- **Polygon**: `shapely.Polygon`, CCW, centerline (matches ResearchBIM).
- **Seed**: `seed: int` is keyword-only and required; reproducibility is
  critical for PlanBIM training-data generation.
- **Partial output on failure**: when `valid=False`, `floors` may carry
  partial layouts for debugging — implementations must not clear them.
- **`Door` slot**: `LabeledRoom.doors` is reserved but always `None` in
  v1. Activation deferred until access topology from Phase 8 corridor
  carving is upgraded to emit door positions.
- **Anchor-locked rooms**: `vertical_circulation` rooms get their
  polygon from the linked `VerticalAnchor.footprint_polygon`, not from
  algorithm growth. Other anchors (PS / EPS / duct shafts with
  `host_role=None`) are treated as forbidden regions only; no
  `LabeledRoom` is emitted for them.
- **Adapter layer**: drop-in replacement of `ResearchBIM_synthetic-bim`
  `run_s04_core_bsp(...)` is handled by `adapters/researchbim.py`
  (post-v1). v1 only ships this contract.

---

# 3. Internal pipeline

Per-stage operational view. Design rationale (why seed-first growth +
post-hoc carving instead of spine-first) lives in D002. v1 algorithm
executes this pipeline against **one floor at a time**; the multi-floor
orchestrator that wraps this loop is a deferred concern (D001).

## 3.1 Pipeline diagram

```text
FloorShape (one floor) + ProgramRequest.floor_programs[level]
  → 3.2 atomize            (Cell Phase 3)  → atoms
  → 3.3 atom_graph         (Cell Phase 4)  → atom_graph
  → 3.4 regionize          (Cell Phase 5)  → regions
  → 3.5 region_graph       (Cell Phase 6)  → region_graph
  → 3.6 region partition growth (Cell Phase 7)  → rooms (pre-carve)
  → 3.7 corridor carving   (Cell Phase 8)  → rooms + corridor_polygons
  → 3.8 labeling           → LabeledFloorLayout
multi-floor outer loop  → assemble LabeledRoomLayout
```

## 3.2 atomize

For each `ShapePart`, generate proportional atom cells targeting
`target_atom_size ≈ 0.3 m` per side. Boundary cells whose
intersection-area-fraction with the part is below 0.5 ("50 % rule") merge
into the longest-shared-boundary neighbor. Inputs: `FloorShape.parts` +
`DimensionPolicy`. Output: `list[Atom]` (~0.3 m² each).

## 3.3 atom_graph

Build atom adjacency graph with `shared_boundary_length` weighted edges.
Inputs: atoms. Output: `atom_graph` (NetworkX).

## 3.4 regionize

Hierarchical slab-cut of atoms into ~3 m² regions (Cell tier sequence
T1a / T1b / T2 / T3). Regions are **purely geometric** per D003 —
no role hint, no kind field. Inputs: atoms + atom_graph. Output:
`list[Region]`.

## 3.5 region_graph

Region-level adjacency graph (region–region shared boundary). Used as
the substrate for seed-first growth. Inputs: regions. Output:
`region_graph`.

## 3.6 region partition growth

Seed-first room growth across regions. Hub seed → growth fills the
floor greedily by per-`Role` priority. `vertical_circulation` rooms are
**not grown** (D004) — their polygon is the linked
`VerticalAnchor.footprint_polygon` and they participate as fixed
forbidden regions during growth. Inputs: regions + region_graph +
`ProgramRequest.floor_programs[level]`. Output: preliminary `rooms`.

## 3.7 corridor carving

Two-stage carving (Cell Phase 8):

- **Stage 1 — hub-radial A***: route paths from each
  hub-disconnected room cluster back to the `hub` room.
- **Stage 2 — detour shortcut**: add direct edges between hub-adjacent
  rooms when the Stage 1 path is materially longer than the shortcut.

Inputs: preliminary rooms + region_graph. Output: final rooms +
`corridor_polygons`.

## 3.8 labeling

Assign final `Role` (already determined by seed program) + carry
through `usage` to each room, compute `area_m2`, run `proto3:D020`
domain feasibility gates (area / dim / access / multi-floor) and
`proto3:D023` required-only summation. Inputs: rooms +
`ProgramRequest`. Output: `LabeledFloorLayout` for this floor.

The outer per-floor loop assembles all `LabeledFloorLayout`s into one
`LabeledRoomLayout` (D001 §2.3).

## 3.9 Cross-cutting concerns

Per `proto3:D001` (carried): provenance, debug artifacts (SVG default
per `proto3:D013`), `FailureRecord` accumulation, and seed propagation
thread through every stage but are not stages themselves. They live in
shared infrastructure modules invoked from each stage.

---

# 4. Terminology

## 4.1 Process terms

Carried from `proto3:D001` with one status change — Search Orchestrator
is **deferred** in this repo (no orchestrator code exists yet; the
audit marked `proto3:D008` / `D009` / `D010` as deferred together).

| Term | Meaning | Status here |
|---|---|---|
| **Step** | Development roadmap unit. Order in which the repo is implemented. | Active — Step list to be derived in the next pass. |
| **Stage** | Runtime pipeline unit. One transformation a single layout candidate undergoes (§3.2–3.8). | Active. |
| **Search Orchestrator** | Control loop that runs the Stage pipeline repeatedly, manages candidates, retries, no-good records, search budget. | Deferred. |
| **Cross-cutting Infrastructure** | Systems used across stages — provenance, debug artifacts, viz, RunConfig. | Active. |
| **Target** | Building / spatial typology adapter (apartment / hotel / house / office / warehouse) — carries the `target_rules/<typology>.json` config (`proto3:D021` / `proto3:D022`). | Active. |

Rules:

- **Step ≠ Stage.** Step is implementation order; Stage is runtime
  pipeline order. A Step may implement one Stage, several Stages, part
  of a Stage, cross-cutting infrastructure, or future Search
  Orchestrator scope.
- **Candidate Search is not a Stage** (`proto3:D008` deferred carry).

## 4.2 Geometric layers

Triple-layer model per D003:

| Layer | Typical size | Purpose |
|---|---:|---|
| `Atom` | ~0.3 m² | Finest geometric primitive. Per-part proportional cells. |
| `Region` | ~3 m² | Atom cluster, **purely geometric** — no role, no kind. |
| `Room` | variable | Architectural unit — carries `Role` and `usage`. |

Numerical defaults from Cell `DimensionPolicy`:
`target_atom_size = 0.3 m`, `geometry_snap = 0.01 m`,
`module_quantum = 0.05 m`.

## 4.3 Role taxonomy

7-class `Role` per D004 — `public` / `private` / `service` / `wet` /
`hub` / `corridor` / `vertical_circulation`. See D004 for the full
table including per-role algorithm behavior, anchor binding rules,
and the deferred-role registry (`storage` deferred, `outdoor`
permanently excluded).

## 4.4 Decision namespace

This repo's D-series (`D001`, `D002`, ...) is the new repo's own
namespace, restarted at D001. Predecessor proto3 decisions are
referenced as `proto3:DXXX` throughout this repo. The two are not the
same numbering. See `000_Architecture_Decisions.md` §4 for the
inherited-decision audit.

---

# 5. Step map

Steps are *implementation roadmap units* per §4.1 — the order in which
the repo is built. v1 ships at Step 08 completion (single-floor
apartment with `run()` end-to-end + SVG viz). Steps 09–10 are explicitly
post-v1.

Workflow conventions follow `proto3:D015` (per-Step branch + per-work-
item commit + no-squash merge) and `proto3:D016` (per-Step Plan +
Tracker companion docs).

## 5.1 Active Steps (v1)

| # | Step | Core artifact | Definition of Done |
|---|---|---|---|
| **01** | Project skeleton | `pyproject.toml` + `src/<pkg>/__init__.py` + `tests/` scaffold + minimal CI | `pip install -e .` works; empty `pytest` run passes |
| **02** | Core schema port | New contract types from D001 (`ShapeInput` / `FloorShape` / `ShapePart` / `VerticalAnchor` / `ProgramRequest` / `SpaceUnitSpec` / `LabeledRoomLayout` / `LabeledFloorLayout` / `LabeledRoom` / `Role` / `FailureRecord`). Cell schema is **refactored in-place** to use the new types (no internal-vs-public schema split). | All types importable; instantiation + strict `Literal` validation tests pass (`proto3:D017` carry); Cell algorithm modules still compile against the unified schema |
| **03** | Geometry pipeline port | Cell **Phase 3–5** ported (pure-geometry half): `territory` / `atomize` / `atom_graph` / `regionize` / `region_graph` + `dimensions` / `_helpers`. Footprint parts → atoms → regions → region adjacency graph. Size/aspect gates live *inside* `regionize` cut selection; `shape_gate` + growth/carve (Phase 6–8) deferred to Step 04 (S03-D3 / S03-D16). | 33 Cell showcase cases produce **semantically equivalent** per-stage golden outputs (polygon area / atom / region counts within `tol=1e-6` — not byte-identical, since shapely / NetworkX float serialization can drift); `target_atom_size = 0.3 m` defaults preserved |
| **04** | Algorithm core port | Cell **Phase 6–8** ported (growth + carve half): `seed_placement` / `growth_seed` / `growth_cells` / `growth_partition` / `growth_absorb` / `room_growth` / `corridor` + `corridor_*` (×5) + `shape_gate` (reflex helper, deferred from S03-D16). Consumes Step 03 `Region` / `AtomGraph` / `RegionGraph` / atoms as growth substrate; the final `corridor` stage emits a region-based `CorridoredLayout` (per-room region sets + corridor regions). Polygonization + `LabeledRoomLayout` assembly is **Step 07** (S04-D2). | 33 showcase cases produce **semantically equivalent** seed / layout / corridor golden outputs; per-stage golden + dev-bridge viz infra extended from Step 03 (only the stage list grows) |
| **05** | Program layer port | proto3 `stages/stage01_program.py` + `stages/stage02_gate.py` ported. The 4 gates (`check_min_area` / `check_min_dim` / `check_access_schema` / `check_multi_floor_feasibility`) live in `constraints/gates.py`. `proto3:D020` / `D023` carry. | Program gate unit tests pass; `ProgramInstantiationFailure` + `DomainGateFailure` hierarchy round-trips through `FailureRecord` |
| **06** | Target rules system | `TargetRules` (+ `default_min_area_m2`) + `data/target_rules/apartment.json` + `README.md` + `target/rules_loader.py` + single generic `TargetAdapter` + `expand_program()` caller helper (`proto3:D021` / `D022` carry). `usage` stays a user/BIM-set pass-through — no role↔usage auto-mapping (S06-D3). | `expand_program({"public": 1, "private": 3, ...}, "apartment", rules=...)` returns a valid `ProgramRequest` that passes stage01/stage02; `apartment.json` validates against the loader |
| **07** | Entry point + labeling | `run(shape, program, *, seed) -> LabeledRoomLayout` assembled per D001. Per-floor outer loop, labeling stage (3.8) assigns final `Role` + carries `usage` + computes `area_m2` + runs gates. Failure path produces `valid=False` with non-empty `failure_records` (`proto3:D018` enforcement). | `run()` on each of 6 apartment fixtures returns `valid=True` matching golden `LabeledRoomLayout`; failure injection (e.g., infeasible program) returns `valid=False` with the right `FailureRecord` codes |
| **08** ✅ | SVG visualization | **Done (v1 ship gate).** Canonical layered-SVG renderer (`viz/svg.py` — `render()`): 12 ordered named `<g>` layers **re-derived from our pipeline** (proto3's `viz/svg.py` was a footprint+grid skeleton, so its architecture was adopted but its spine-first stack dropped — S08-D2). `make_gif()` pipeline-progression animation from the matplotlib frames via `pillow` (S08-D3/D4). Single `viz/palette.py` vocabulary (S08-D6). SVG rides the `on_stage` hook — `run()` untouched (S08-D7) — opt-in via `RunConfig.debug_artifacts`. Matplotlib viz demoted to dev-bridge. | Structural SVG tests (layer order/classes, role-fill, footprint union, anchors — not byte-golden, S08-D5) + gif smoke; opt-in via `RunConfig(debug_artifacts=("json","svg"))`. ✅ |

**v1 ship gate — met.** Step 08 complete: `run()` works on single-floor
apartments end-to-end with the canonical SVG viz path (+ a pipeline-progression
GIF). No remote / external pipeline integration required for v1. Post-v1:
Steps 09 (ResearchBIM adapter) + 10 (multi-floor orchestrator), §5.2.

## 5.2 Deferred Steps (post-v1)

| # | Step | Activation trigger |
|---|---|---|
| **09** | ResearchBIM adapter (`adapters/researchbim.py`) | Activated when integrating with the `ResearchBIM_synthetic-bim` Stage 4 — drop-in replacement for `run_s04_core_bsp(...)` via `Building` / `Storey` mutation translation |
| **10** | Multi-floor orchestrator | Activated when the first multi-floor target (house / hotel) is scoped. Wraps per-floor `run()` with vertical-anchor alignment + per-floor program allocation + cross-floor validation (D001 / D004) |

## 5.3 Dependencies

```text
Step 01 (skeleton)
  └─ Step 02 (schema) ←── blocks everything below
      ├─ Step 03 (geometry pipeline)
      │   └─ Step 04 (algorithm core) ←── consumes 03's Region / AtomGraph / RegionGraph
      ├─ Step 05 (program layer)       ─┐ parallelizable with the 03→04 line
      │   └─ Step 06 (target rules)     │
      │                                 │
      └─ Step 07 (entry point + labeling) ←── joins 04 / 05 / 06
          └─ Step 08 (SVG viz)
              └─ v1 ship ╳
                  ├─ Step 09 (ResearchBIM adapter)   ── post-v1, independent
                  └─ Step 10 (multi-floor orchestrator) ── post-v1, independent
```

The 03→04 line (geometry → algorithm core) and the 05→06 line
(program → target rules) may proceed on parallel branches once Step 02
lands; Step 07 is the join point. Steps 09–10 are independent of each
other and can land in either order post-v1.

## 5.4 Why not more granular Steps?

`archive/celllayout/` Phase 1–8 already covers the full atomize →
corridor-carve algorithm. The new repo's Step list does not need a Step
per Phase — the port is mostly *file move + import rewrite + golden
test*, and splitting per-Phase would multiply the Plan / Tracker
overhead without producing meaningfully separable PRs. Steps 03–04 each
bundle their Phase ports behind a single golden-regression gate (03:
geometry Phase 3–5; 04: algorithm Phase 6–8); if the gate breaks during
a Phase port, the broken Phase is identifiable from test output, not
from Step granularity.

`proto3`'s 001–014 Step roadmap was sized for a *from-scratch* spine-
first pipeline. Inheriting a validated algorithm collapses much of that
scope.
