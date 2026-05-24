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

_To be written._ Target shape:

```text
ShapeInput + ProgramRequest  →  LabeledRoomLayout
```

- **`ShapeInput`** — footprint expressed as parts (preserving orientation per
  part), not a single unioned polygon. See `D001`.
- **`ProgramRequest`** — room program (counts per role, area targets, etc.).
- **`LabeledRoomLayout`** — output polygons per room with role labels and
  corridor geometry. Exact field list pending.

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
