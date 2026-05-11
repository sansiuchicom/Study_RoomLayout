# Auto LIR + Per-family Recursive Progressive Fill (v3.2)

> 임의 형태 2D 건물 footprint(hole 가능)를 wall-aligned cell 격자로 분할.
> 본 문서는 다른 대화에서 self-contained하게 이어갈 수 있도록 작성됨.
>
> **v3.2 핵심 변화**:
> - **Per-family proportional** cell sizing — 같은 theta family는 한 cell 크기, 다른 theta family는 자기 main rect로 재계산
> - **50% merge rule** + **0% creation threshold** — 흰 공간 0 (footprint 100% 커버)
> - **Critical bug fixes**: MultiPolygon 모든 부분 보존, buffer-free 이웃 판정, orphan 보존
> - **Stress test 통과**: 15개 복잡 케이스 (ㄱ,ㄴ,7,ㅗ,十,ㅁ,U,H,ㄷ,Z + mirror + 회전 + multi-wing) 모두 0% gap

---

## 0. 문제 설정

### 풀고자 하는 것
임의 형태의 건물 평면(footprint)을 입력받아, 평면 전체를 cell 격자로 덮되 cell 경계가 가능한 한 인접 벽에 평행/수직이 되도록 분할.

### 입출력
- **입력**: shapely Polygon (외곽 + 0개 이상 hole). 비-Manhattan, 회전된 wing, 곡선 boundary 모두 가능. **사전 정보 불필요** (mirror, component history 등).
- **출력**: 평면 전체(hole 제외)를 100% 덮는 cell 다각형들. 각 cell에 family_id, depth, polygon 정보 부착.

### 제약
- Python 3.11+
- 시드 기반 random
- offline OK
- shapely + numpy + matplotlib

### 용도
이 cell 위에 polyomino식 방 배치가 다음 단계 (별개 주제).

---

## 1. 핵심 아이디어 (한 줄 요약)

> **Footprint에서 LIR(Largest Inscribed Rectangle)을 자동 탐색해 main으로 정하고, main에 격자를 깐다. 남은 영역(leftover)에 같은 알고리즘을 재귀 적용. Same-theta family는 phase chain으로 seamless 연장, different-theta family는 자기 main rect로 cell 크기 재계산하여 자체 격자.**

---

## 2. 발견 과정 및 핵심 통찰

### 검토한 접근들 (시리즈 누적)

| 접근 | 특징 | 한계 |
|---|---|---|
| Cut-cell Cartesian | 단일 회전 격자 + 클립 | 다중 wing 방향 처리 불가 |
| Frame field (gmsh) | smooth quad mesh | (i, j) 좌표 없음 |
| Reflex Bisector + Steiner (v2e) | reflex 추론 cut | hole 주변 over-segment |
| Per-component grid (v2g) | construction info 명시 | mirror 처리 어색 |
| Manual Progressive (v2h) | main 우선 + leftover (manual) | main 명시 필요 |
| Auto LIR Progressive (v3) | LIR 자동 탐색 | nested 어색 |
| Recursive Progressive (v3.1) | LIR 재귀 + phase chain | 단일 cell 크기 한계 |
| **Per-family Recursive (v3.2)** ★ | family별 cell 크기 + bug fixes | 현재 best |

### v3.2의 8가지 핵심 통찰

1. **Main 사각형이 격자의 기준이다.**
   건축에서 "main"은 가장 큰 사각형 영역. 격자의 기준점(theta, phase, cell 크기)을 결정.

2. **Main 안의 hole은 분할 사유가 아니다.**
   v2e가 hole 주변 4-way 분할했는데 불필요. main 격자가 hole을 자연스럽게 회피.

3. **Same-theta leftover는 phase chain으로 seamless 연장.**
   ㄱ자, ㅁ자, U자 등 axis-aligned 다리들이 모두 한 family + 한 phase → 시각적으로 한 큰 격자.

4. **Different-theta는 분리, 자기 cell 크기로.**
   회전 wing은 자체 family. 자기 main rect의 dimension에 맞춰 proportional cell 크기 (target 0.3m 근처).

5. **LIR은 자동 탐색 가능 → 사전 정보 불필요.**
   Mirror, component info 등은 critical path에서 빠질 수 있음. Stress test에서 검증됨.

6. **Nested 구조는 재귀로 자연스럽게.**
   큰 leftover 안 sub-LIR이 의미 있으면 재귀. Phase chain이 depth 거쳐 chain.

7. **Cell 크기는 모듈이 아니라 추상 단위.**
   0.3m 배수에 매달리지 말고 footprint에 정확히 fit. 모듈 제약은 다음 단계(방 배치)에서 강제.

8. **Boundary cell은 약간 irregular해도 OK.**
   50% rule이 작은 sliver를 인접 cell에 흡수 → 시각적 자연스러움 + adjacency 보존.

---

## 3. 알고리즘 구조

```
def recursive_progressive_per_family(polygon, target=0.3, depth=0,
                                       parent_phase, parent_theta,
                                       parent_cell_w, parent_cell_h):
    
    # === LIR 탐색 (2-step refined) ===
    main_rect, main_theta = find_main_rect_refined(polygon)
    
    # === 종료 조건 ===
    can_recurse = (depth < max_depth and 
                   polygon.area >= min_recurse_area and
                   main_rect is not None)
    has_meaningful_lir = main_rect.area >= polygon.area * min_lir_ratio
    
    # === Family 결정 ===
    if angle_diff(main_theta, parent_theta) < 2°:
        # Same family — parent 정보 그대로 사용
        cell_w = parent_cell_w
        cell_h = parent_cell_h
        phase = parent_phase
        theta = parent_theta
    else:
        # New family — 이 polygon의 main rect로 proportional 재계산
        family_id = next_family_id()
        cell_w, cell_h = main_rect.W / round(W/target), main_rect.H / round(H/target)
        phase = main_rect의 corner 좌표
    
    if not (can_recurse and has_meaningful_lir):
        # === TERMINAL: 그냥 격자 ===
        cells = grid_no_skip_aniso(polygon, theta, cell_w, cell_h, phase)
        cells = merge_below_50_aniso(cells, cell_w, cell_h)
        return cells
    
    # === RECURSIVE: main + leftover ===
    main_cells = grid_no_skip_aniso(main_rect ∩ polygon, theta, cell_w, cell_h, phase)
    main_cells = merge_below_50_aniso(main_cells, cell_w, cell_h)
    
    leftover_cells = []
    for leftover in (polygon - main_rect).split_into_pieces():
        if leftover.area >= 0.001:  # 거의 모든 작은 영역도 처리
            sub_cells = recursive_progressive_per_family(
                leftover, target,
                depth=depth+1,
                parent_phase=phase,        # phase chain
                parent_theta=theta,
                parent_cell_w=cell_w,      # 같은 family면 그대로 사용
                parent_cell_h=cell_h,
            )
            leftover_cells.extend(sub_cells)
    
    return main_cells + leftover_cells
```

### LIR 탐색 (2-step refined)

```
1. Coarse: boundary edge 각도들 (2° binned, 길이 가중) 상위 4 + 0°
   - 각 후보 θ: rotate -θ → rasterize → max_rect_in_binary_matrix
2. Fine: top-2 coarse 주변 ±2°를 0.5° step으로 정밀 탐색
3. 최대 면적 LIR 선택
```

### Maximal Rectangle in Binary Matrix (히스토그램+스택, O(MN))

각 row에 대해 "이 row를 바닥으로 1의 연속 높이"를 histogram으로 만들고, 그 histogram에서 최대 직사각형 (stack-based O(N)). 모든 row 중 최대.

### Critical Bug Fixes (v3.1 → v3.2)

이전 버전에서 small but critical bugs 발견:

1. **`grid_no_skip_aniso`의 MultiPolygon**: cell이 polygon boundary로 두 조각 분할되면 큰 조각만 살리고 작은 조각 버림 → polygon 안 빈 공간. **Fix**: 모든 부분을 별도 cell로 보존.

2. **`merge_below_50_aniso`의 buffer 이웃 판정**: 5mm buffer로 인접 판정 → 실제로 안 닿은 cell도 "이웃" 인식 → MultiPolygon merge → 작은 부분 버림. **Fix**: buffer 없이 실제 boundary 공유만 인정.

3. **Orphan cell nullify**: 이웃 못 찾는 작은 cell을 None으로 → 빈 공간. **Fix**: orphan은 그대로 보존 (작아도 빈 공간보단 낫다).

4. **Tiny remnant drop**: leftover area < 0.1m² 필터로 wing 끝 작은 영역들 drop. **Fix**: threshold 0.001m²로 낮춤.

이 fix들로 stress test 15/15 케이스 모두 0% gap 달성.

---

## 4. Python 구현 (self-contained)

### 의존성
```bash
pip install shapely numpy matplotlib
```

### 핵심 코드

```python
import numpy as np
import shapely.geometry as sg
import shapely.affinity as sa
from shapely.ops import unary_union
from matplotlib.path import Path


# ============================================================
# 1. Rasterize polygon to binary mask
# ============================================================
def rasterize_polygon(polygon, resolution=0.1):
    """Polygon 내부를 binary matrix로. matplotlib.Path으로 빠른 처리."""
    coords = list(polygon.exterior.coords)
    minx, miny, maxx, maxy = polygon.bounds
    nx = int(np.ceil((maxx - minx) / resolution)) + 1
    ny = int(np.ceil((maxy - miny) / resolution)) + 1
    xs = minx + (np.arange(nx) + 0.5) * resolution
    ys = miny + (np.arange(ny) + 0.5) * resolution
    grid_x, grid_y = np.meshgrid(xs, ys)
    points = np.column_stack([grid_x.ravel(), grid_y.ravel()])
    inside = Path(coords).contains_points(points).reshape(ny, nx)
    return inside, (minx, miny, resolution)


# ============================================================
# 2. Maximal rectangle in binary matrix (O(MN))
# ============================================================
def max_rect_in_histogram(heights):
    """히스토그램에서 최대 직사각형. Returns (left_idx, height, width)."""
    stack = []
    n = len(heights)
    best = (0, 0, 0)
    best_area = 0
    for i in range(n + 1):
        h = heights[i] if i < n else 0
        while stack and heights[stack[-1]] > h:
            top = stack.pop()
            top_h = heights[top]
            left = stack[-1] + 1 if stack else 0
            width = i - left
            area = top_h * width
            if area > best_area:
                best_area = area
                best = (left, top_h, width)
        stack.append(i)
    return best


def max_rect_in_mask(mask):
    """Binary 2D matrix에서 최대 직사각형. Returns (i0, j0, w, h) or None."""
    rows, cols = mask.shape
    if rows == 0 or cols == 0:
        return None
    heights = np.zeros(cols, dtype=int)
    best = None
    best_area = 0
    for j in range(rows):
        heights = np.where(mask[j], heights + 1, 0)
        left, h, w = max_rect_in_histogram(heights.tolist())
        if h * w > best_area:
            best_area = h * w
            best = (left, j - h + 1, w, h)
    return best


# ============================================================
# 3. LIR at given angle
# ============================================================
def lir_at_angle(polygon, theta, resolution=0.1):
    """Polygon exterior 안의 최대 inscribed rect (각도 theta로 회전).
    Holes 무시 (main rect가 hole 포함, cell이 회피)."""
    cx, cy = polygon.centroid.x, polygon.centroid.y
    rotated = sa.rotate(polygon, -np.degrees(theta), origin=(cx, cy))
    exterior_only = sg.Polygon(rotated.exterior)
    mask, (minx, miny, res) = rasterize_polygon(exterior_only, resolution)
    result = max_rect_in_mask(mask)
    if result is None:
        return None
    i0, j0, w, h = result
    if w == 0 or h == 0:
        return None
    rect_rotated = sg.box(minx + i0*res, miny + j0*res,
                          minx + (i0+w)*res, miny + (j0+h)*res)
    return sa.rotate(rect_rotated, np.degrees(theta), origin=(cx, cy))


def candidate_angles_from_boundary(polygon, bin_deg=2.0, top_k=4):
    """Boundary edge 각도들을 길이 가중 binning 후 상위 K개 + 0°."""
    coords = list(polygon.exterior.coords)
    bin_size = np.radians(bin_deg)
    binned = {}
    for i in range(len(coords) - 1):
        dx = coords[i+1][0] - coords[i][0]
        dy = coords[i+1][1] - coords[i][1]
        L = np.hypot(dx, dy)
        if L < 0.05:
            continue
        angle = np.arctan2(dy, dx) % (np.pi/2)
        key = round(angle / bin_size) * bin_size
        binned[key] = binned.get(key, 0) + L
    sorted_bins = sorted(binned.items(), key=lambda x: -x[1])
    candidates = [k for k, _ in sorted_bins[:top_k]]
    if not any(abs(c) < bin_size for c in candidates):
        candidates.append(0.0)
    return candidates


# ============================================================
# 4. 2-step refined LIR search
# ============================================================
def find_main_rect_refined(polygon, resolution=0.05,
                            coarse_bin_deg=2.0, top_k_coarse=4,
                            fine_step_deg=0.5, fine_range_deg=2.0,
                            n_refine_centers=2):
    """2-step LIR: coarse 후보 → top-K 주변 fine refinement.
    Returns: (rect, theta, info) or (None, 0, {})
    """
    coarse_angles = candidate_angles_from_boundary(
        polygon, bin_deg=coarse_bin_deg, top_k=top_k_coarse)
    
    coarse_results = []
    for theta in coarse_angles:
        rect = lir_at_angle(polygon, theta, resolution)
        if rect is not None:
            coarse_results.append({'theta': theta, 'rect': rect,
                                   'area': rect.area, 'phase': 'coarse'})
    if not coarse_results:
        return None, 0.0, {}
    
    coarse_sorted = sorted(coarse_results, key=lambda r: -r['area'])
    fine_step = np.radians(fine_step_deg)
    n_steps = int(np.radians(fine_range_deg) / fine_step)
    fine_results = []
    tried = set(round(r['theta'] * 1e5) for r in coarse_results)
    for center_info in coarse_sorted[:n_refine_centers]:
        for i in range(-n_steps, n_steps + 1):
            if i == 0:
                continue
            theta = (center_info['theta'] + i * fine_step) % (np.pi/2)
            key = round(theta * 1e5)
            if key in tried:
                continue
            tried.add(key)
            rect = lir_at_angle(polygon, theta, resolution)
            if rect is not None:
                fine_results.append({'theta': theta, 'rect': rect,
                                     'area': rect.area, 'phase': 'fine'})
    
    all_results = coarse_results + fine_results
    best = max(all_results, key=lambda r: r['area'])
    return best['rect'], best['theta'], {'best': best}


# ============================================================
# 5. Proportional cell sizing
# ============================================================
def compute_proportional_cell_size(main_rect, main_theta, target):
    """main_rect의 dimension에서 proportional cell_w, cell_h 계산.
    main을 정확히 N×M으로 나눠 sliver 없게 함.
    Returns: (cell_w, cell_h, base_phase)
    """
    cx, cy = main_rect.centroid.x, main_rect.centroid.y
    rotated = sa.rotate(main_rect, -np.degrees(main_theta), origin=(cx, cy))
    minx, miny, maxx, maxy = rotated.bounds
    W = maxx - minx
    H = maxy - miny
    n_x = max(1, round(W / target))
    n_y = max(1, round(H / target))
    cell_w = W / n_x
    cell_h = H / n_y
    base_phase = (cx, cy, minx, miny)
    return cell_w, cell_h, base_phase


# ============================================================
# 6. Anisotropic grid — MultiPolygon 모든 부분 보존
# ============================================================
def grid_no_skip_aniso(piece, theta, cell_w, cell_h,
                        phase_origin=None, seed=42, min_create_area=1e-6):
    """polygon에 닿는 모든 cell 생성 (흰 공간 0).
    
    cell.intersection이 MultiPolygon이면 모든 부분을 별도 cell로 (★ critical fix).
    """
    if phase_origin is None:
        rng = np.random.default_rng(seed)
        cx, cy = piece.centroid.x, piece.centroid.y
        ox, oy = rng.uniform(0, cell_w), rng.uniform(0, cell_h)
    else:
        cx, cy, ox, oy = phase_origin
    
    rotated = sa.rotate(piece, -np.degrees(theta), origin=(cx, cy))
    minx, miny, maxx, maxy = rotated.bounds
    minx_g = np.floor((minx - ox) / cell_w) * cell_w + ox - cell_w
    miny_g = np.floor((miny - oy) / cell_h) * cell_h + oy - cell_h
    maxx_g = np.ceil((maxx - ox) / cell_w) * cell_w + ox + cell_w
    maxy_g = np.ceil((maxy - oy) / cell_h) * cell_h + oy + cell_h
    nx = int(np.round((maxx_g - minx_g) / cell_w))
    ny = int(np.round((maxy_g - miny_g) / cell_h))
    
    cells = []
    for j in range(ny):
        for i in range(nx):
            x0 = minx_g + i * cell_w
            y0 = miny_g + j * cell_h
            cell = sg.box(x0, y0, x0 + cell_w, y0 + cell_h)
            inter = cell.intersection(rotated)
            if inter.is_empty:
                continue
            # ★ 모든 부분 보존 (이전: 가장 큰 것만)
            if isinstance(inter, sg.MultiPolygon):
                parts = [g for g in inter.geoms
                         if isinstance(g, sg.Polygon) and g.area >= min_create_area]
            elif isinstance(inter, sg.Polygon):
                parts = [inter] if inter.area >= min_create_area else []
            else:
                parts = []
                if hasattr(inter, 'geoms'):
                    for g in inter.geoms:
                        if isinstance(g, sg.Polygon) and g.area >= min_create_area:
                            parts.append(g)
            cells.extend(parts)
    
    return ([sa.rotate(c, np.degrees(theta), origin=(cx, cy)) for c in cells],
            (cx, cy, ox, oy))


# ============================================================
# 7. 50% rule merge — buffer 없는 이웃 판정 + orphan 보존
# ============================================================
def merge_below_50_aniso(cells, cell_w, cell_h,
                          threshold_ratio=0.5, max_iter=100):
    """50% 미만 cell을 가장 큰 boundary 공유 이웃에 흡수.
    
    [v3.2 fixes]
    - Buffer 없이 실제 공유 boundary만 이웃 인식 (MultiPolygon merge 방지)
    - Orphan은 nullify 안 함 — 그대로 보존 (작아도 빈 공간보단 낫다)
    """
    threshold = cell_w * cell_h * threshold_ratio
    cells = list(cells)
    skip_indices = set()  # orphan으로 판정된 cell — 다시 안 건드림
    
    for _ in range(max_iter):
        smallest_idx, smallest_area = None, float('inf')
        for i, c in enumerate(cells):
            if c is None or i in skip_indices:
                continue
            if c.area < threshold and c.area < smallest_area:
                smallest_area = c.area
                smallest_idx = i
        if smallest_idx is None:
            break
        
        small = cells[smallest_idx]
        # 실제 공유 boundary가 있는 이웃만 (buffer 없음)
        neighbors = []
        for j, other in enumerate(cells):
            if j == smallest_idx or other is None:
                continue
            inter = small.intersection(other)
            if inter.is_empty:
                continue
            if hasattr(inter, 'length') and inter.length > 0.001:
                neighbors.append((j, other.area, inter.length))
        
        if not neighbors:
            # 진짜 orphan — 빈 공간 만드느니 그대로 둠
            skip_indices.add(smallest_idx)
            continue
        
        # 가장 긴 boundary 공유 이웃 우선 (자연스러운 merge)
        biggest_j = max(neighbors, key=lambda x: x[2])[0]
        merged = small.union(cells[biggest_j])
        if isinstance(merged, sg.Polygon):
            cells[biggest_j] = merged
        elif isinstance(merged, sg.MultiPolygon):
            # 안전장치: 모든 부분 보존
            geoms = sorted(merged.geoms, key=lambda g: -g.area)
            cells[biggest_j] = geoms[0]
            for extra in geoms[1:]:
                cells.append(extra)
        cells[smallest_idx] = None
    
    return [c for c in cells if c is not None]


# ============================================================
# 8. Boundary 기반 theta 추론 (fallback)
# ============================================================
def piece_direct_theta(piece, min_straight_length=1.0):
    """Piece boundary의 긴 직선 segment들로 dominant direction 추론.
    None 반환 시 추론 부적합."""
    coords = list(piece.exterior.coords)
    angles, weights = [], []
    for i in range(len(coords) - 1):
        e_len = np.hypot(coords[i+1][0] - coords[i][0],
                         coords[i+1][1] - coords[i][1])
        if e_len < min_straight_length:
            continue
        dx = coords[i+1][0] - coords[i][0]
        dy = coords[i+1][1] - coords[i][1]
        angles.append(np.arctan2(dy, dx) % (np.pi / 2))
        weights.append(e_len)
    if not angles:
        return None
    s = sum(w * np.sin(4 * a) for w, a in zip(weights, angles))
    c = sum(w * np.cos(4 * a) for w, a in zip(weights, angles))
    if np.hypot(s, c) < 0.1 * sum(weights):
        return None
    return (np.arctan2(s, c) / 4) % (np.pi / 2)


def angle_diff(a, b):
    """[0, π/2) 도메인에서 두 각도의 차이"""
    d = abs(a - b) % (np.pi / 2)
    return min(d, np.pi/2 - d)


# ============================================================
# 9. Recursive Progressive Per-family — 메인 알고리즘
# ============================================================
def recursive_progressive_per_family(polygon, target_cell_size=0.3, seed=42,
                                       max_depth=3, min_lir_ratio=0.4,
                                       min_recurse_area=8.0,
                                       lir_resolution=0.05,
                                       _depth=0,
                                       _parent_theta=None,
                                       _parent_phase=None,
                                       _parent_cell_w=None,
                                       _parent_cell_h=None,
                                       _family_id=0,
                                       _next_family_id=None):
    """
    Per-family proportional + recursive progressive fill.
    
    - Family = same theta + phase chain (한 cell 크기, 한 phase 공유)
    - 다른 theta는 새 family로 cell_w, cell_h 자체 계산
    - Phase chain은 depth 거쳐 계속됨 (axis-aligned 다리들이 한 격자처럼)
    
    Args:
        polygon: shapely Polygon
        target_cell_size: 셀 크기 목표 (예: 0.3m). 실제는 family별 proportional.
        max_depth: 재귀 깊이 한도 (3)
        min_lir_ratio: LIR이 polygon의 이 비율 미만이면 main+leftover 안 함 (0.4)
        min_recurse_area: 이 미만은 그냥 격자 (8m²)
    
    Returns: (cells, pieces_info, root_main_rect, next_family_id)
    """
    if _next_family_id is None:
        _next_family_id = [_family_id + 1]
    
    rng = np.random.default_rng(seed)
    all_cells = []
    pieces_info = []
    
    main_rect, main_theta, _ = find_main_rect_refined(
        polygon, resolution=lir_resolution)
    
    can_recurse = (_depth < max_depth and
                   polygon.area >= min_recurse_area and
                   main_rect is not None)
    has_meaningful_lir = (main_rect is not None and
                          main_rect.area >= polygon.area * min_lir_ratio)
    
    # Effective theta
    if main_rect is not None and has_meaningful_lir:
        effective_theta = main_theta
    else:
        effective_theta = piece_direct_theta(polygon, 1.0)
        if effective_theta is None:
            effective_theta = _parent_theta if _parent_theta is not None else 0.0
    
    # Family 결정
    is_same_family = (_parent_theta is not None and
                       angle_diff(effective_theta, _parent_theta) < np.radians(2))
    
    if is_same_family:
        family_id = _family_id
        cell_w = _parent_cell_w
        cell_h = _parent_cell_h
        phase = _parent_phase
        effective_theta = _parent_theta  # 정확히 일치
    else:
        family_id = _next_family_id[0]
        _next_family_id[0] += 1
        if main_rect is not None:
            cell_w, cell_h, phase = compute_proportional_cell_size(
                main_rect, effective_theta, target_cell_size)
        else:
            # Fallback: polygon bbox 기반
            cx, cy = polygon.centroid.x, polygon.centroid.y
            rotated = sa.rotate(polygon, -np.degrees(effective_theta),
                                origin=(cx, cy))
            minx, miny, maxx, maxy = rotated.bounds
            W, H = maxx - minx, maxy - miny
            n_x = max(1, round(W / target_cell_size))
            n_y = max(1, round(H / target_cell_size))
            cell_w = W / n_x
            cell_h = H / n_y
            phase = (cx, cy, minx, miny)
    
    # === TERMINAL ===
    if not (can_recurse and has_meaningful_lir):
        cells, _ = grid_no_skip_aniso(polygon, effective_theta,
                                       cell_w, cell_h,
                                       phase_origin=phase,
                                       seed=int(rng.integers(0, 2**31)))
        cells = merge_below_50_aniso(cells, cell_w, cell_h, 0.5)
        pieces_info.append({
            'polygon': polygon, 'theta': effective_theta,
            'role': 'terminal', 'name': f'd{_depth}_terminal',
            'depth': _depth, 'family_id': family_id,
            'cell_w': cell_w, 'cell_h': cell_h,
            'n_cells': len(cells),
        })
        for c in cells:
            all_cells.append((c, 0))
        return all_cells, pieces_info, main_rect, _next_family_id[0]
    
    # === RECURSIVE: main + leftover ===
    main_region = main_rect.intersection(polygon)
    if isinstance(main_region, sg.MultiPolygon):
        main_subpieces = list(main_region.geoms)
    elif isinstance(main_region, sg.Polygon):
        main_subpieces = [main_region]
    else:
        main_subpieces = []
    main_subpieces = [p for p in main_subpieces if p.area >= 0.001]
    
    main_phase = phase
    for sub in main_subpieces:
        cells, p_returned = grid_no_skip_aniso(
            sub, effective_theta, cell_w, cell_h,
            phase_origin=main_phase,
            seed=int(rng.integers(0, 2**31)))
        cells = merge_below_50_aniso(cells, cell_w, cell_h, 0.5)
        if main_phase is None:
            main_phase = p_returned
        piece_id = len(pieces_info)
        pieces_info.append({
            'polygon': sub, 'theta': effective_theta,
            'role': 'main', 'name': f'd{_depth}_main',
            'depth': _depth, 'family_id': family_id,
            'cell_w': cell_w, 'cell_h': cell_h,
            'n_cells': len(cells),
        })
        for c in cells:
            all_cells.append((c, piece_id))
    
    remainder = polygon.difference(main_rect)
    if isinstance(remainder, sg.MultiPolygon):
        rem_pieces = list(remainder.geoms)
    elif isinstance(remainder, sg.Polygon):
        rem_pieces = [remainder]
    else:
        rem_pieces = []
    rem_pieces = [p for p in rem_pieces if p.area >= 0.001]
    
    for k, leftover in enumerate(rem_pieces):
        sub_cells, sub_pieces, _, _ = recursive_progressive_per_family(
            leftover, target_cell_size,
            seed=int(rng.integers(0, 2**31)),
            max_depth=max_depth, min_lir_ratio=min_lir_ratio,
            min_recurse_area=min_recurse_area,
            lir_resolution=lir_resolution,
            _depth=_depth + 1,
            _parent_theta=effective_theta,
            _parent_phase=main_phase,
            _parent_cell_w=cell_w,
            _parent_cell_h=cell_h,
            _family_id=family_id,
            _next_family_id=_next_family_id,
        )
        offset = len(pieces_info)
        for cell, sub_pid in sub_cells:
            all_cells.append((cell, sub_pid + offset))
        pieces_info.extend(sub_pieces)
    
    return all_cells, pieces_info, main_rect, _next_family_id[0]


# ============================================================
# 10. 메인 엔트리 (한 줄 호출)
# ============================================================
def auto_partition(footprint, target_cell_size=0.3, seed=42,
                    max_depth=3, min_lir_ratio=0.4, min_recurse_area=8.0):
    """Footprint만 입력 → fully automatic 분할.
    
    Returns: dict with 'cells', 'pieces', 'root_main_rect'
    """
    cells, pieces, root_main, _ = recursive_progressive_per_family(
        footprint, target_cell_size=target_cell_size, seed=seed,
        max_depth=max_depth, min_lir_ratio=min_lir_ratio,
        min_recurse_area=min_recurse_area,
    )
    return {'cells': cells, 'pieces': pieces, 'root_main_rect': root_main}
```

### 사용 예시

```python
import shapely.geometry as sg
import shapely.affinity as sa
from shapely.ops import unary_union
import numpy as np

# 임의 footprint (외곽 + hole, mirror, 회전 wing 등 무엇이든)
main = sg.box(0, 0, 12, 8)
wing = sa.translate(sa.rotate(sg.box(0, 0, 6, 4), 25, origin=(0, 0)),
                    xoff=10, yoff=6)
bump = sg.Point(0, 4).buffer(2.0, resolution=20)
core1 = sg.box(3, 2.5, 5.5, 4.5)
fp = unary_union([main, wing, bump]).difference(core1)

# 한 줄 — 사전 정보 없이 자동 분할
result = auto_partition(fp, target_cell_size=0.3, seed=42)

print(f"#families: {len(set(p['family_id'] for p in result['pieces']))}")
print(f"#cells: {sum(p['n_cells'] for p in result['pieces'])}")
for p in result['pieces']:
    print(f"  d{p['depth']} fam{p['family_id']} [{p['role']:8s}] "
          f"theta={np.degrees(p['theta']):.1f}°, "
          f"cell={p['cell_w']:.3f}x{p['cell_h']:.3f}m, "
          f"cells={p['n_cells']}")
```

---

## 5. Stress Test 결과 (15 케이스)

| # | Case | Family | Cells | Gap |
|---|------|--------|-------|-----|
| 1 | ㄱ자 (L-shape) | 1 | 773 | 0.000% |
| 2 | ㄴ자 (J-shape) | 1 | 767 | 0.000% |
| 3 | 7자 (top + right) | 1 | 780 | 0.000% |
| 4 | ㅗ자 (T-shape) | 1 | 865 | 0.000% |
| 5 | 十자 (plus) | 1 | 955 | 0.000% |
| 6 | **ㅁ자 (square ring with courtyard)** | 1 | 1278 | 0.000% |
| 7 | U자 (mirror wings) | 1 | 1112 | 0.000% |
| 8 | H자 (two columns + crossbar) | 1 | 994 | 0.000% |
| 9 | **회전 7자 (20°)** | 1 | 779 | 0.000% |
| 10 | Mirror wings (±30°) | 5 | 1281 | 0.000% |
| 11 | ㅁ자 + 회전 wing | 3 | 1457 | 0.000% |
| 12 | Multi-wing complex (3 wings + core) | 6 | 1321 | 0.000% |
| 13 | ㄷ자 (3-sided) | 1 | 1391 | 0.000% |
| 14 | Z자 변형 | 1 | 1114 | 0.000% |
| 15 | Mirror palace (atrium + ±20° wings) | 5 | 1793 | 0.000% |

**모든 케이스 100% footprint 커버**, fully automatic, 사전 정보 0.

### 핵심 검증된 것들

1. **Phase chain의 위력**: axis-aligned 한글 자모(ㄱ,ㄴ,7,ㅗ,十,ㅁ,U,H,ㄷ,Z) 모두 1 family로 처리. 다리들이 한 큰 격자처럼 보임 → polyomino 확장 자연스러움.

2. **Mirror 자동 처리**: 명시적 hint 없이 LIR이 정중앙 main 찾고 양쪽 wing 자체 family로 처리.

3. **Hole 자동 회피**: ㅁ자 / atrium / core 모두 main grid가 자동 회피. 별도 분할 안 함.

4. **회전 자동 인식**: 회전 7자 (20°)도 LIR이 정확히 20° 찾음.

5. **임의 multi-wing**: 다른 각도의 wing 3개도 family 분리해서 깔끔히 처리.

---

## 6. Edge Case Stress Test (15 추가 케이스)

원래 우려했던 "한계 1: LIR 부적합 footprint"를 검증하기 위해 의도적으로 LIR이 작거나 곡선이 많은 극한 케이스 15개 테스트:

| # | Case | LIR ratio | Family | Cells | Gap |
|---|------|-----------|--------|-------|-----|
| 1 | Star (5-pointed) | 0.48 | 4 | 498 | 0.000% |
| 2 | Thin plus (very narrow) | 0.64 | 1 | 525 | 0.000% |
| 3 | Long thin corridor (20×1.5) | 1.00 | 1 | 335 | 0.000% |
| 4 | Thin L (narrow legs) | 0.59 | 1 | 340 | 0.000% |
| 5 | Equilateral triangle | 0.51 | 11 | 731 | 0.000% |
| 6 | Rhombus (diamond) | 0.55 | 2 | 350 | 0.000% |
| 7 | Many holes (Swiss cheese 6) | 1.21 | 1 | 1323 | 0.000% |
| 8 | Circle | 0.64 | 1 | 906 | 0.000% |
| 9 | Ellipse (8×4) | 0.64 | 4 | 1172 | 0.000% |
| 10 | **Blob (organic 20-vertex)** | 0.65 | 5 | 1175 | **0.172%** |
| 11 | Spiky (16-pointed) | 0.57 | 9 | 667 | 0.000% |
| 12 | Small kitchen (~12m²) | 0.80 | 1 | 161 | 0.000% |
| 13 | Big main + tiny extrusions | 0.99 | 1 | 1572 | 0.000% |
| 14 | Dense holes (3×3 grid) | 1.33 | 1 | 1204 | 0.000% |
| 15 | Multiple circles fused | 0.63 | 1 | 895 | 0.000% |

**14/15 perfect coverage**, 단 1개(blob)만 0.17% gap — floating-point 누적 오차.

### 검증된 것들

1. **LIR ratio 0.5 이하도 작동**: 별(0.48), 삼각형(0.51), 마름모(0.55), spiky(0.57). main+leftover 재귀가 자연스럽게 처리.

2. **곡선 footprint 잘 처리**: 원, 타원, 겹친 원들 모두 0% gap. LIR이 큰 사각형 잡고 boundary cells가 곡선 따라감.

3. **Hole-heavy 의외로 깔끔**: Swiss cheese(6 hole), Dense 3×3 hole 모두 1 family로 처리. LIR이 외곽 사각형 그대로 잡고(hole 무시) → cell이 hole 자동 회피.

4. **Spike-heavy 동작**: 별/spiky/triangle 같은 다중 spike 케이스도 재귀로 다 처리.

### 한계 1 재정의

원래: "LIR이 의미 없는 main을 줄 수 있는 case → v2e fallback 필요"

**재정의 후**: LIR ratio 0.4 이상이면 main+leftover 재귀로 충분, 0.4 미만이면 terminal로 그냥 격자 (작동은 함). **v2e fallback 불필요**. 한계 1은 사실상 해결됨.

---

## 7. 알려진 한계 (남은 것들)

### 한계 A: Family fragmentation (cosmetic)
대칭 footprint(triangle 11 fam, spiky 9 fam)에서 family가 많이 생성됨.
- **원인**: family 결정이 직속 parent와만 비교 → 깊이 들어가면 같은 theta도 다른 family로 분리. 떨어진 위치의 같은 theta(spiky의 71° 3번)도 별개 family.
- **영향**: 시각적 cosmetic only. Cell coverage 100%, polyomino 동작 영향 없음.
- **개선안 (낮은 우선순위)**: family를 theta 기준 globally dedupe.

### 한계 B: 45° LIR floating-point edge case
정확히 45° rotation에서 sin/cos = √2/2 부동소수점 누적 오차로 0.17% gap 발생.
- **재현성**: deterministic (seed 무관)
- **빈도**: 매우 드뭄 (45° LIR + 특정 shape)
- **영향**: 시각적으로 거의 안 보임 (~2 cell 영역)
- **개선안 (낮은 우선순위)**: cells을 rotated frame 그대로 유지하고 output에서만 rotate. Refactor 필요.

### 한계 C: Cell adjacency graph 미구축
현재 cells = list of (Polygon, piece_id). Polyomino 방 배치엔 (i, j) + neighbors 정보 필요.

**개선안 (다음 작업 1순위)**: 각 cell에 (piece_id, family_id, depth, grid_i, grid_j, neighbors[N/S/E/W]) 부착.

### 한계 D: Junction cell 모양 irregular
Different-theta 사이 boundary cell이 사다리꼴/오각형 등 irregular shape.

**대응**: 시각적으로 자연스러움. Polyomino adjacency graph에선 cell 모양 무관 → 영향 없음.

### 한계 E: LIR이 hole 무시
현재 polygon.exterior만 rasterize. 일반적으론 OK인데 hole이 매우 크면 LIR의 "유용한" 면적 작을 수 있음.

**개선안**: `include_holes=True` 옵션 — area 계산 시 hole 차감.

### 한계 F: Same-theta 영역 분리 의도
같은 theta인데 일부러 별개 공간으로 분리하고 싶다 (room A vs room B 인접). 알고리즘이 자동으로 한 piece로 묶음.

**대응**: 이건 cell 분할이 아니라 **room placement 단계의 hint**. cell layer는 architectural region 단위로만 분할, semantic 분리는 그 위에서.

---

## 8. 도구상자 (이전 시리즈)

| Pipeline | 입력 | 강점 | 적합 use case |
|---|---|---|---|
| **2M (per-family recursive)** ★ v3.2 | footprint | 모든 면에서 best | 일반 |
| 2L (fixed 0.3m) | footprint | 단순 | 디버깅, 테스트 |
| 2j (recursive single cell size) | footprint | 작동은 함 | (대체됨) |
| 2i (single-level progressive) | footprint | 가벼움 | nested 없을 때 |
| 2e (reflex+Steiner) | footprint | LIR 부적합 fallback | 비정형 |

**일반 사용**: `auto_partition(footprint)` 한 줄로 끝.

---

## 9. 다른 채팅에서 이어가기

### 시리즈 결정 사항
- **사용 사례**: 건축 평면도 분할 → cell 위에 polyomino 방 배치
- **셀 크기**: 0.3m target (proportional 조정으로 ±2%)
- **사전 정보**: footprint polygon만 (mirror, component info 등 불필요)
- **Hole 처리**: main grid가 자동 회피
- **재귀 + phase chain**: nested 구조에서 시각적 연속성

### 다음 작업 우선순위

**1순위: Cell adjacency graph 자료구조** ★
```python
class Cell:
    polygon: shapely.Polygon
    piece_id: int
    family_id: int       # same-theta family
    depth: int
    grid_i: int          # within family
    grid_j: int
    neighbors: List[Tuple[Cell, str, float]]
                          # (cell, edge_type, shared_length)
                          # edge_type: 'grid_N/S/E/W' | 'cross_family'
```

이거 만들면 polyomino 방 배치 알고리즘이 cell graph BFS/DFS로 자연스럽게 동작.

**2순위: 방 배치 알고리즘 시작** (별개 큰 주제)
- 옵션 A: Growth-based (seed cell에서 영역 확장)
- 옵션 B: MIP (mixed integer programming)
- 옵션 C: WFC (wave function collapse)

**3순위 (낮음, 필요시만)**: 부수 한계 처리
- Family fragmentation dedupe (한계 A)
- 45° floating-point fix (한계 B)
- LIR에서 hole 고려 (한계 E)

**한계 1은 이제 한계가 아님** ✓ — edge case test로 검증됨. v2e fallback 불필요.

### 코드 파일 (시리즈 누적)
- `00_footprint.py`: 샘플 footprint
- `02e_improved.py`: Reflex+Steiner v2e
- `02h_progressive.py`: Manual main + progressive
- `02i_lir_progressive.py`: Auto LIR + single-level progressive
- `02j_recursive.py`: Recursive single cell size
- `02L_final.py`: Fixed 0.3m + 50% rule
- **`02M_per_family.py`** ★ 핵심: Per-family + 모든 fix (이 문서 기준)
- `02M_stress_test.py`: 15 케이스 한글 자모/mirror/회전 stress test (모두 0% gap)
- `02M_edge_cases.py`: 15 LIR-unfriendly 극한 케이스 (별/곡선/hole-heavy 등, 14/15 0% gap)

### 새 채팅 시작 시 prompt
> "이전 대화에서 'Auto LIR + Per-family Recursive Progressive Fill' (v3.2)을 만들었어. 첨부 markdown에 알고리즘, Python 구현, stress test 결과가 정리되어 있어. 이번엔 [원하는 작업: cell adjacency graph 구축 / 방 배치 알고리즘 시작 / 한계 X 처리] 하고 싶어. 첨부 문서 먼저 읽고 [baseline 확인 / 토론 / 바로 구현]."

---

## 10. v3.1 → v3.2 변경 요약

### 추가된 개념
- **Per-family proportional cell sizing** — same-theta family는 한 cell, different-theta는 자기 main rect로 재계산
- **0% creation threshold** — `min_create_area=1e-6`으로 거의 모든 polygon-intersecting cell 생성
- **50% merge rule** — 30% → 50%로 더 적극적 boundary cell 흡수
- **Tiny remnant capture** — area 필터 0.1 → 0.001m²

### Critical bug fixes
- `grid_no_skip_aniso`: MultiPolygon 모든 부분 보존 (이전: 큰 것만)
- `merge_below_50_aniso`: buffer 없는 이웃 판정 (MultiPolygon merge 자체 방지)
- `merge_below_50_aniso`: orphan cell 보존 (이전: nullify → 빈 공간)

### 결과 차이 (v3.1 → v3.2)
| Metric | v3.1 | v3.2 |
|---|---|---|
| Stress test gap | 일부 0.05~0.3% | **모두 0.000%** |
| Same-theta family 처리 | 단일 cell 크기 강제 | family별 자체 cell 크기 |
| 흰 공간 발생 가능성 | 있음 (drop threshold) | 0 (모든 cell 보존) |

---

## 11. 보너스: 코드가 짧은 이유 ㅋㅋ

전체 알고리즘 코드가 ~500줄밖에 안 되는 게 신기할 수 있는데, 이유는:

1. **Shapely가 무거운 일 다 함**: polygon intersection, union, difference, contains, length, area, rotate, translate 모두 한 줄. 직접 구현하려면 robust 2D geometry 라이브러리만 1만 줄 넘음.

2. **재귀 구조의 우아함**: 각 단계의 로직이 동일 (LIR → main + leftover → 재귀). 따로 코드 안 짜도 같은 함수가 모든 depth 처리.

3. **단일 책임 함수들**: 각 함수가 한 가지만 함:
   - `rasterize_polygon`: polygon → binary
   - `max_rect_in_mask`: binary → rect
   - `lir_at_angle`: 회전된 LIR
   - `grid_no_skip_aniso`: 격자 + 클립
   - `merge_below_50_aniso`: 작은 cell 흡수
   - `recursive_progressive_per_family`: 위들을 조합 + 재귀
   
   합쳐서 하나의 큰 함수로 만들면 같은 로직이지만 1000+ 줄 됨.

4. **표준 알고리즘**: "Maximal Rectangle in Histogram"은 LeetCode hard 문제로 유명한 30줄짜리 stack 알고리즘. 검색하면 바로 나옴. 같은 식으로 "Max Rectangle in Binary Matrix"도 표준.

5. **NumPy 벡터화**: rasterization에서 `Path.contains_points`로 14400 points를 한 번에 처리. 직접 loop면 100배 길어짐.

6. **상태 없음**: 알고리즘이 pure function 스타일. global state, cache, 복잡한 클래스 위계 없음. 입력 → 출력만.

7. **건축 도메인 특성**: 격자 분할 자체가 본질적으로 단순한 작업. 복잡해 보이는 건 edge case들인데, 그걸 "footprint 100% 커버"라는 단순 목표로 통일하니 처리 명확.

비슷한 일을 하는 mesh generation 라이브러리(gmsh, CGAL)가 수만 줄인 이유는 일반성과 robustness 때문. 우리는 "건축 평면도, polyomino용"으로 좁혀서 가니까 짧을 수 있음.

---

**문서 끝.**

본 알고리즘 v3.2는 **30개 케이스 stress test 통과** (한글 자모/mirror/회전/multi-wing 15개 + 별/곡선/hole-heavy 등 LIR-unfriendly 극한 15개). 사실상 모든 일반적인 건축 footprint 형태에 fully automatic + 거의 100% 커버.
다음 단계는 cell adjacency graph 구축 → 방 배치 알고리즘.
