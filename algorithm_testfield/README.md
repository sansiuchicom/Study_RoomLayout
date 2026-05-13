# RoomLayoutCell Algorithm Testfield

Fresh testfield for the scan-to-BIM room-layout data generator.

```text
labeled footprint parts (ShapeInput)
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
ShapeInput parts
  Design-time primitives with raw vertex coordinates.
  Each part already carries its own orientation by construction.

Atom
  Fine geometry/control unit, generated per part.
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

## Key Shift from the Previous Iteration

The previous testfield recovered orientation from a unioned polygon via
recursive LIR + boundary-angle clustering. That produced angle drift (25° read
as 22°), sliver explosion, and uncovered-region bugs around joints.

The fresh testfield drops detection entirely. Synthetic data is constructed as
labeled `ShapePart` lists; each part's orientation is trivially the angle of
any of its edges (mod π/2). No LIR, no theta estimation, no clustering.

This is sound because the testfield only consumes synthetic data — the
construction step always knows what shapes it just built. The information was
present and was being thrown away.

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

3. Construction info is ground truth.
   Parts carry their own orientation by virtue of their vertex coordinates.
   Downstream code reads theta from a part's edges; it never estimates,
   clusters, or fits.

4. Vertex alignment matters.
   Part vertices, reflex vertices, and hole vertices should become atom-line
   anchors.

5. Atoms and regions have different jobs.
   Atoms are fine enough for corridor/access. Regions are coarse enough to make
   room grouping plausible.

6. Visualization is mandatory.
   Every phase should have a diagnostic drawing before the next phase depends
   on it.

## Planned Modules

```text
algorithm_testfield/
├── celllayout_tf/
│   ├── schema.py          # ShapePart, ShapeInput
│   ├── cases.py           # 33 showcase ShapeInput builders
│   ├── dimensions.py      # DimensionPolicy and interval splitting
│   ├── atomize.py         # Per-part vertex-aware atomizer
│   ├── atom_graph.py      # Atom adjacency graph
│   ├── regionize.py       # Atom grouping into small regions
│   ├── layout.py          # Room/corridor layout pipeline
│   ├── metrics.py         # Dataset and geometry quality metrics
│   └── viz.py             # Stage-by-stage diagnostics
├── demos/
│   └── visualize_phase.py
├── outputs/
├── tests/
└── README.md
```

Note: no `orientation.py`. Per-part theta is a one-liner (atan2 of any edge);
it lives as a small helper in `schema.py` or `atomize.py`, not as its own
phase or module.

## Phase Plan

### Phase 1: Input Schema + Cases

Define the input model and reproduce the 33 showcase footprints as labeled
part lists.

Schema:

```python
@dataclass(frozen=True)
class ShapePart:
    exterior: tuple[tuple[float, float], ...]
    holes: tuple[tuple[tuple[float, float], ...], ...] = ()

@dataclass(frozen=True)
class ShapeInput:
    name: str
    parts: tuple[ShapePart, ...]
```

Hard constraint: parts are NEVER unioned at the schema layer. Each part stores
the design-time primitive verbatim. The footprint (union of parts) is
computed on demand by viz/metrics, not stored.

Part patterns across the 33 cases:

```text
single rect / L / T / + / E / ㄹ          axis-aligned, 1-many rect parts
ㅁ with hole                                rect part + interior hole
rotated rect / rotated L / rotated 7      rotated parts only
main + wing (22, 23, 24)                  axis-aligned + rotated parts
circle / half circle / ellipse            single high-vertex part
curved-ㄱ                                  2 rects + 1 disk part
```

Tests:

```text
all 33 cases representable
ShapePart rejects <3 vertices
ShapeInput rejects empty parts
case_slug stable
selected_cases([k]) returns correct entry
```

### Phase 2: Dimension Policy

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
widths are quantum-aligned where possible
no avoidable tiny slivers
average width stays near 0.30m
```

### Phase 3: Per-Part Atomizer

Generate fine atoms inside each part's own local orientation frame, then
combine across parts with an overlap-ownership rule.

Per-part inputs:

```text
part vertices              (already in correct frame)
part theta                 (atan2 of first non-degenerate edge, mod π/2)
DimensionPolicy            (target atom size, module quantum)
```

Linework sources within a part:

```text
part exterior
part holes
reflex vertex guide lines
modular grid lines in the part's local frame
```

Overlap ownership rule (initial):

```text
Atomize each part independently in its own frame.
For parts that overlap, earlier parts in the list win.
Later parts only atomize their non-overlapping remainder.
```

This makes case 22 (main + rotated wing) deterministic: main owns its full
rect; the wing's atoms cover only the rotated protrusion.

Output:

```python
Atom(
    atom_id,
    polygon,
    area,
    centroid,
    part_id,
    theta,
    is_feature_sliver,
)
```

Tests:

```text
union(atoms) == union(parts) (no gap, no overlap)
holes preserved
rotated part atoms follow part theta exactly (no drift, no off-by-degree)
overlap ownership: later-part atoms never invade earlier-part territory
vertex anchors appear as atom boundaries
```

### Phase 4: Atom Graph

Build graph connectivity for atom grouping and corridor routing.

Edge metadata:

```text
shared_boundary_length
centroid_distance
same_part
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

Group atoms into room-building regions of roughly `target_area` each. The
algorithm runs per piece, in the theta-group's local frame, in two passes.

Spec:

```text
target_region_area     = 3-8m²
regions are connected atom sets
sliver atoms are already absorbed at atomize
every atom assigned to exactly one region
no region spans two parts or two pieces
cut coords come from the theta-group's atom-edge pool
sibling cells reuse cut coords where balance allows
```

Algorithm:

```text
Pass A — Structural pre-cut
  Structural coords = vertex coords of every territory piece in the
  theta group, in local frame. For each piece, take only the structural
  coords that fall strictly inside its bbox. Bin atoms by those x then
  by those y; each non-empty (x_idx, y_idx) is a "cell".

  This forces region boundaries onto hole reflex coords, neighbor-part
  edge coords, and any part vertex that lands inside another part.
  Atom interiors are never split.

Pass B — Balance subdivision with neighbor propagation
  Each cell needs k = round(cell_area / target_area) regions. If
  k <= 1 the cell is kept; otherwise it is recursively subdivided.

  Cut candidates per recursion level:
    - drawn from the theta-group's atom-edge pool (every atom polygon
      vertex coord in local frame).
    - atoms split by local centroid sign vs the candidate coord.
    - filtered by MIN_AREA, BAL_MIN balance, MAX_ASPECT local-bbox
      aspect on each side.

  Ranking key:
    (1) balance descending                            — primary
    (2) coord-already-seen-in-this-theta-group first  — tiebreaker
    (3) local-bbox aspect ascending                   — final tiebreak

  After a cut is picked, its (axis, coord) joins the theta-group's
  seen-coord state. Cells of the same theta group share this state.
  Cells are processed area-descending so the largest cells anchor
  the cut lines that smaller cells then reuse.
```

Cut history:

```text
Each region records the cut coords that bound it:
  - Pass A: the interior structural coords adjacent to its cell on
    each side (0-4 entries per cell, depending on edge/corner position).
  - Pass B: each (axis, coord) selected on the path to this leaf.
Format: tuple[tuple[axis_label, local_coord], ...]
        where axis_label in {"axis_x", "axis_y"}.
```

Region output:

```python
Region(
    region_id: int,
    shape: ShapePart,
    atom_ids: tuple[int, ...],
    part_id: int,
    piece_id: int,
    theta: float,
    cut_history: tuple[tuple[str, float], ...],
)
```

Tests pinning the spec:

```text
every atom assigned to exactly one region
region area sum == atom area sum (per case)
no region spans two parts or pieces
case 13 (cross): cuts include the cross-part structural x=5 and x=9
case 17 (hole):  cells around the hole are bounded by hole reflex coords
target_area smaller -> more regions
cut_history coords are a subset of the theta-group atom-edge pool
```

### Phase 6: Layout v1

Build the first room-layout result from regions and atom routing.

Public API:

```python
layout_input(
    shape: ShapeInput,
    target_room_count: int,
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
no gap / overlap / outside area
```

### Phase 7: Visualization + Metrics

Every phase should save debug figures:

```text
input parts
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

Phases 1–4 implemented and stable on `master`. Phase 5 is in active
development on branch `phase-5-slab`: the initial T1a/T1b/T2/T3
polygon-cut hierarchy has been replaced with the slab + shared
atom-grid pool (committed). Structural pre-cut and neighbor-coord
propagation (the design above) are the next change on the branch.

Implemented modules:

```text
celllayout_tf/schema.py
celllayout_tf/cases.py
celllayout_tf/dimensions.py
celllayout_tf/atomize.py
celllayout_tf/atom_graph.py
celllayout_tf/regionize.py
celllayout_tf/territory.py
celllayout_tf/viz.py
```

Implemented phases of `demos/visualize_phase.py`:
`input`, `territory`, `atom`, `graph`, `region`, `dimensions`.

Run:

```text
cd /workspace/Study_RoomLayout_Cell/algorithm_testfield
PYTHONPATH=. pytest -q tests
PYTHONPATH=. python demos/visualize_phase.py --phase region
PYTHONPATH=. python demos/visualize_phase.py --phase region 13 17 24
```
