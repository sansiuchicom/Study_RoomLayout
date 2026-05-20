# RoomLayoutCell Algorithm

Algorithm pipeline for the scan-to-BIM room-layout data generator (promoted
from the original `algorithm_testfield/` after Phase 8 — see the historical
context in §"Key Shift from the Previous Iteration" below).

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
algorithm/
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

Round 4는 **(a) seed 자동 배치** + **(b) reflex-count + 전역 L 슬롯 shape
게이트**로 교체. 빈 공간은 의도적으로 corridor 단계까지 보류 (spec
§"unassigned regions are what spine-first will turn into corridor"와 일치).

§Rectangle gate (cut_history 기반) 초기안은 §Shape gate로 대체되었다 —
같은 geometric 검사를 더 단순하게 표현 (Phase 5 region이 이미 local frame
axis-aligned 사각형이므로 cut_history cancel 회계는 over-engineering).

##### Decisions (locked in)

| 항목 | 결정 |
|---|---|
| Hub election | region_graph degree centrality, tie-break: area DESC |
| "각 부분" 단위 | **Territory** (`resolve_territories` 결과). Connected component보다 강함. Hole 케이스는 1 territory, multi-part(22, 23, 28, 29)는 다 territory. |
| Territory 수 > K | 살아있는 territory를 면적 DESC로 정렬, top K만 채택. 나머지 territory의 region은 unassigned (corridor 후보). |
| Seed 잔여 배치 | Region-hop FPS, tie-break: area DESC |
| `RoomSpec.seed_position` | `tuple | None` — None이면 자동 배치 |
| 모양 검사 | **Reflex vertex count of local-frame union** (아래 §Shape gate) |
| L 슬롯 정책 | 전역 `max_l_rooms` (fixture, default 2) — hub도 같은 풀 공유 |
| T/U/Z/+ 모양 | **never OK** (reflex ≥ 2 즉시 거부) |
| 더 깊은 L | 한 방이 이미 L (reflex=1) 인 채로 더 자라기 OK (슬롯 추가 소모 X, 결과 reflex=1 유지하면) |
| Cross-theta-group 흡수 | **금지** — wing은 자기 territory에서 자라거나 unassigned |
| Curved territory | 사각형 게이트 면제 (다른 gate들만 작동) |
| Seed region 초기 비-사각형 | 그대로 인정 (v1). 확장 후 reflex만 검사 |

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

##### Shape gate (reflex-count + global L budget)

Phase 5 regionize가 모든 region을 local-frame axis-aligned 사각형으로
생산하므로, room의 모양은 local-frame union의 **reflex(오목) vertex
개수** 로 충분히 표현된다.

```text
reflex_count(local_union):
  0  → axis-aligned 사각형          (always OK)
  1  → L자                          ("L 슬롯" 1개 소모, 전역 max_l_rooms 까지)
 ≥2  → T자 / U자 / Z자 / +자 등    (never OK)
```

L 슬롯은 fixture의 ``max_l_rooms`` (default 2) 까지 전역 공유. hub도 같은
풀에서 점유 — 따로 면제 없음. 이미 L인 방이 더 깊은 L (여전히 reflex=1)
로 자라는 건 새 슬롯 소모 없이 허용. L → rect 복원 (코너 채우기) 도 가능
하며 슬롯이 회수된다.

흡수 게이트 (3-layer):

```text
gate(room_idx, room_region_ids_after, rooms_state_before, regions_by_id,
     kind_by_part, max_l_rooms) -> bool:

  Layer 1 — cross-theta
    room_region_ids_after 안의 모든 region이 같은 theta-group인가?
    아니면 즉시 False (회전 wing 흡수 금지).

  Layer 2 — curved exemption
    하나라도 territory.kind == "curved" 인 region이 포함되면 True 즉시
    리턴. 곡선 territory는 reflex 검사 무의미하므로 다른 gate들
    (hub-connectivity, role aspect) 만으로 제어.

  Layer 3 — reflex + L budget
    new_reflex = reflex_count(union_in_local_frame)
    if new_reflex == 0:        return True
    if new_reflex >= 2:        return False
    # new_reflex == 1 (L 자)
    if 이미 L 이었던 방:        return True   # 슬롯 추가 소모 X
    other_l_count = (다른 방 중 reflex >= 1 개수)
    return other_l_count < max_l_rooms
```

Geometric union:

```text
union(region.shape rotated by -theta, for region in room_region_ids_after)
→ shapely Polygon (MultiPolygon이면 disconnected — reflex sentinel로 거부)

count_reflex(union.exterior, CCW-oriented):
  각 vertex (a, b, c) at index i in exterior coords:
    cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
    if cross < -1e-9:   reflex 증가
```

랭킹: `shared_boundary_length DESC` (기존 유지). reflex==0 후보가
reflex>=1 후보보다 자연스럽게 더 자주 게이트 통과 → 추가 ranking 조정
불필요.

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

W4  shape gate (cross-theta + curved exempt + reflex/L-budget)
    celllayout_tf/shape_gate.py — count_reflex_vertices, make_shape_gate
    fixture LayoutFixture.max_l_rooms 필드 추가
    tests: 합성 (rect/L/T/+) reflex 카운트, 전역 budget 동작

W5  region_unit_greedy v2 wire-up
    필터에 shape_gate 추가, auto-seed 분기 추가
    rooms_state를 게이트에 전달 (L 슬롯 카운트용)
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

##### Known risks

1. **Phase 5 region rectangularity** — Layer 3 reflex 검사는 각 region이
   local frame에서 axis-aligned 사각형이라는 promise에 의존. 곡선 piece
   안 region은 Layer 2가 면제하지만, axis-aligned/rotated piece의 region
   중 비-rect가 있으면 그 region이 들어간 방은 무조건 reflex 게이트 위
   ≥ 0 추가 vertex를 가지게 되어 게이트 동작 왜곡. W4 시작 시 검증
   테스트로 33-case × all regions 의 (local_frame 회전 후) rect 여부
   sanity check.

2. **Greedy ordering 의존성** — L 슬롯이 "선착순". 한 방이 슬롯을 먼저
   소비하면 후순위 방은 L 못 됨. 결과 품질이 흡수 순서에 따라 달라짐.
   v1에서는 수용. 결과 시각 검수 후 필요 시 후처리 swap 로직 도입 고려.

#### Round 4 v2 — Voronoi-priority pivot (W6+)

W5 결과 검수 후 두 가지 회의:

1. **확장이 일찍 멈춤** — single-region greedy가 strip 단위 흡수 기회를
   못 봄. 부분 흡수 = L → L 슬롯 소진 후 saturated. 결과적으로
   unassigned 비율 높음.
2. **L-budget + reflex-count는 magic** — fixture에 박힌 `max_l_rooms`,
   reflex-tier(0/1/2+) 등 사실상 multi-criteria scoring. 학계 정직성
   기준에서 정당화 약함 (proto3 D005 정신, README §Phase 7 "Magic /
   scoring 회피"와 직접 충돌).

→ 알고리즘 자체를 **bounded Voronoi + outward-vector 기반 priority
growth** 로 교체. 모든 의사결정은 hard gate + 단일 tie-break.

##### 알고리즘 정리

```text
사전 계산 (per fixture, 한 번):
  per territory T:
    bounded Voronoi of T's seeds (multi-source BFS on T's induced
      region graph; hop distance; tie: seed_id ASC)
    per seed s:
      anchor =
        multi-seed cell: length-weighted centroid of s's cell's
                         internal edges (in T's theta-local frame)
        single-seed:     T's centroid (local frame)
        ambiguous (no internal edges, or |outward| < eps):
                         hash-based perturbation seeded by seed_id
                         (deterministic)
      outward_vector = seed_centroid - anchor                (local frame)
      side_priority (4-tier):
        dominant_out   = side along the larger |outward| axis (sign +)
        secondary_out  = side along the smaller |outward| axis (sign +)
        secondary_in   = opposite of secondary_out
        dominant_in    = opposite of dominant_out

성장 (round-based):
  while progress in last round:
    for each room R (round-robin order, e.g., by current area ASC):
      for side in R's side_priority order:
        strip = candidate regions adjacent to R's bbox on `side`,
                whose union with R yields a clean rect (= bbox-equiv)
                AND fits inside R's territory (cell-membership check)
        if strip is None: continue (next side)
        check aspect gate (mid-of-role range, hard)
        check hub gate (D011, hard)
        if pass: mark cells of `strip` as R's proposed
                 break out of side loop
      if no side advanced R: R saturated this round
    end-of-round conflict resolution:
      for each cell proposed by 2+ rooms:
        winner = hub if any, else smallest-area room
        losers retry next priority side same round
    if no room moved: stop

Phase 2 (잔여 흡수): skip v1 — 결과 보고 결정
```

##### 핵심 hard gates

| Gate | 정의 |
|---|---|
| **Strip rect 유지** | union(room ∪ strip) area == bbox(union) area (within tolerance) |
| **Territory 포함** | strip의 각 region이 room의 territory에 속함 (part_id 일치) |
| **Aspect 범위** | role_aspect_ranges[role] 이내 |
| **Hub-connectivity** | strip 흡수 후 모든 방이 hub 도달 가능 (D011) |

Tie-break: 단일 — strip area DESC (같은 side 후보 중)

Magic 없음, weight 없음, reflex/L 슬롯/cut_history cancel 없음.

##### W6 work items

```text
W6a  growth_priority.py — bounded Voronoi + anchor + outward + side priority
     (사전 계산 only, 라운드 루프는 W6c)
W6b  strip extension (region-level) + bbox-in-territory check
W6c  round-based priority growth + proposal conflict resolution
W6d  wire-up — region_priority_growth() entry, layout viz call site swap
     (기존 region_unit_greedy 보존, viz는 새 함수로)
W6e  33-case 재생성 + Round 3/4 v1/v2 비교 montage
```

W4 shape_gate 코드는 보존 (사용 안 함 — 후속 평가에 참조용). W5
`region_unit_greedy`도 보존 (regression baseline 비교용). 검증 완료 후
W7에서 deprecation 또는 제거 결정.

##### Region-level의 한계 (인지)

Phase 5 region들의 outer edge가 좌표적으로 들쭉날쭉이면 strip이
clean rect 만들기 어려움 → 변 막힘 → unassigned 늘어남. atom-level
격상은 결과 보고 W6e 이후 결정.

### Phase 8: Corridor Carving

Room placement이 끝난 layout 위에서, hub에서 모든 방으로 닿는 복도를
깎아내는 단계. 두 단계 + cleanup:

- **Stage 1 — Base corridor (hub-radial)**: hub 인접 체크 → A* on
  region_graph로 hub→target path 탐색 (boundary 우선, 작은 방 회피) →
  path 위 region carve.
- **Stage 2 — Detour shortcut**: 모든 페어의 `corridor_strict /
  map_dist` ratio 계산 → threshold (building type별 단일값, 거주=2.5)
  이상 페어 중 가장 큰 거 선택 → entrance에서 entrance로 strict A*
  (hub/corridor 통과 hard block으로 새 carve 강제) → loop/cycle 형성
  → 반복.
- **Cleanup**: 남은 unassigned region을 corridor → 인접 방 (aspect 정사각형
  우선) 순으로 흡수, 그래도 남으면 leftover로 표시.

입자 단위는 **region** (atom 0.3m 단위는 너무 좁아 thickness 로직 별도
필요; region 단변 0.4~2.0m가 자연스러운 복도 폭). Door 위치는 별도
phase로 미룸. 상세 스펙은 [PHASE8_Corridor.md](PHASE8_Corridor.md).

브랜치: `phase-8-corridor-carving`.

### Phase 9: Visualization + Metrics

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

Phases 1–7 merged to `master`. Phase 7 Round 4 v2 (partition growth
+ 3-stage absorption + aspect gate) shipped on branch
`phase-7-rect-growth` (merged) — see §Phase 7 / Round 4 v2 above.
Phase 8 (Corridor Carving) spec written, implementation pending on
branch `phase-8-corridor-carving` — see [PHASE8_Corridor.md](PHASE8_Corridor.md).

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
celllayout_tf/layout_fixtures.py
celllayout_tf/room_growth.py         # Round 2 (v1), Round 4 (v2)
celllayout_tf/growth_partition.py    # Round 4 v2 W7+
celllayout_tf/growth_priority.py     # Round 4 v2 W6 (priority experiment)
celllayout_tf/seed_placement.py      # Round 4 v2 W6/W8+
celllayout_tf/shape_gate.py
celllayout_tf/viz.py
```

Implemented phases of `demos/visualize_phase.py`:
`input`, `territory`, `atom`, `graph`, `region`, `region_graph`,
`dimensions`, `layout`.

Run:

```text
cd /workspace/Study_RoomLayout_Cell/algorithm
PYTHONPATH=. pytest -q tests
PYTHONPATH=. python demos/visualize_phase.py --phase region
PYTHONPATH=. python demos/visualize_phase.py --phase region_graph 13 17 24
```
