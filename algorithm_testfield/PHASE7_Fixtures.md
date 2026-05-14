# Phase 7 Fixtures — Seeded Room Growth

External input for the 33 testfield cases. Phase 7 algorithm consumes
these fixtures and produces a `GrowthResult` per case (see [README.md](README.md)
§ Phase 7).

**Scope of this file**: room count (K), role distribution, seed
coordinates, area constraints. Nothing else (no adjacency graph, no
hub designation, no corridor placeholder — those belong to later phases).

---

## Conventions

### K — number of rooms

Determined from footprint area, following Korean apartment평형 patterns:

| Footprint area (m²) | K | Korean reference |
|---|:---:|---|
| ≤ 60 | 2 | 원룸 (~18평 이하) |
| 60 – 90 | 3 | 투룸 LDK (~18–27평) |
| 90 – 120 | 4 | 표준 32평 |
| 120 – 150 | 5 | 40평대 |
| 150 – 200 | 6 | 45–60평 |
| > 200 | 7 | 60평+ |

### Role distribution per K

Roles are a 4-value subset of proto3 `Role` (`hub` / `corridor` are
excluded — they belong to spine/layout phases downstream):

| K | Distribution | Pattern |
|:---:|---|---|
| 2 | `private, wet` | 원룸 (방 + 욕실) |
| 3 | `public, private, wet` | LDK + 1방 + 욕실 |
| 4 | `public, private×2, wet` | LDK + 2방 + 욕실 |
| 5 | `public, private×3, wet` | LDK + 3방 + 욕실 |
| 6 | `public, private×3, wet×2` | LDK + 3방 + 욕실×2 |
| 7 | `public, private×3, wet×2, service` | 거실 + 3방 + 욕실×2 + 주방분리 |

### Naming

Room `name` is **domain-free** — `space_1, space_2, ..., space_K` in
listed order. `role` carries the only domain hint, kept as metadata.
The first room (`space_1`) is always the `public` room when K ≥ 3.

### Role aspect ranges

Per-role default `target_aspect_range` used by the algorithm when a
RoomSpec doesn't override its own. `target_aspect_range` is the
algorithm's only "shape constraint" knob, and it lives here in the
fixture — not inside the algorithm.

Following proto3 D005, the range is a **hard gate**: a candidate region
whose absorption would push the room's `bbox_aspect` outside the range
is rejected. The room may end up under `target_area` if no in-range
candidate exists — that's reported in diagnostics, not silently
worked around.

| role | default `target_aspect_range` | rationale |
|---|---|---|
| public | (1.0, 2.5) | LDK 거실 — 사각형 ~ 1:2.5 길쭉 (전면 발코니형) |
| private | (1.0, 2.0) | 침실 — 사각형 위주, 안방+드레스 통합 시 길쭉 |
| wet | (1.0, 2.0) | 욕실 — 사각형 위주, 변기-세면-욕조 일렬 |
| service | (1.0, 4.0) | 주방·다용도실 — 가늘고 긴 배치 흔함 |

All ranges start at 1.0 because `bbox_aspect = max_side / min_side` is
always ≥ 1 by definition.

`target_aspect_range = None` (in a RoomSpec) → algorithm ignores aspect
for that room and uses `shared_boundary_length` as the only tie-break.

The 33 case fixtures below all omit `target_aspect_range` → role
defaults apply. Override only when a case needs an unusual room shape
(none in the current set).

This is a first-pass set, intentionally on the loose side. Tighten
after the first visualization round if rooms come out too elongated.

### Seed position

A `(x, y)` coordinate in the footprint's local frame. Resolved at
runtime to the containing region (or atom, depending on algorithm) via
`Polygon.contains(Point)`. Coordinates are chosen by hand to:

- lie strictly inside the footprint (not on hole / not on boundary)
- be reasonably distributed across the footprint
- avoid clustering two seeds in the same region

### Area constraints

For every case:

- `target_area_each_m2 = footprint_area_m2 / K`  (uniform)
- `min_area_m2 = target × 0.5`
- `max_area_m2 = target × 1.5`

Note: footprint area below is approximate (computed by hand from
`cases.py` rect/disk parameters). The runtime should recompute it
from the actual `ShapeInput.parts` union and use that as authoritative.

---

## Summary table

| # | name | area (m²) | K | role distribution |
|---:|---|---:|:---:|---|
| 01 | 30평 판상형 | 140 | 5 | pub, pri×3, wet |
| 02 | 30평 ㄱ자 | 122 | 5 | pub, pri×3, wet |
| 03 | 40평 4-bay | 160 | 6 | pub, pri×3, wet×2 |
| 04 | 50평 ㄷ자 | 131 | 5 | pub, pri×3, wet |
| 05 | 타워형 | 122 | 5 | pub, pri×3, wet |
| 06 | Square 10×10 | 100 | 4 | pub, pri×2, wet |
| 07 | Long rect 20×6 | 120 | 4 | pub, pri×2, wet |
| 08 | Tall rect 6×20 | 120 | 4 | pub, pri×2, wet |
| 09 | ㄱ자 standard | 95 | 4 | pub, pri×2, wet |
| 10 | ㄱ자 thick | 124 | 5 | pub, pri×3, wet |
| 11 | ㄱ자 thin | 75 | 3 | pub, pri, wet |
| 12 | 7자 standard | 98 | 4 | pub, pri×2, wet |
| 13 | 十자 symmetric | 88 | 3 | pub, pri, wet |
| 14 | 十자 asymmetric | 69 | 3 | pub, pri, wet |
| 15 | T자 | 98 | 4 | pub, pri×2, wet |
| 16 | ㅁ자 small hole | 126 | 5 | pub, pri×3, wet |
| 17 | ㅁ자 big hole | 108 | 4 | pub, pri×2, wet |
| 18 | Rect rotated 30° | 96 | 4 | pub, pri×2, wet |
| 19 | Rect rotated 60° | 96 | 4 | pub, pri×2, wet |
| 20 | ㄱ자 rotated 30° | 95 | 4 | pub, pri×2, wet |
| 21 | 7자 rotated 45° | 88 | 3 | pub, pri, wet |
| 22 | Main + wing 25° | 116 | 4 | pub, pri×2, wet |
| 23 | Mirror wings | 126 | 5 | pub, pri×3, wet |
| 24 | 7자 angled | 48 | 2 | pri, wet |
| 25 | Circle r=6 | 113 | 4 | pub, pri×2, wet |
| 26 | Ellipse 10×6 | 100 | 4 | pub, pri×2, wet |
| 27 | Half circle | 57 | 2 | pri, wet |
| 28 | Curved ㄱ | 105 | 4 | pub, pri×2, wet |
| 29 | E자 | 132 | 5 | pub, pri×3, wet |
| 30 | ㄹ자 (zigzag) | 112 | 4 | pub, pri×2, wet |
| 31 | 비대칭 ㄱ | 62 | 3 | pub, pri, wet |
| 32 | 60평 큰 ㄱ자 | 242 | 7 | pub, pri×3, wet×2, svc |
| 33 | ㅁ자 + wing | 116 | 4 | pub, pri×2, wet |

(`pub` = public, `pri` = private, `wet` = wet, `svc` = service)

Total: K=2 × 2, K=3 × 5, K=4 × 16, K=5 × 8, K=6 × 1, K=7 × 1.

---

## Per-case fixtures

### Case 01 — 30평 판상형

Footprint: `rect(0, 0, 14, 10)`, area 140 m². K = 5, target = 28 m².  
Constraints: min 14, max 42.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (3.5, 5.0) |
| space_2 | private | (7.0, 7.5) |
| space_3 | private | (7.0, 2.5) |
| space_4 | private | (11.0, 7.5) |
| space_5 | wet | (11.0, 2.5) |

### Case 02 — 30평 ㄱ자

Footprint: `rect(0,0,8,10) + rect(8,0,14,7)`, area 122 m². K = 5, target = 24.4 m².  
Constraints: min 12.2, max 36.6.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (4.0, 5.0) |
| space_2 | private | (4.0, 8.0) |
| space_3 | private | (4.0, 2.0) |
| space_4 | private | (11.0, 5.0) |
| space_5 | wet | (12.0, 2.0) |

### Case 03 — 40평 4-bay

Footprint: `rect(0, 0, 16, 10)`, area 160 m². K = 6, target = 26.7 m².  
Constraints: min 13.3, max 40.0.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (3.0, 5.0) |
| space_2 | private | (8.0, 7.5) |
| space_3 | private | (13.0, 7.5) |
| space_4 | private | (13.0, 2.5) |
| space_5 | wet | (8.0, 2.5) |
| space_6 | wet | (3.0, 2.0) |

### Case 04 — 50평 ㄷ자

Footprint: `rect(0,0,16,3.8) + rect(0,6.2,16,10) + rect(0,3.8,4,6.2)`, area ≈ 131 m². K = 5, target = 26.2 m².  
Constraints: min 13.1, max 39.3.  
*Open center: x∈[4,16], y∈[3.8,6.2] is empty.*

| name | role | seed_position |
|---|---|---|
| space_1 | public | (2.0, 5.0) |
| space_2 | private | (5.5, 1.9) |
| space_3 | private | (10.0, 1.9) |
| space_4 | private | (10.0, 8.1) |
| space_5 | wet | (5.5, 8.1) |

### Case 05 — 타워형

Footprint: three overlapping rects, area ≈ 122 m². K = 5, target = 24.4 m².  
Constraints: min 12.2, max 36.6.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (4.0, 4.0) |
| space_2 | private | (8.0, 5.5) |
| space_3 | private | (11.5, 9.0) |
| space_4 | private | (12.0, 4.5) |
| space_5 | wet | (4.0, 1.0) |

### Case 06 — Square 10×10

Footprint: `rect(0, 0, 10, 10)`, area 100 m². K = 4, target = 25.0 m².  
Constraints: min 12.5, max 37.5.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (3.0, 7.0) |
| space_2 | private | (7.0, 7.0) |
| space_3 | private | (7.0, 3.0) |
| space_4 | wet | (3.0, 3.0) |

### Case 07 — Long rect 20×6

Footprint: `rect(0, 0, 20, 6)`, area 120 m². K = 4, target = 30.0 m².  
Constraints: min 15.0, max 45.0.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (3.0, 3.0) |
| space_2 | private | (8.0, 3.0) |
| space_3 | private | (13.0, 3.0) |
| space_4 | wet | (18.0, 3.0) |

### Case 08 — Tall rect 6×20

Footprint: `rect(0, 0, 6, 20)`, area 120 m². K = 4, target = 30.0 m².  
Constraints: min 15.0, max 45.0.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (3.0, 3.0) |
| space_2 | private | (3.0, 8.0) |
| space_3 | private | (3.0, 13.0) |
| space_4 | wet | (3.0, 18.0) |

### Case 09 — ㄱ자 standard

Footprint: `rect(0,0,12,5) + rect(0,5,5,12)`, area 95 m². K = 4, target = 23.75 m².  
Constraints: min 11.9, max 35.6.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (3.0, 2.5) |
| space_2 | private | (8.0, 2.5) |
| space_3 | private | (2.5, 8.0) |
| space_4 | wet | (2.5, 11.0) |

### Case 10 — ㄱ자 thick

Footprint: `rect(0,0,14,5) + rect(0,5,6,14)`, area 124 m². K = 5, target = 24.8 m².  
Constraints: min 12.4, max 37.2.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (3.0, 2.5) |
| space_2 | private | (8.0, 2.5) |
| space_3 | private | (12.0, 2.5) |
| space_4 | private | (3.0, 9.0) |
| space_5 | wet | (3.0, 12.5) |

### Case 11 — ㄱ자 thin

Footprint: `rect(0,0,14,3) + rect(0,3,3,14)`, area 75 m². K = 3, target = 25.0 m².  
Constraints: min 12.5, max 37.5.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (5.0, 1.5) |
| space_2 | private | (1.5, 8.0) |
| space_3 | wet | (11.0, 1.5) |

### Case 12 — 7자 standard

Footprint: `rect(0,7,14,12) + rect(10,0,14,7)`, area 98 m². K = 4, target = 24.5 m².  
Constraints: min 12.25, max 36.75.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (5.0, 9.5) |
| space_2 | private | (11.0, 9.5) |
| space_3 | private | (12.0, 4.0) |
| space_4 | wet | (12.0, 1.5) |

### Case 13 — 十자 symmetric

Footprint: `rect(0,4,14,8) + rect(5,0,9,12)`, area 88 m². K = 3, target = 29.3 m².  
Constraints: min 14.7, max 44.0.  
*Cross arms — 3 seeds fill center + 2 horizontal arms; vertical arms get absorbed.*

| name | role | seed_position |
|---|---|---|
| space_1 | public | (7.0, 6.0) |
| space_2 | private | (2.0, 6.0) |
| space_3 | wet | (12.0, 6.0) |

### Case 14 — 十자 asymmetric

Footprint: `rect(0,4,14,7) + rect(6,0,9,12)`, area 69 m². K = 3, target = 23.0 m².  
Constraints: min 11.5, max 34.5.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (7.5, 5.5) |
| space_2 | private | (2.0, 5.5) |
| space_3 | wet | (12.0, 5.5) |

### Case 15 — T자

Footprint: `rect(0,0,14,5) + rect(5,5,9,12)`, area 98 m². K = 4, target = 24.5 m².  
Constraints: min 12.25, max 36.75.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (7.0, 2.5) |
| space_2 | private | (2.0, 2.5) |
| space_3 | private | (7.0, 8.5) |
| space_4 | wet | (12.0, 2.5) |

### Case 16 — ㅁ자 small hole

Footprint: `rect(0,0,14,10) hole(4.5,3,8.5,6.5)`, area 126 m². K = 5, target = 25.2 m².  
Constraints: min 12.6, max 37.8.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (2.0, 5.0) |
| space_2 | private | (6.5, 1.5) |
| space_3 | private | (6.5, 8.5) |
| space_4 | private | (12.0, 7.5) |
| space_5 | wet | (12.0, 2.5) |

### Case 17 — ㅁ자 big hole

Footprint: `rect(0,0,14,10) hole(3,3,11,7)`, area 108 m². K = 4, target = 27.0 m².  
Constraints: min 13.5, max 40.5.  
*Big hole — narrow rim. Seeds on the four sides.*

| name | role | seed_position |
|---|---|---|
| space_1 | public | (1.5, 5.0) |
| space_2 | private | (7.0, 1.5) |
| space_3 | private | (12.5, 5.0) |
| space_4 | wet | (7.0, 8.5) |

### Case 18 — Rect rotated 30°

Footprint: `rect(0,0,12,8)` rotated 30° around (6,4), area 96 m². K = 4, target = 24.0 m².  
Constraints: min 12.0, max 36.0.  
*Seeds clustered near rotation center to stay safely inside.*

| name | role | seed_position |
|---|---|---|
| space_1 | public | (4.5, 3.0) |
| space_2 | private | (7.5, 3.0) |
| space_3 | private | (4.5, 5.0) |
| space_4 | wet | (7.5, 5.0) |

### Case 19 — Rect rotated 60°

Footprint: `rect(0,0,12,8)` rotated 60° around (6,4), area 96 m². K = 4, target = 24.0 m².  
Constraints: min 12.0, max 36.0.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (4.5, 3.0) |
| space_2 | private | (7.5, 3.0) |
| space_3 | private | (4.5, 5.0) |
| space_4 | wet | (7.5, 5.0) |

### Case 20 — ㄱ자 rotated 30°

Footprint: ㄱ rotated 30° around its union centroid (≈4.71, 4.71), area 95 m². K = 4, target = 23.75 m².  
Constraints: min 11.9, max 35.6.  
*Seeds near centroid; verify each lies inside the rotated polygon at load time.*

| name | role | seed_position |
|---|---|---|
| space_1 | public | (4.5, 4.0) |
| space_2 | private | (5.5, 6.0) |
| space_3 | private | (3.0, 5.0) |
| space_4 | wet | (6.0, 2.5) |

### Case 21 — 7자 rotated 45°

Footprint: 7자 rotated 45° around its union centroid, area 88 m². K = 3, target = 29.3 m².  
Constraints: min 14.7, max 44.0.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (8.0, 6.0) |
| space_2 | private | (4.0, 8.0) |
| space_3 | wet | (10.0, 4.0) |

### Case 22 — Main + wing 25°

Footprint: `rect(0,0,12,8)` + rotated wing (5×4) translated to (9,7), rot 25°, area ≈ 116 m². K = 4, target = 29.0 m².  
Constraints: min 14.5, max 43.5.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (4.0, 4.0) |
| space_2 | private | (8.0, 4.0) |
| space_3 | private | (11.5, 8.5) |
| space_4 | wet | (4.0, 1.5) |

### Case 23 — Mirror wings ±30°

Footprint: `rect(0,0,12,8)` + 2 rotated wings, area ≈ 126 m². K = 5, target = 25.2 m².  
Constraints: min 12.6, max 37.8.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (4.0, 4.0) |
| space_2 | private | (8.0, 4.0) |
| space_3 | private | (0.0, 7.5) |
| space_4 | private | (12.0, 9.0) |
| space_5 | wet | (4.0, 1.5) |

### Case 24 — 7자 angled (−25° + 0°)

Footprint: 2 rotated rects forming a small angled 7, area ≈ 48 m². K = 2, target = 24.0 m².  
Constraints: min 12.0, max 36.0.  
*K=2 원룸 pattern: 침실 + 욕실.*

| name | role | seed_position |
|---|---|---|
| space_1 | private | (8.0, 4.0) |
| space_2 | wet | (4.0, 9.0) |

### Case 25 — Circle r=6

Footprint: disk at origin r=6, area ≈ 113 m². K = 4, target = 28.3 m².  
Constraints: min 14.1, max 42.4.  
*Seeds inside the circle (clearly within r=6 from origin).*

| name | role | seed_position |
|---|---|---|
| space_1 | public | (-2.5, 2.5) |
| space_2 | private | (2.5, 2.5) |
| space_3 | private | (-2.5, -2.5) |
| space_4 | wet | (2.5, -2.5) |

### Case 26 — Ellipse 10×6

Footprint: ellipse centered at origin, xfact=8, yfact=4, area ≈ 100 m². K = 4, target = 25.0 m².  
Constraints: min 12.5, max 37.5.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (-3.5, 1.5) |
| space_2 | private | (3.5, 1.5) |
| space_3 | private | (-3.5, -1.5) |
| space_4 | wet | (3.5, -1.5) |

### Case 27 — Half circle r=6

Footprint: top half of disk centered at origin r=6, area ≈ 57 m². K = 2, target = 28.5 m².  
Constraints: min 14.25, max 42.75.

| name | role | seed_position |
|---|---|---|
| space_1 | private | (-2.5, 2.5) |
| space_2 | wet | (2.5, 2.5) |

### Case 28 — Curved ㄱ

Footprint: `rect(0,0,4,14) + rect(4,0,13,4) + disk(4,4,4)`, area ≈ 105 m². K = 4, target = 26.25 m².  
Constraints: min 13.1, max 39.4.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (2.0, 8.0) |
| space_2 | private | (2.0, 12.0) |
| space_3 | private | (8.5, 2.0) |
| space_4 | wet | (12.0, 2.0) |

### Case 29 — E자

Footprint: `rect(0,0,5,12) + rect(5,0,14,3) + rect(5,5,14,8) + rect(5,10,14,12)`, area 132 m². K = 5, target = 26.4 m².  
Constraints: min 13.2, max 39.6.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (2.5, 8.0) |
| space_2 | private | (9.0, 1.5) |
| space_3 | private | (9.0, 6.5) |
| space_4 | private | (9.0, 11.0) |
| space_5 | wet | (2.5, 3.0) |

### Case 30 — ㄹ자 (zigzag)

Footprint: `rect(0,8,14,12) + rect(11,0,14,12) + rect(0,0,11,4)`, area 112 m². K = 4, target = 28.0 m².  
Constraints: min 14.0, max 42.0.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (5.0, 10.0) |
| space_2 | private | (5.0, 2.0) |
| space_3 | private | (12.5, 6.0) |
| space_4 | wet | (9.0, 2.0) |

### Case 31 — 비대칭 ㄱ

Footprint: `rect(0,0,14,3) + rect(0,3,2.2,12)`, area ≈ 62 m². K = 3, target = 20.6 m².  
Constraints: min 10.3, max 30.9.  
*Very thin vertical arm (2.2m wide).*

| name | role | seed_position |
|---|---|---|
| space_1 | public | (6.0, 1.5) |
| space_2 | private | (1.1, 7.0) |
| space_3 | wet | (12.0, 1.5) |

### Case 32 — 60평 큰 ㄱ자

Footprint: `rect(0,0,16,12) + rect(16,0,22,5) + rect(16,6,21,10)`, area 242 m². K = 7, target = 34.6 m².  
Constraints: min 17.3, max 51.9.  
*Largest case — full role distribution incl. service.*

| name | role | seed_position |
|---|---|---|
| space_1 | public | (4.0, 6.0) |
| space_2 | private | (10.0, 9.0) |
| space_3 | private | (13.0, 9.0) |
| space_4 | private | (13.0, 3.0) |
| space_5 | wet | (4.0, 2.0) |
| space_6 | wet | (19.0, 2.5) |
| space_7 | service | (18.5, 8.0) |

### Case 33 — ㅁ자 + wing

Footprint: `rect(0,0,12,10) hole(3,3,7,7) + rect(8,5,15,9)`, area ≈ 116 m². K = 4, target = 29.0 m².  
Constraints: min 14.5, max 43.5.

| name | role | seed_position |
|---|---|---|
| space_1 | public | (1.5, 5.0) |
| space_2 | private | (5.0, 1.5) |
| space_3 | private | (5.0, 8.5) |
| space_4 | wet | (13.0, 7.0) |

---

## Validation rules

When loading fixtures at runtime, the loader should verify:

```text
1. seed_position lies strictly inside the footprint (not on hole, not outside).
   - Failure → fixture error with case index + offending seed.
2. No two seeds resolve to the same region (region_unit_greedy) or atom
   (atom-level algorithms).
   - Failure → fixture error.
3. K matches len(rooms).
4. role count matches the declared distribution for K.
```

Seed coordinates above are picked by eye from `cases.py` rectangle/disk
parameters. Rotated cases (18, 19, 20, 21) and the curved case (28)
are the most likely to need adjustment after the first visualization
round.
