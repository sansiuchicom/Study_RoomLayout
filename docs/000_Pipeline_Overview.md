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
    holes: tuple[Ring, ...] = ()            # CCW interior holes; empty by default
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
    debug_artifacts: dict[str, str]         # {kind: path}

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

_To be written._ Inherited from the `archive/celllayout/` Phase 1–8 work:

```text
ShapeInput
  → atomize          (per-territory cells, 50% merge rule)
  → atom_graph
  → regionize        (~3 m² atom clusters)
  → region_graph
  → region growth    (seed-first room growth)
  → corridor carving (hub-radial A* + shortcut)
  → labeling         (role assignment, validation)
  → LabeledRoomLayout
```

The growth-and-carving model replaces the predecessor proto3 spine-first model.
See `D002`.

---

# 4. Terminology

_To be written._ Carry over the Step / Stage / Search Orchestrator /
Cross-cutting Infrastructure / Target distinction from proto3 where it still
applies, after the §4 audit in `000_Architecture_Decisions.md`.
