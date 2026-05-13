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
│   ├── territory.py       # Overlap resolution + shape-contact helpers
│   ├── atomize.py         # Per-part vertex-aware atomizer
│   ├── atom_graph.py      # Atom adjacency graph
│   ├── regionize.py       # Atom grouping into small regions
│   ├── region_graph.py    # Region adjacency graph
│   ├── layout.py          # Room/corridor layout pipeline (planned, Phase 7)
│   ├── metrics.py         # Dataset and geometry quality metrics (planned)
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
algorithm runs per piece, in the theta-group's local frame, in two passes
over a shared "structural pool" of coordinates.

Defaults:

```text
target_area    = 3.0 m²   (≈ 1평, Korean residential unit)
MIN_AREA       = 0.7 m²
MAX_ASPECT     = 3.0      (1m × 3m terminal cap)
BAL_MIN        = 0.15
```

Structural pool (per theta group, in local frame):

```text
1. Every non-curved territory piece's polygon vertex coords
2. Every boundary-crossing point between any pair of parts (in any
   theta group) — projected into each piece's local frame, computed
   from ORIGINAL part polygons to skip polygon.difference FP drift.

Conceptually a unified "vertex set" where shape-crossings count as
vertices alongside polygon corners.
```

Algorithm:

```text
Pass A — Structural pre-cut
  Per piece, take pool coords strictly inside its bbox. Bin atoms by
  (x_idx, y_idx) → cells. Each cell's cut_history is the bounding
  structural coords (0-4 entries: corner cells 2, edge 3, interior 4).
  Cells with area < MIN_AREA are absorbed into their largest live
  lattice-adjacent neighbor (successor-chain).

  This forces region boundaries onto reflex/hole/neighbor-edge coords.
  Atom interiors are never split.

Pass B — Balance subdivision with neighbor propagation
  Per theta group, cells are processed area-descending sharing a
  _PropagationState (seen_xs / seen_ys). For each cell:

    k = max(round(area / target_area),
            ceil(cell_aspect / MAX_ASPECT))
        (k_aspect bump so narrow slabs subdivide enough that each
         terminal piece can satisfy aspect with seen-coord cuts.)

  At each recursion level, _select_lattice_cut:
    - Candidates drawn from the theta-group's atom-edge pool.
    - Atoms split by local centroid sign vs the candidate coord.
    - Filtered by MIN_AREA on each side, BAL_MIN balance, and the
      MAX_ASPECT gate. Inside a cell with aspect > MAX_ASPECT, the
      gate uses max(MAX_ASPECT, cell_aspect) so thin cells can still
      subdivide along their wider neighbors' seen cuts.

  Ranking (lexicographic):
    (1) Any seen-coord candidate wins over any unseen.
    (2) Within the chosen pool: balance descending, aspect ascending.

  Picked cut joins state.seen_*. Cells of the same theta group share
  this state, so sibling cells line up at the same coords.
```

Cut history:

```text
Each region records the cut coords that bound it:
  - Pass A: the bounding structural coords of its cell (0-4 entries).
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

atomize.py is extended to support Pass A:
- Per-theta-group atom anchors include cross-pair boundary projections,
  so atom edges land exactly on Pass A's structural cuts (no snap drift).
- Sliver absorption ranks neighbors (same_part DESC, length DESC) so a
  sliver atom prefers a host in its own (part_id, piece_id).

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

### Phase 6: Region Graph

Build region adjacency from `atom_graph`. Same role as Phase 4 but at the
region level: drives Phase 7's room grouping and corridor routing.

Construction (per pair of regions sharing at least one atom-graph edge):

```text
Walk atom_graph edges. For each edge whose two atoms belong to
DIFFERENT regions, accumulate the metadata under that (region_a,
region_b) pair.
```

`door_capable_length` v1:

```text
Recompute each cross-region atom contact as shared LineString segments.
Group segments by direction (1° tolerance) and supporting line (1e-6m
tolerance), then merge endpoint-contiguous intervals (1e-6m tolerance).
The stored value is the longest merged straight run, clamped to
shared_boundary_length.
```

Edge metadata:

```text
shared_boundary_length    sum of atom-edge shared_boundary_length
door_capable_length       longest contiguous straight portion of the
                          shared boundary, used for the ≥0.9m door
                          gate downstream
centroid_distance         distance between region centroids
same_theta_group          both regions share the same eff_theta
exterior_contact          any underlying atom-edge endpoint lies on
                          the footprint exterior
hole_contact              any underlying atom-edge endpoint lies on
                          a hole boundary
```

Output:

```python
RegionEdge(
    region_a: int,
    region_b: int,
    shared_boundary_length: float,
    door_capable_length: float,
    centroid_distance: float,
    same_theta_group: bool,
    exterior_contact: bool,
    hole_contact: bool,
)

RegionGraph(
    regions: tuple[Region, ...],
    edges: tuple[RegionEdge, ...],
)
```

Tests:

```text
build_region_graph(shape) is connected on simply-connected footprints
hole-separated regions are NOT adjacent
case 13 cross: each arm's regions are mutually adjacent only within arm
case 17 ㅁ자 hole: regions wrap around the hole, all connected
door_capable_length(R_a, R_b) ≤ shared_boundary_length(R_a, R_b)
shared_boundary_length is symmetric (a,b) == (b,a)
```

### Phase 7: Layout v1

Build the first room-layout result from regions, region_graph, and atom
routing. Hub-first design — hub anchors the layout, rooms group around it,
corridors connect.

Public API:

```python
layout_input(
    shape: ShapeInput,
    target_room_count: int,
    entry_point: tuple[float, float] | None = None,
    corridor_width: float = 0.6,
) -> LayoutResult
```

Sub-steps:

```text
7a. Hub selection
    If entry_point given: the region containing that point. Else:
    the region with highest atom-graph centrality.

7b. Room grouping (hub-aware)
    Greedy merge of regions until count == target_room_count, using
    region_graph adjacency + (area balance, aspect, hub-distance)
    as merge criteria.

7c. Corridor routing
    For each non-hub room, find atom-graph shortest path from a
    hub atom to a room-boundary atom. Each path's atoms become
    corridor atoms (subtracted from their original room). v1 target
    width is 0.6m (about two atoms), expanded by adding adjacent atoms
    around the path where possible.

7d. Validation
    - All atoms assigned to exactly one of {room_i, corridor}
    - Each room has door_capable_length ≥ 0.9m onto corridor or hub
    - room count == target_room_count (when feasible)
    - rooms and corridor are connected sets
```

Output:

```python
Room(
    room_id: int,
    region_ids: tuple[int, ...],
    atom_ids: tuple[int, ...],
    polygon: ShapePart,
    area: float,
    is_hub: bool,
)

Corridor(
    atom_ids: tuple[int, ...],
    polygon: ShapePart,
    connected_room_ids: tuple[int, ...],
    area: float,
)

LayoutResult(
    rooms: tuple[Room, ...],
    corridor: Corridor,
    hub_room_id: int,
    diagnostics: dict,  # gap_area_ratio, unreachable_rooms, etc.
)
```

### Phase 8: Visualization + Metrics

Every phase should save debug figures:

```text
input parts
atoms
atom graph
regions
region graph
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

Phases 1–6 implemented and stable in the testfield. Phase 6 adds the
region adjacency graph from atom-graph contacts and exposes a region-graph
diagnostic renderer.

Implemented modules:

```text
celllayout_tf/schema.py
celllayout_tf/cases.py
celllayout_tf/dimensions.py
celllayout_tf/atomize.py
celllayout_tf/atom_graph.py
celllayout_tf/regionize.py
celllayout_tf/region_graph.py
celllayout_tf/territory.py
celllayout_tf/viz.py
```

Implemented phases of `demos/visualize_phase.py`:
`input`, `territory`, `atom`, `graph`, `region`, `region_graph`, `dimensions`.

Run:

```text
cd /workspace/Study_RoomLayout_Cell/algorithm_testfield
PYTHONPATH=. pytest -q tests
PYTHONPATH=. python demos/visualize_phase.py --phase region
PYTHONPATH=. python demos/visualize_phase.py --phase region_graph 13 17 24
```
