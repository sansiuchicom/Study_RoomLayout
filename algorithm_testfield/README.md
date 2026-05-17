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

### Phase 7: Seeded Room Growth (algorithm-only sandbox)

**Scope.** Given per-room seeds + role-based size/aspect constraints as
external input, test how well an algorithm grows regions into "그럴듯한"
room shapes. Layout, seed positioning, atom-level corridor carving —
**all deferred to later phases**.

This phase is a sandbox for the **growth algorithm itself**, isolated
from layout decisions. Domain knowledge does not enter the algorithm; it
enters only the fixture (room count K, role labels, seed coordinates,
role-based area/aspect tables), which is parameterized externally.

Out of scope for Phase 7 (deferred):

```text
hub designation               — fixture에서 implicit (public role 첫 방)
seed positioning              — separate phase (manual / FPS / voronoi)
corridor carving (atom 단위)  — Phase 8+ (atom-level fine geometry)
door-capable boundary check   — validation phase
repair / rectangularization   — proto3 Stage 12 격, 별도 phase
```

#### External input (fixture-driven)

Fixtures for the 33 cases live in [`PHASE7_Fixtures.md`](PHASE7_Fixtures.md).

```python
@dataclass(frozen=True)
class RoomSpec:
    name: str                              # domain-free ID: "space_1", ...
    role: Literal["public", "private", "service", "wet"]
    seed_position: tuple[float, float]     # algorithm resolves to region
    target_aspect_range: tuple[float, float] | None = None
    # None → use role default; (min, max) → explicit allowed range

@dataclass(frozen=True)
class LayoutFixture:
    case_index: int
    case_name: str
    footprint_area_m2: float
    rooms: tuple[RoomSpec, ...]
    role_min_areas: dict[str, float]                    # 절대 min per role
    role_aspect_ranges: dict[str, tuple[float, float]]  # 절대 aspect per role
```

**No `target_area`, no `max_area`.** Earlier drafts derived
`target = footprint / K` and `max = target × 1.5` (or ×10). Both
encoded an implicit "균등 분배가 default" assumption. The current schema
drops both — growth dynamics + role constraints determine the
distribution without a centrally imposed target.

`role` mirrors proto3 `Role` Literal but uses only 4 of 6 values
(`hub` and `corridor` are excluded — they belong to spine-first phases
downstream).

`target_aspect_range` and `role_min_areas` are the only "shape / size"
knobs the algorithm consumes, and both are **external input**. The
algorithm never assumes "square is good" or any target area internally
— each room declares its allowed aspect range, the fixture declares
per-role minimum areas. Following proto3 D005 (gates, not scores), both
act as **hard gates**.

#### Hub designation (weak invariant, Phase 7 only)

The first `RoomSpec` with `role == "public"` is treated as the **hub**
(no explicit fixture flag — implicit by role + listing order). If no
room has `role == "public"` (K=2 원룸 cases), the hub invariant is
disabled for that fixture.

When a hub exists, growth must preserve **weak hub-connectivity**:

> Every assigned room remains path-connected to the hub in the
> region-graph induced subgraph over the rooms' assigned regions.

This implements proto3 D011 (access-preserving atom growth) at the
**region layer** — "moving through another room" is acceptable because
this phase doesn't draw corridors. Atom-level **strong** hub-adjacency
(each room walls-shares with hub directly or via corridor) is deferred
to Phase 8+.

#### Public API (planned)

```python
grow_rooms(
    shape: ShapeInput,
    fixture: LayoutFixture,
    algorithm: Literal["region_unit_greedy", ...],
    policy: DimensionPolicy | None = None,
) -> GrowthResult
```

#### Algorithm candidates (one at a time, visual comparison)

**(1) `region_unit_greedy`** — first target, region-level growth:

```text
init:
  For each room: seed_position → containing region (Polygon.contains).
                 Assign that region to the room.
  hub_room = first room with role "public", else None.
  For each room: resolve aspect_range (room override or role default),
                                min_area (role_min_areas[role]).

loop:
  unmet = [r for r in rooms if current_area(r) < r.min_area]
  if unmet:
    rank by (min_area − current_area) descending     # min 미달 우선
  else:
    rank by current_area ascending                    # smallest first

  picked_this_iter = False
  for r in ranked order:
    candidates = unassigned region_graph neighbors of r's regions.
    if candidates empty: mark r saturated; continue.

    filtered = candidates filtered by:
      (a) aspect gate:
            a_min, a_max = r.aspect_range
            a_min ≤ bbox_aspect(r ∪ c) ≤ a_max
      (b) hub invariant (only if hub_room is not None):
            after absorbing c by r, all rooms still path-connected
            to hub_room in region-graph induced subgraph.

    if filtered:
      pick max shared_boundary_length(r, c)
      assign c to r; picked_this_iter = True; break.
    else:
      mark r saturated this iteration.

  if not picked_this_iter: stop.   # every room saturated
```

**Stop condition**: every room is saturated — either no unassigned
neighbor exists, or every neighbor violates the aspect or hub gate.
There is no explicit "fill X% of footprint" target; the resulting
unassigned regions are what spine-first will turn into corridor /
access in a later phase.

**Aspect & hub as hard gates** (D005 spirit): a candidate violating
either is **rejected, not penalized**. If no candidate is in-range, the
room is skipped — it may end up below `min_area`, but that failure is
reported in diagnostics rather than masked by accepting a bad shape.

Region-level. Atom-level fine tuning ignored at this phase. Phase 5
regionize already produces near-rectangular regions, so the result
naturally inherits that shape quality.

**Magic / scoring 회피** — every value the algorithm uses is either
geometric (measurable) or external input:

| value | source |
|---|---|
| `bbox_aspect(room)` | geometric: max_side / min_side of bbox |
| `aspect_range` (per room) | external: `RoomSpec.target_aspect_range` 또는 `role_aspect_ranges[role]` |
| `min_area` (per room) | external: `fixture.role_min_areas[role]` |
| `shared_boundary_length` | Phase 6 metadata (geometric) |
| hub designation | external: first `public`-role room |

No tunable weights, no hardcoded thresholds, no central area target.

Deferred algorithm variants (compared visually after region_unit_greedy
results are inspected):

```text
(2) aspect_min_BFS    — atom-unit aspect-minimizing growth
(3) bbox_guided       — target bbox 안쪽 atom 우선 흡수
(4) frontier_strip    — axis-aligned strip growth from seeds
(5) region+atom 2-stage — (1) coarse + (2)/(3) fine-tune
```

#### Output

```python
@dataclass(frozen=True)
class GrownRoom:
    name: str
    role: str
    region_ids: tuple[int, ...]
    area_m2: float
    polygon: ShapePart

@dataclass(frozen=True)
class GrowthResult:
    fixture: LayoutFixture
    rooms: tuple[GrownRoom, ...]
    unassigned_region_ids: tuple[int, ...]
    diagnostics: dict      # per-room area_pressure history, etc.
```

#### Evaluation (first iteration)

**Visualization only**. Quantitative metrics deferred — to be agreed
case-by-case after looking at SVGs. Each case's growth result rendered
with:

```text
- footprint outline
- regions (faint outline)
- atoms (background)
- room assignment (color per room, color scheme by role)
- seed positions (annotated dots)
- unassigned regions (gray hatched)
```

#### Tests (initial sketch)

```text
seed_position 안쪽 → 정확히 한 region에 resolve
seed_position 바깥/hole → fixture validation error
모든 room이 connected (region_graph induced subgraph)
모든 region이 정확히 한 room에 할당되거나 unassigned로 보고
case 01 (rect, K=5) 시각화 통과
case 24 (small angled, K=2) 시각화 통과
```

#### Round 4 — Rect-Preserving Growth (in progress, branch `phase-7-rect-growth`)

Round 3 result review (33 PNGs) surfaced two systemic issues:

```text
1. 사각형 유지 실패 — bbox_aspect gate는 외접 사각형 비율만 보므로
   L자/T자 흡수가 합법적으로 통과됨. Rectangularity 개념 없음.
2. 빈 공간 다수 — aspect gate가 너무 엄격하면 페리피럴 region이 어느
   방의 게이트도 통과 못해 orphan으로 남음. 두 문제는 같은 뿌리:
   bbox aspect 단일 게이트로는 좋은 모양을 표현 못함.
```

Round 4는 **(a) seed 자동 배치** + **(b) cut_history 기반 rectangle 게이트**로
교체. 빈 공간은 의도적으로 corridor 단계까지 보류 (spec §"unassigned
regions are what spine-first will turn into corridor"와 일치).

##### Decisions (locked in)

| 항목 | 결정 |
|---|---|
| Hub election | region_graph degree centrality, tie-break: area DESC |
| "각 부분" 단위 | **Territory** (`resolve_territories` 결과). Connected component보다 강함. Hole 케이스는 1 territory, multi-part(22, 23, 28, 29)는 다 territory. |
| Territory 수 > K | 살아있는 territory를 면적 DESC로 정렬, top K만 채택. 나머지 territory의 region은 unassigned (corridor 후보). |
| Seed 잔여 배치 | Region-hop FPS, tie-break: area DESC |
| `RoomSpec.seed_position` | `tuple | None` — None이면 자동 배치 |
| 사각형 정의 | **cut_history boundary cancellation** (아래 §Rectangle gate) |
| Cross-theta-group 흡수 | **금지** — wing은 자기 territory에서 자라거나 unassigned |
| Seed region 초기 비-사각형 | 그대로 인정 (v1). 확장 후 사각형성만 검사 |

##### Seed auto-placement

```text
Phase A — Hub (has_public인 경우만; K=2는 skip)
  전체 region 중 (degree DESC, area DESC) → hub seed

Phase B — Territory coverage
  surviving_territories를 면적 DESC로 정렬
  top min(len(territories), K)개를 선택
  hub_seed의 territory는 이미 채워졌다고 간주
  나머지 선택된 territory 각각:
    territory 내 (degree DESC, area DESC) → forced seed

Phase C — FPS for remaining
  while len(seeds) < K:
    candidates = (선택된 territory들의 unseeded regions)
    pick argmax_{c} min_{s in seeds} hop_distance(c, s)  # region_graph 위
    tie-break: area DESC
```

##### Rectangle gate (cut_history 기반)

핵심 정의:

```text
room_boundary_cuts(room_regions) -> {axis: sorted coords}
  1. room 내 모든 region.cut_history 좌표를 axis별로 모음.
  2. 각 cut (axis, c)에 대해, 그 cut를 따라 인접한 두 region이
     모두 room 내에 있으면 cancel (internal cut, room 경계 아님).
     인접 판정은 region_graph edge metadata로 한다.
  3. 남은 좌표가 room의 boundary cut.

is_rectangle(room_regions) ⟺
  len(boundary_cuts["axis_x"]) ≤ 2 AND
  len(boundary_cuts["axis_y"]) ≤ 2
  (2개 미만은 piece 외곽선에 의해 implicit하게 닫힘)
```

흡수 게이트:

```text
gate(R, C):
  (a) cross-theta 금지:   R.theta_group == C.theta_group
  (b) hub-connectivity:    기존 D011 유지
  (c) rectangle 유지:      is_rectangle(R.regions ∪ {C})
  (d) role aspect range:   기존 hard gate 유지
```

랭킹: `shared_boundary_length DESC` (기존 유지). v2에서는 cut-aligned
bonus 없이 게이트만으로 사각형성을 강제하는지 본다.

##### Work items (W1–W7)

각 항목 = 별도 commit, no-squash로 보존.

```text
W1  centrality + territory 매핑 헬퍼
    region_to_territory, region_degree, pick_top_centrality
    tests: case 22, 23, 28, 29

W2  auto_place_seeds(shape, region_graph, territories, K, has_public)
    Phase A/B/C 구현
    tests: 단일 territory, multi-part, territory 수 > K, K=2

W3  RoomSpec.seed_position: tuple | None
    fixture validation 갱신, 기존 33 fixture 호환

W4  cut_history rectangle gate
    room_boundary_cuts cancel 로직 (region_graph adjacency 활용)
    is_rectangle_after(room, candidate)
    tests: 합성 mini case + case 13 cross + case 18 rotated

W5  region_unit_greedy v2 wire-up
    필터에 cross-theta + rectangle gate 추가
    기존 smoke test 통과 + 새 invariant tests

W6  33-case 시각화 재생성, Round 3와 side-by-side 검수

W7  메모리 + Current Status 업데이트
```

##### Branch / merge

```text
main
 ├─ phase-7-region-unit-greedy   (Round 1-3 archive)
 └─ phase-7-rect-growth          (Round 4, this branch)

W6 검수 후:
  통과 → phase-7-rect-growth → main (no-ff)
         phase-7-region-unit-greedy archive 태그 (선택)
  실패 → 브랜치 폐기 또는 experiment/ 이동
         phase-7-region-unit-greedy → main (Round 3 baseline 채택)
```

##### Known risk

`room_boundary_cuts` cancel 로직이 가장 까다로움. cut_history는 좌표만
저장하지 "어느 쪽에 누가 있는지" 정보가 없어, 두 region이 정말 그 cut를
따라 인접한지는 region_graph edge에서 다시 확인해야 함. W4 시작 시점에
`RegionEdge` metadata에 cut-aligned 정보(`shared_axis`, `shared_coord`)가
즉시 추출 가능한지 검토. 없으면 atom_graph까지 한 단계 내려갈 가능성.

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

## Current Status

Phases 1–6 stable on `main`. Phase 7 Rounds 1–3 (schema + fixtures +
`region_unit_greedy` v1 + layout visualization) on branch
`phase-7-region-unit-greedy`, not yet merged. Phase 7 Round 4
(rect-preserving growth) in progress on branch `phase-7-rect-growth`
— see §Phase 7 / Round 4 above.

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
celllayout_tf/layout_fixtures.py     # Round 1
celllayout_tf/room_growth.py         # Round 2 (v1), Round 4 (v2)
celllayout_tf/viz.py
```

Implemented phases of `demos/visualize_phase.py`:
`input`, `territory`, `atom`, `graph`, `region`, `region_graph`,
`dimensions`, `layout`.

Run:

```text
cd /workspace/Study_RoomLayout_Cell/algorithm_testfield
PYTHONPATH=. pytest -q tests
PYTHONPATH=. python demos/visualize_phase.py --phase region
PYTHONPATH=. python demos/visualize_phase.py --phase region_graph 13 17 24
```
