# RoomLayoutCell Geometry-Only Layout Plan

## Summary

`RoomLayoutCell` is the algorithm lab for `RoomLayout`. It should prove whether
geometry-only layout generation can produce plausible room-like partitions before
anything is ported into the main repo.

This repo intentionally avoids domain knowledge:

```text
No living / bedroom / bathroom rules.
No apartment-specific access policy.
No ProgramInstance semantics.
```

The first layout experiment consumes simple geometric intent:

```text
Input:
  footprint polygon
  target_room_count
  optional entry/root point
  optional area weights

Output:
  over-segmented zones
  merged room groups
  hub/access candidate
  corridor or access path
  diagnostics + visualization
```

## Repository Structure

The repo is organized so existing zoning experiments remain stable while the new
layout experiment can grow beside them.

```text
algorithm/
├── demos/
│   ├── zoning_demo.py       # Current zone_footprint() showcase runner.
│   └── layout_demo.py       # Future room-group + hub/corridor runner.
├── celllayout/
│   ├── atom/                # Existing atom/cell decomposition.
│   ├── cases.py             # 33 showcase footprints.
│   ├── zoning.py            # Existing zone generator; keep stable.
│   ├── graph.py             # M1: zone adjacency graph.
│   ├── grouping.py          # Planned: zones -> room groups.
│   ├── access.py            # Planned: hub selection + corridor routing.
│   ├── experiment.py        # Planned: layout_footprint() public API.
│   ├── metrics.py           # Planned: diagnostics and quality metrics.
│   └── viz.py               # Planned: integrated visualization.
├── demo.py                  # Compatibility wrapper for demos/zoning_demo.py.
└── outputs/
    ├── zoning/              # Current zoning reference figures.
    └── layout/              # Future layout experiment figures.
```

Existing usage remains valid:

```bash
cd algorithm
python demo.py
python demos/zoning_demo.py
```

Both commands write zoning figures to:

```text
algorithm/outputs/zoning/
```

Future layout experiments should write to:

```text
algorithm/outputs/layout/
```

## Key Changes

- Treat `zone_footprint()` output as **sub-room blocks**, not final rooms.
- Add a `room_group` step that merges adjacent zones to match
  `target_room_count`.
- Treat `hub` as a geometry-only access source, not a living/kitchen semantic.
- Use atom/cell information first as a **corridor routing substrate**, not as a
  required final room-growth representation.
- Let corridor/access feasibility influence grouping rather than treating it as
  a purely final cleanup pass.

## Proposed Pipeline

```text
1. Generate zones
   footprint -> zones, families

2. Build zone graph
   zones -> adjacency graph
   edge metadata:
     shared boundary length
     centroid distance
     door-capable-like boundary width

3. Choose hub/access source
   if entry exists:
     choose zone near entry with good centrality
   else:
     choose central/high-connectivity zone

4. Merge zones into target room groups
   zones + target_room_count -> room_groups
   constraints:
     adjacent zones only
     compact merged shape
     reasonable aspect ratio
     approximate target area balance
     preserve future access feasibility

5. Route access
   hub/access source -> every room_group
   use atom/cell graph for shortest path if available
   produce corridor cells or corridor polygon

6. Repair and evaluate
   subtract or reserve corridor from affected rooms
   remove tiny fragments
   compute diagnostics

7. Visualize
   draw footprint, zones, room groups, hub, corridor path, failures
```

## Minimal Interfaces

Planned high-level experiment entrypoint:

```python
layout_footprint(
    footprint,
    target_room_count: int,
    entry_point: tuple[float, float] | None = None,
    area_weights: list[float] | None = None,
) -> LayoutExperimentResult
```

Use simple geometry-only result objects or dicts:

```text
LayoutExperimentResult
- zones
- zone_graph
- room_groups
- hub
- corridor
- diagnostics

Zone
- zone_id
- polygon
- area
- family_id
- theta

RoomGroup
- room_id
- zone_ids
- polygon
- area
- aspect
- compactness

Corridor
- polygon or cell_ids
- connected_room_ids
- area
- path_cost

Diagnostics
- room_count_match
- gap_area_ratio
- unreachable_room_count
- corridor_area_ratio
- fragmented_room_count
- min_room_area
- max_aspect
```

## Milestones

1. **M1 Zone Graph** (implemented)
   - Build adjacency graph from `zone_footprint()` output.
   - Visualize shared-boundary graph.

2. **M2 Zone Merge**
   - Merge zones into exactly `target_room_count` room groups.
   - Start with deterministic greedy merge using adjacency + compactness + area balance.

3. **M3 Hub Selection**
   - Pick hub/access source from entry point if provided.
   - Fallback to graph-central zone.

4. **M4 Corridor Routing**
   - Build cell/atom graph.
   - Route shortest access paths from hub to each room group.
   - Output corridor cells or corridor polygon.

5. **M5 Integrated Visualization**
   - Add layout visualization under `celllayout.viz`.
   - Show zones, merged rooms, hub, corridor, and unreachable rooms.

6. **M6 Batch Evaluation**
   - Run all 33 cases through `demos/layout_demo.py`.
   - Print metrics table and save figures under `outputs/layout/`.

## Test Scenarios

- Rectangles: `30평 판상형`, `40평 4-bay`, `Square 10x10`
- Concave footprints: `ㄱ자`, `ㄷ자`, `E자`, `ㄹ자`
- Hole footprints: `ㅁ자 small hole`, `ㅁ자 big hole`, `ㅁ자 + wing`
- Rotated/multi-axis: `Rect rotated 30°`, `ㄱ자 rotated 30°`, `Mirror wings ±30°`
- Curved: `Circle`, `Ellipse`, `Half circle`

Acceptance criteria for the first useful version:

```text
- target_room_count is matched
- no footprint gap except intentional holes
- every room group has access path to hub
- corridor area is reported
- fragmented rooms are reported, not hidden
- all 33 cases produce visualization without crashing
```

## Assumptions

- `RoomLayoutCell` stays domain-free: no bedroom/bathroom/living rules.
- `target_room_count` is the first program-like input.
- `area_weights` are optional and purely geometric.
- Entry/root point is optional; when missing, hub is chosen by centrality.
- Current `zone_footprint()` remains the zone generator.
- Main repo integration is deferred until Cell proves zone merge + access routing works.
