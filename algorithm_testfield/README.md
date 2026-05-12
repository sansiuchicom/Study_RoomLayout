# RoomLayoutCell Algorithm Testfield

Fresh testfield for the scan-to-BIM room-layout data generator.

The previous topology-first zoning experiment has been archived at:

```text
legacy/algorithm_testfield_20260512/
```

This directory starts over with the original research goal restored:

```text
footprint
-> fine atoms
-> small regions
-> rooms + corridor/access
-> scan-to-BIM training layout data
```

## Core Direction

This is not a zoning-quality experiment. The goal is to create a geometric
substrate that can generate plausible room layouts for training data.

The hierarchy is:

```text
Atom
  Fine geometry/control unit.
  Used for corridor width, access routing, and precise footprint coverage.

Region
  Coarse block made from multiple atoms.
  Several regions can form one room.

Room
  Final room group produced from regions.

Corridor / Access
  Routed primarily on the atom graph, because corridor width needs fine control.
```

`zone` is no longer the central concept. If used, it should only mean a debug or
intermediate grouping, not a final design target.

## Dimension Policy

The dataset should avoid noisy fitted decimals such as `0.292857m`, but a hard
`0.30m` grid creates slivers and poor vertex alignment. Use a quantized modular
policy instead.

Initial policy:

```text
geometry_snap      = 0.01m
module_quantum     = 0.05m
target_atom_size   = 0.30m
normal_atom_widths = 0.25m / 0.30m / 0.35m
edge_exceptions    = 0.20m / 0.40m when needed
```

Meaning:

```text
0.30m is the target, not a hard cell size.
Atom intervals should be multiples of 0.05m where possible.
Final coordinates should remain clean for dataset labels.
Corridor widths are checked metrically, not only by atom count.
```

Example:

```text
1.00m interval -> 0.35 + 0.30 + 0.35
4.10m interval -> mostly 0.30m, adjusted with 0.25/0.35 pieces
```

## Design Principles

1. Do not drop small geometry.
   Small pieces may be inconvenient, but they should remain assignable atoms.

2. Prefer assignment over repair.
   Avoid gap/tail cleanup by polygon surgery. Assign atoms/regions instead.

3. LIR is metadata, not boundary.
   LIR can detect orientation and main direction, but LIR rectangles should not
   directly decide final atom or room boundaries.

4. Vertex alignment matters.
   Footprint vertices, reflex vertices, hole vertices, and important boundary
   changes should become atom-line anchors.

5. Atom and region have different jobs.
   Atoms are fine enough for corridor/access. Regions are coarse enough to make
   room grouping plausible.

6. Visualization is mandatory.
   Every stage should have a diagnostic drawing before the next stage depends on
   it.

## Planned Modules

```text
algorithm_testfield/
├── celllayout_tf/
│   ├── dimensions.py      # DimensionPolicy and interval splitting
│   ├── orientation.py     # Recursive LIR/boundary orientation patches
│   ├── atomize.py         # Vertex-aware modular atom generation
│   ├── atom_graph.py      # Atom adjacency graph
│   ├── regionize.py       # Atom grouping into small regions
│   ├── layout.py          # Room/corridor layout pipeline
│   ├── metrics.py         # Dataset and geometry quality metrics
│   └── viz.py             # Stage-by-stage diagnostics
├── demos/
│   └── layout_demo.py
├── tests/
└── README.md
```

## Phase Plan

### Phase 1: Dimension Policy

Implement clean, dataset-friendly modular dimensions.

Core API:

```python
DimensionPolicy(
    geometry_snap=0.01,
    module_quantum=0.05,
    target_atom_size=0.30,
    min_atom_size=0.20,
    max_atom_size=0.40,
)

split_interval(length, policy) -> list[float]
```

Tests:

```text
interval sums are exact after snap
widths are quantum-aligned
no avoidable tiny slivers
average width stays near 0.30m
```

### Phase 2: Orientation Patches

Use recursive LIR and boundary-angle logic only to detect local orientation.

Output:

```python
OrientationPatch(
    patch_id,
    polygon,
    theta,
    confidence,
    depth,
)
```

Tests:

```text
rectangle -> one patch
rotated rectangle -> one rotated patch
main + wing -> multiple patches
L-shape -> main patch + leftover patch
```

### Phase 3: Vertex-Aware Atomizer

Generate fine atoms from linework, not from LIR rectangles.

Linework sources:

```text
footprint exterior
hole boundaries
reflex vertex guide lines
important vertex local x/y guide lines
orientation-frame modular grid lines
```

Output:

```python
Atom(
    atom_id,
    polygon,
    area,
    centroid,
    patch_id,
    theta,
    is_feature_sliver,
)
```

Tests:

```text
atom union == footprint
no overlaps
holes are preserved
rotated footprint atoms follow local theta
vertex anchors appear as atom boundaries
```

### Phase 4: Atom Graph

Build graph connectivity for atom grouping and corridor routing.

Edge metadata:

```text
shared_boundary_length
centroid_distance
same_patch
theta_diff
exterior_contact
hole_contact
```

Tests:

```text
simple footprint graph is connected
hole-separated atoms are not falsely adjacent
shared boundary lengths are stable
```

### Phase 5: Regionizer

Group atoms into room-building regions.

Initial targets:

```text
target_region_area = 3-8m²
regions are connected atom sets
sliver atoms are absorbed by adjacent regions
all atoms assigned exactly once
```

Region output:

```python
Region(
    region_id,
    atom_ids,
    polygon,
    area,
    dominant_theta,
    compactness,
    exterior_contact,
)
```

### Phase 6: Layout v1

Build the first room-layout result from regions and atom routing.

Public API:

```python
layout_footprint(
    footprint,
    target_room_count,
    entry_point=None,
    corridor_width=1.20,
)
```

Initial requirements:

```text
room_count matches target when feasible
rooms are connected region groups
corridor/access path is atom-based
all output polygons are valid
no gap/overlap/outside area
```

### Phase 7: Visualization + Metrics

Every stage should save debug figures:

```text
orientation patches
atoms
atom graph
regions
room groups
corridor/access
```

Dataset metrics:

```text
coordinate_grid_compliance
atom_width_distribution
region_area_distribution
room_area_distribution
corridor_width_error
gap_area / overlap_area / outside_area
graph_connectivity
```

## Current Status

Phase 1 is implemented:

```text
celllayout_tf/dimensions.py
tests/test_dimensions.py
```

Run:

```text
cd /workspace/Study_RoomLayout_Cell/algorithm_testfield
PYTHONPATH=. pytest -q tests
```

Sample interval splits:

```text
1.00m -> 0.35 + 0.30 + 0.35
2.05m -> 0.25 + 0.30 x 6
4.10m -> 0.25 + 0.30 x 12 + 0.25
1.03m -> 0.35 + 0.33 + 0.35
```

Next phase: orientation patches.
