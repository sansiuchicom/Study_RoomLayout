# Auto LIR + Recursive Progressive Fill 분할 알고리즘 (v3.1)

> 임의 형태 2D 건물 footprint(hole 가능)를 wall-aligned cell 격자로 분할.
> 본 문서는 다른 대화에서 self-contained하게 이어갈 수 있도록 작성됨.
>
> **v3.1 핵심 변화**: Recursive progressive fill — leftover가 충분히 크면
> 그 안에서도 LIR 다시 찾고 progressive 재귀 적용. Phase chain으로 nested
> structure에서도 시각적 연속성 유지.

---

## 0. 문제 설정

### 풀고자 하는 것
임의 형태의 건물 평면(footprint)을 입력받아, 평면 전체를 cell 격자로 덮되 cell 경계가 가능한 한 인접 벽에 평행/수직이 되도록 분할.

### 입출력
- **입력**: shapely Polygon (외곽 + 0개 이상 hole). 비-Manhattan, 회전된 wing, 곡선 boundary 모두 가능. **다른 어떤 사전 정보도 필요 없음** (mirror, component history 등 불필요).
- **출력**: 평면 전체(hole 제외)를 덮는 cell 다각형들 (~0.3~0.6m), piece별로 (i, j) 좌표 가능

### 제약
- Python 3.11+
- 시드 기반 random (같은 입력 → 같은 결과)
- offline OK

### 용도
이 cell 위에 polyomino식 방 배치가 다음 단계 (별개 주제).

---

## 1. 핵심 아이디어 (한 줄 요약)

> **Footprint에서 가장 큰 inscribed rectangle (LIR)을 찾아 main으로 정한 뒤, main 영역에 우선 격자를 깐다. 남은 영역(leftover)은 자체적으로 같은 알고리즘을 재귀 적용 — leftover 안에서도 sub-LIR 찾고 main+leftover로 분할. Main과 같은 theta인 leftover는 main의 phase를 공유하여 seamless하게 연장된다 (재귀 깊이 거쳐 phase chain).**

---

## 2. 왜 이게 잘 되는가 (이전 접근들과 비교)

### 발견 과정 요약 (이전 대화 시리즈 결과)

| 접근 | 특징 | 한계 |
|---|---|---|
| **Cut-cell Cartesian** | 단일 회전 격자 + 클립 | 다중 wing 방향 처리 불가 |
| **Frame field (gmsh)** | smooth quad mesh | (i, j) 좌표 없음 → polyomino 부적합 |
| **Reflex Bisector + Steiner (v2e)** | reflex 추론 cut + per-piece grid | hole 주변 over-segmentation, 곡선 영역 추론 노이즈 |
| **Per-component grid (v2g)** | construction info 명시적 사용 | mirror 처리 어색, 정보 의존성 |
| **Manual Progressive Fill (v2h)** | main 우선 + leftover (manual main) | main 명시 필요 |
| **Auto LIR Progressive (v3)** | LIR 자동 탐색 + progressive | nested 구조에서 leftover 어색 |
| **Recursive Progressive (v3.1)** ★ | LIR 재귀 + phase chain | 현재 best |

### v3.1의 핵심 통찰 6가지

**통찰 1: Main 사각형이 격자의 기준이다.**
건축에서 "main"은 가장 큰 사각형 영역. 이게 격자의 기준점(theta, phase)을 결정.

**통찰 2: Main 안의 hole은 분할 사유가 아니다.**
v2e는 hole 주변 4-way 분할했는데 불필요. main의 격자가 같은 방향이면 hole은 cell이 회피하는 obstacle일 뿐.

**통찰 3: Same-theta leftover는 phase 공유로 seamless 연장.**
Branch가 main과 같은 방향이면 phase 공유. 시각적으로 두 영역의 경계가 사라짐 (7자, L자 같은 axis-aligned 복합 도형).

**통찰 4: Different-theta leftover만 분리 처리.**
회전된 wing처럼 정말 다른 방향이 필요한 영역만 별도 격자.

**통찰 5: LIR은 자동 탐색 가능 → construction info 불필요.**
Footprint만 주어져도 LIR 알고리즘이 main 사각형을 자동 탐색. **mirror, component history 등 사전 정보가 critical path에서 빠질 수 있음**.
- Mirror 대칭 footprint? LIR이 정중앙으로 잡히고 양쪽 leftover이 자연스레 mirror 관계
- Component info? 알고리즘이 boundary geometry로 영역 인식

**통찰 6 (v3.1 신규): Nested 구조는 재귀로 자연스럽게 해소.**
큰 leftover 안에 또 의미 있는 LIR이 있으면 재귀 적용. Phase chain으로 부모-자식 같은 theta면 phase 상속 → 다단계 nested에서도 시각적 연속성.

---

## 3. 알고리즘 구조

```
def recursive_progressive_fill(polygon, depth=0, parent_phase=None, parent_theta=None):
    # === 1. LIR 탐색 ===
    main_rect, main_theta = find_main_rect_refined(polygon)
    
    # === 2. 종료 조건 체크 ===
    can_recurse = (depth < max_depth and 
                   polygon.area >= min_recurse_area and 
                   main_rect is not None)
    has_meaningful_lir = main_rect.area >= polygon.area * min_lir_ratio
    
    if not (can_recurse and has_meaningful_lir):
        # TERMINAL: 그냥 격자
        theta = main_theta if has_meaningful_lir else infer_from_boundary(polygon)
        # parent와 theta 같으면 phase 공유 (chain)
        if parent_theta and angle_diff(theta, parent_theta) < 2°:
            phase = parent_phase
            theta = parent_theta  # 정확히 일치
        cells = grid_with_phase(polygon, theta, phase)
        return cells
    
    # === 3. RECURSIVE: main + leftover ===
    # Main fill (parent와 같은 theta면 phase chain)
    main_phase = parent_phase if angle_match(main_theta, parent_theta) else new_phase()
    main_cells = grid_with_phase(main_rect ∩ polygon, main_theta, main_phase)
    
    # 각 leftover에 대해 재귀
    leftovers = (polygon - main_rect).split_into_pieces()
    leftover_cells = []
    for leftover in leftovers:
        if leftover.area >= 0.3:
            sub_cells = recursive_progressive_fill(
                leftover, 
                depth=depth+1,
                parent_phase=main_phase,    # phase chain
                parent_theta=main_theta,
            )
            leftover_cells.extend(sub_cells)
    
    return main_cells + leftover_cells
```

### LIR 탐색 (2-step refined)

```
1. Coarse: boundary edge 각도 (2° binned) 후보 4개 + 0°
   - 각 후보에서 polygon -theta 회전 → rasterize → max_rect_in_binary_matrix
2. Fine: 상위 2개 coarse 주변 ±2°를 0.5° step으로 정밀 탐색
3. 최대 면적 LIR 선택
```

### Maximal Rectangle in Binary Matrix (히스토그램+스택, O(MN))

각 row에 대해 "이 row를 바닥으로 위로 올라가는 1의 연속 높이" histogram 구축, 그 histogram에서 최대 직사각형 찾기 (stack-based O(N)).

### Phase Chain 동작 예시

```
H 케이스 (nested L, 모든 부분 0°):
depth=0: LIR θ=0°, phase=P₀ (own)
  depth=1: LIR θ=89.5° (mod 90° = 0°), |θ-parent|<2° → phase=P₀ (shared)
    depth=2: LIR θ=0°, |θ-parent|<2° → phase=P₀ (shared)
→ 모든 cell이 같은 격자 위에 → 시각적으로 한 큰 격자
```

---

## 4. Python 구현 (self-contained)

### 의존성
```bash
pip install shapely numpy matplotlib
# matplotlib for Path.contains_points (rasterization)
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
    """Polygon 내부를 binary matrix로. 빠른 처리를 위해 matplotlib.Path 사용."""
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
    """Polygon의 exterior 안의 최대 inscribed rect (각도 theta로 회전).
    Holes는 무시 (main rect가 hole 포함, 나중에 cell이 회피).
    """
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
def find_main_rect_refined(polygon, resolution=0.1,
                            coarse_bin_deg=2.0, top_k_coarse=4,
                            fine_step_deg=0.5, fine_range_deg=2.0,
                            n_refine_centers=2):
    """2-step LIR: coarse 후보 → top-K 주변 fine refinement.
    Returns: (rect, theta, info_dict) or (None, 0, {})
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
    
    # Fine: top-K coarse 주변
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
    return best['rect'], best['theta'], {
        'coarse_results': coarse_results,
        'fine_results': fine_results,
        'best': best,
    }


# ============================================================
# 5. Grid with explicit phase (for sharing across pieces/depths)
# ============================================================
def grid_with_phase(piece, theta, cell_size, phase_origin=None,
                     merge_threshold=0.15, seed=42):
    """phase_origin이 주어지면 그대로 사용 (phase 공유).
    None이면 seed 기반 random phase.
    Returns: (cells, phase_origin)
    """
    if phase_origin is None:
        rng = np.random.default_rng(seed)
        cx, cy = piece.centroid.x, piece.centroid.y
        ox, oy = rng.uniform(0, cell_size), rng.uniform(0, cell_size)
    else:
        cx, cy, ox, oy = phase_origin
    
    rotated = sa.rotate(piece, -np.degrees(theta), origin=(cx, cy))
    minx, miny, maxx, maxy = rotated.bounds
    minx_g = np.floor((minx - ox) / cell_size) * cell_size + ox - cell_size
    miny_g = np.floor((miny - oy) / cell_size) * cell_size + oy - cell_size
    maxx_g = np.ceil((maxx - ox) / cell_size) * cell_size + ox + cell_size
    maxy_g = np.ceil((maxy - oy) / cell_size) * cell_size + oy + cell_size
    nx = int(np.round((maxx_g - minx_g) / cell_size))
    ny = int(np.round((maxy_g - miny_g) / cell_size))
    
    cells = []
    threshold_area = cell_size * cell_size * merge_threshold
    for j in range(ny):
        for i in range(nx):
            x0 = minx_g + i * cell_size
            y0 = miny_g + j * cell_size
            cell = sg.box(x0, y0, x0 + cell_size, y0 + cell_size)
            inter = cell.intersection(rotated)
            if not inter.is_empty and inter.area >= threshold_area:
                cells.append(inter)
    cells_world = [sa.rotate(c, np.degrees(theta), origin=(cx, cy)) for c in cells]
    return cells_world, (cx, cy, ox, oy)


# ============================================================
# 6. Boundary 기반 theta 추론 (fallback)
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
# 7. Cell merging
# ============================================================
def merge_small_cells(cells, cell_size, min_ratio=0.3, max_iter=30):
    """작은 cell을 가장 큰 인접 cell에 병합."""
    threshold = cell_size * cell_size * min_ratio
    cells = list(cells)
    for _ in range(max_iter):
        smallest_idx, smallest_area = None, float('inf')
        for i, c in enumerate(cells):
            if c is None:
                continue
            if c.area < threshold and c.area < smallest_area:
                smallest_area = c.area
                smallest_idx = i
        if smallest_idx is None:
            break
        small = cells[smallest_idx]
        small_buf = small.buffer(0.01)
        neighbors = []
        for j, other in enumerate(cells):
            if j == smallest_idx or other is None:
                continue
            inter = small_buf.intersection(other.buffer(0.01))
            if not inter.is_empty and inter.area > 1e-6 and inter.length > 0.05:
                neighbors.append((j, other.area))
        if not neighbors:
            cells[smallest_idx] = None
            continue
        biggest_j, _ = max(neighbors, key=lambda x: x[1])
        merged = small.union(cells[biggest_j])
        if isinstance(merged, sg.Polygon):
            cells[biggest_j] = merged
        elif isinstance(merged, sg.MultiPolygon):
            cells[biggest_j] = max(merged.geoms, key=lambda g: g.area)
        cells[smallest_idx] = None
    return [c for c in cells if c is not None]


# ============================================================
# 8. Recursive Progressive Fill (메인 알고리즘)
# ============================================================
def recursive_progressive_fill(polygon, cell_size=0.5, seed=42,
                                max_depth=3,
                                min_lir_ratio=0.4,
                                min_recurse_area=8.0,
                                lir_resolution=0.1,
                                _depth=0,
                                _parent_phase=None,
                                _parent_theta=None):
    """
    재귀 progressive fill.
    
    각 단계에서 LIR 찾고 main+leftover 분할. Leftover 충분히 크면 재귀.
    Phase chain: parent와 같은 theta면 phase 공유.
    
    Args:
        polygon: shapely Polygon (with optional holes)
        cell_size: 셀 크기 (default 0.5m)
        seed: 시드
        max_depth: 최대 재귀 깊이 (default 3)
        min_lir_ratio: LIR이 polygon의 이 비율 미만이면 main+leftover 안 함 (0.4)
        min_recurse_area: 이보다 작은 polygon은 그냥 격자 (8m²)
        lir_resolution: LIR 탐색 해상도 (0.1m)
    
    Returns:
        all_cells: list of (Polygon, piece_id)
        pieces_info: list of dict (각 piece에 'depth' 필드 포함)
        root_main_rect: depth=0의 main rect (참고용)
    """
    rng = np.random.default_rng(seed)
    all_cells = []
    pieces_info = []
    
    # === LIR 탐색 ===
    main_rect, main_theta, _ = find_main_rect_refined(
        polygon, resolution=lir_resolution)
    
    # === 종료 조건 ===
    can_recurse = (_depth < max_depth and
                   polygon.area >= min_recurse_area and
                   main_rect is not None)
    has_meaningful_lir = (main_rect is not None and
                          main_rect.area >= polygon.area * min_lir_ratio)
    
    if not (can_recurse and has_meaningful_lir):
        # === TERMINAL ===
        if main_rect is not None and has_meaningful_lir:
            theta = main_theta
        else:
            theta = piece_direct_theta(polygon, 1.0)
            if theta is None:
                theta = _parent_theta if _parent_theta is not None else 0.0
        
        # Phase chain 적용
        phase_init = None
        if _parent_phase is not None and _parent_theta is not None:
            if angle_diff(theta, _parent_theta) < np.radians(2):
                phase_init = _parent_phase
                theta = _parent_theta  # 정확히 일치
        
        cells, _ = grid_with_phase(polygon, theta, cell_size,
                                    phase_origin=phase_init,
                                    seed=int(rng.integers(0, 2**31)))
        cells = merge_small_cells(cells, cell_size, 0.3)
        pieces_info.append({
            'polygon': polygon, 'theta': theta,
            'role': 'terminal',
            'name': f'd{_depth}_terminal',
            'depth': _depth,
            'n_cells': len(cells),
        })
        for c in cells:
            all_cells.append((c, 0))
        return all_cells, pieces_info, main_rect
    
    # === RECURSIVE ===
    # Main의 phase: parent와 theta 같으면 chain
    main_phase = None
    if _parent_phase is not None and _parent_theta is not None:
        if angle_diff(main_theta, _parent_theta) < np.radians(2):
            main_phase = _parent_phase
            main_theta = _parent_theta  # 정확히 일치
    
    # Main fill
    main_region = main_rect.intersection(polygon)
    if isinstance(main_region, sg.MultiPolygon):
        main_subpieces = list(main_region.geoms)
    elif isinstance(main_region, sg.Polygon):
        main_subpieces = [main_region]
    else:
        main_subpieces = []
    main_subpieces = [p for p in main_subpieces if p.area >= 0.3]
    
    for sub in main_subpieces:
        cells, phase = grid_with_phase(
            sub, main_theta, cell_size, phase_origin=main_phase,
            seed=int(rng.integers(0, 2**31)))
        cells = merge_small_cells(cells, cell_size, 0.3)
        if main_phase is None:
            main_phase = phase  # 이 레벨에서 결정된 phase
        piece_id = len(pieces_info)
        pieces_info.append({
            'polygon': sub, 'theta': main_theta,
            'role': 'main',
            'name': f'd{_depth}_main',
            'depth': _depth,
            'n_cells': len(cells),
        })
        for c in cells:
            all_cells.append((c, piece_id))
    
    # Leftover들 — 각각 재귀 호출
    remainder = polygon.difference(main_rect)
    if isinstance(remainder, sg.MultiPolygon):
        rem_pieces = list(remainder.geoms)
    elif isinstance(remainder, sg.Polygon):
        rem_pieces = [remainder]
    else:
        rem_pieces = []
    rem_pieces = [p for p in rem_pieces if p.area >= 0.3]
    
    for k, leftover in enumerate(rem_pieces):
        sub_cells, sub_pieces, _ = recursive_progressive_fill(
            leftover, cell_size,
            seed=int(rng.integers(0, 2**31)),
            max_depth=max_depth,
            min_lir_ratio=min_lir_ratio,
            min_recurse_area=min_recurse_area,
            lir_resolution=lir_resolution,
            _depth=_depth + 1,
            _parent_phase=main_phase,
            _parent_theta=main_theta,
        )
        offset = len(pieces_info)
        for cell, sub_pid in sub_cells:
            all_cells.append((cell, sub_pid + offset))
        pieces_info.extend(sub_pieces)
    
    return all_cells, pieces_info, main_rect


# ============================================================
# 9. 메인 엔트리
# ============================================================
def auto_partition(footprint, cell_size=0.5, seed=42,
                    max_depth=3, min_lir_ratio=0.4, min_recurse_area=8.0):
    """Footprint만 입력 → 재귀 progressive 자동 분할.
    
    Returns: dict with 'cells', 'pieces', 'root_main_rect'
    """
    cells, pieces, root_main = recursive_progressive_fill(
        footprint, cell_size=cell_size, seed=seed,
        max_depth=max_depth,
        min_lir_ratio=min_lir_ratio,
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

# 임의 footprint (외곽 + hole)
main = sg.box(0, 0, 12, 8)
wing = sa.translate(sa.rotate(sg.box(0, 0, 6, 4), 25, origin=(0, 0)),
                    xoff=10, yoff=6)
bump = sg.Point(0, 4).buffer(2.0, resolution=20)
core1 = sg.box(3, 2.5, 5.5, 4.5)
fp = unary_union([main, wing, bump]).difference(core1)

# 한 줄 호출 — 사전 정보 없이 자동 분할
result = auto_partition(fp, cell_size=0.5, seed=42)

print(f"#pieces: {len(result['pieces'])}")
for p in result['pieces']:
    print(f"  d{p['depth']} [{p['role']:8s}] {p['name']}: "
          f"theta={np.degrees(p['theta']):.1f}deg, "
          f"area={p['polygon'].area:.2f}m^2, cells={p['n_cells']}")
print(f"#cells total: {sum(p['n_cells'] for p in result['pieces'])}")
```

---

## 5. Prototype 결과 (v3.1)

### 9개 테스트 케이스

| Case | 설명 | Recursive (v3.1) | Non-recursive (v3) |
|---|---|---|---|
| A | 7-shape | 2 pieces, 286 cells | 2 pieces, 286 cells |
| B | rotated wing 25° | 3 pieces, 506 cells | 2 pieces, 496 cells |
| C | curved bump | 2 pieces, 433 cells | 2 pieces, 435 cells |
| D | full complex (2 holes) | 4 pieces, 506 cells | 3 pieces, 503 cells |
| E | two wings (different angles) | 5 pieces, 501 cells | 3 pieces, 503 cells |
| F | rotated main 15° | 3 pieces, 289 cells | 3 pieces, 289 cells |
| **G** | **nested wings (0° + 25° + 50°)** | **4 pieces, 527 cells** | **2 pieces, 517 cells** ★ |
| **H** | **nested L (all 0°)** | 3 pieces, 373 cells | 2 pieces, 373 cells |
| **I** | **two wings + nested sub** | **6 pieces, 446 cells** | **3 pieces, 449 cells** ★ |

### 재귀가 빛나는 케이스

**G: nested wings (main 0° + wing 25° + sub-wing 50°)** ★
- v3.1 (recursive): d0 main 0° → d1 wing main 25° → d2 sub-wing terminal 49.5°
- v3 (non-recursive): wing+sub-wing 한 leftover로 묶이고 averaged theta로 어색
- **sub-wing이 정확히 자기 50° 격자로 따로 처리됨**

**H: nested L (main + arm + sub-arm, all 0°)**
- v3.1: 3 pieces, 모두 0°이고 phase chain으로 공유 → 시각적으로 한 큰 격자
- 구조적으로 더 정확하지만 시각적 결과는 v3와 동일 (모두 같은 phase)

**I: two wings + nested sub on one (75° at depth 2)**
- v3.1: 6 pieces, 멀티레벨 — 각 wing 따로 + 한쪽 wing의 sub 또 따로
- sub의 75° 각도가 정확히 추론됨 (depth 2 terminal)

### 단순 케이스 (A, C, F)

재귀가 발동 안 함 (leftover가 너무 작거나 LIR ratio 부족) → v3와 동일 결과. 회귀 없음.

### Phase Chain 동작 확인 (verbose 로그 예시)

```
H 케이스:
depth=0, polygon area=84.00m^2
LIR: theta=0.0deg, area=48.00 (57%)
  depth=1, polygon area=36.00m^2
  LIR: theta=89.5deg, area=24.00 (67%)
    depth=2, polygon area=12.07m^2
    LIR: theta=0.0deg, area=12.00 (99%)  ← 거의 완벽한 직사각형!
```

89.5° vs 0°는 mod π/2 도메인에서 사실상 같은 방향 (|θ-parent|<2°). 알고리즘이 인식하고 phase 공유 → 모든 cell이 한 격자 위에 정렬.

### 성능
LIR refinement 100~150ms / depth × ~3 depths ≈ 500ms / 케이스. 충분히 빠름.

---

## 6. 알려진 한계 및 개선점

### 한계 1 (남음): LIR fallback이 의미 없는 경우
매우 비정형 footprint (별 모양, 십자 모양 등)에서 LIR이 작아서 main 역할 못함. 현재는 LIR ratio < 0.4면 그냥 격자 → boundary 추론. 곡선 영역에선 추론 노이즈.

**개선안**: v2e (reflex bisector) fallback 자동 적용.

### 한계 2 (대부분 해결됨): Cell adjacency graph 미구축
현재 cells = list of (Polygon, piece_id). 방 배치엔 (i, j) 좌표 + neighbors 정보 필요.

**개선안**: 각 cell에 (piece_id, depth, i, j, N/S/E/W neighbors) 부착하는 graph 자료구조 추가. **다음 작업의 1순위**.

### 한계 3: LIR 면적이 hole 무시해서 과대 추정
현재는 polygon.exterior만 rasterize → main_rect가 hole 포함. 일반적으론 OK인데 hole이 매우 크면 main_rect의 "유용한" 면적이 작아짐.

**개선안**: hole까지 고려한 LIR 옵션 (`include_holes=True`) — 면적 계산 시 hole 면적 차감.

### 한계 4: 매우 좁은 throat
극도로 좁은 영역 (cell_size에 가깝거나 작은)에선 cell이 거의 안 생김. min_recurse_area에 도달 못해서 이상하게 종료될 수 있음.

**개선안**: throat 감지 → 더 작은 cell_size로 그 영역만 재격자.

### 한계 5: max_depth 도달 시 마지막 leftover
max_depth에서도 큰 leftover가 남으면 그냥 격자. 이 격자는 LIR 정렬 안 돼서 cell이 어색할 수 있음.

**개선안**: max_depth 늘리거나, min_recurse_area 줄이기. 또는 max_depth 도달 시 v2e 적용.

### 한계 6 (philosophical): Same-theta 영역 분리 의도
같은 theta인데 일부러 별개 공간으로 분리하고 싶다 (room A vs room B 인접). 알고리즘은 자동으로 한 piece로 묶어버림.

**개선안**: 이건 cell 분할 단계가 아니라 **room placement 단계의 hint**로 처리. cell 알고리즘은 architectural region 단위로만 분할하고, semantic 분리는 위에서.

---

## 7. 파이프라인 도구상자 요약

| Pipeline | 입력 | 강점 | 적합 use case |
|---|---|---|---|
| **2j (recursive progressive)** ★ v3.1 default | footprint만 | **가장 깔끔, fully automatic, nested 처리** | 일반 건축 footprint |
| 2i (single-level progressive) | footprint만 | 가벼움, 단순 케이스 | nested 구조 없을 때 |
| 2h (manual main + progressive) | footprint + main_rect | 사용자 명시 main | LIR 자동 탐색 부적합 |
| 2g (hierarchical) | footprint + 모든 component | 명시적 component 분할 | parametric generator |
| 2e (reflex+Steiner) | footprint만 | 비정형 fallback | LIR 의미 없는 footprint |

**일반 사용**: `auto_partition(footprint)` 한 줄로 끝.

---

## 8. 다른 채팅에서 이어가기 위한 컨텍스트

### 이전 대화 시리즈 결정 사항
- **사용 사례**: 건축 평면도 분할 → cell 위에 polyomino 방 배치
- **셀 크기**: 0.3~0.6m (0.5m 기본)
- **알고리즘 선택**: 여러 후보 비교 끝에 **recursive progressive fill (LIR-based)**이 가장 깔끔
- **Hole 처리**: main이 hole을 자동 회피 (intersection 기반), 별도 분할 불필요
- **사전 정보**: mirror, component history 등 critical path에서 빠짐 (auto LIR로 충분)
- **재귀**: nested 구조에서 phase chain으로 시각적 연속성 유지

### 검토했지만 채택 안 한 접근들
- **Cut-cell single rotation**: 다중 wing 방향 처리 불가
- **Frame field (gmsh)**: smooth하지만 (i, j) 좌표 없음
- **Reflex Bisector + Steiner (v2e)**: hole 주변 over-segment, 곡선 추론 노이즈
- **Per-component grid (v2g)**: construction info 필요, mirror 처리 어색
- **Squarified treemap**: rectilinear 외곽만 가능
- **Voronoi/CVT**: cell이 사각형 아니어서 polyomino 부적합

### 다음 작업 우선순위

**1순위: Cell adjacency graph 자료구조** ★
- 각 cell에 (piece_id, depth, i, j, neighbors[N/S/E/W]) 정보 부착
- 방 배치 시 polyomino 성장의 핵심 데이터구조
- 구현 후 시각화로 검증 (격자 좌표, neighbor edge highlight)

**2순위: 방 배치 알고리즘 시작** (별개 큰 주제)
- 옵션 1: Growth-based (seed cell에서 cell 단위로 영역 확장)
- 옵션 2: MIP (mixed integer programming, 최적화)
- 옵션 3: WFC (wave function collapse, 제약 전파)
- 각각 장단점 비교 후 선택

**3순위: 한계 처리 (필요시)**
- 매우 비정형 footprint에 v2e 자동 fallback (한계 1)
- LIR에서 hole 고려 옵션 (한계 3)

### 코드 파일 구조 (이전 대화 기준)
- `00_footprint.py`: 샘플 footprint 생성기
- `02e_improved.py`: Reflex+Steiner (v2e) — 비정형 fallback
- `02h_progressive.py`: Manual main + progressive
- `02i_lir_progressive.py`: Auto LIR + single-level progressive (v3)
- **`02j_recursive.py`** ★ 핵심: Recursive progressive (이 문서 기준, v3.1)

`02j_recursive.py`가 현재 추천 메인 구현. § 4의 코드가 이 파일을 정리한 self-contained 버전.

---

## 9. 새 채팅 시작 시 prompt 예시

> "이전 대화에서 'Auto LIR + Recursive Progressive Fill' 분할 알고리즘 (v3.1)을 만들었어. 첨부한 markdown 문서에 알고리즘 설명, Python 구현, 알려진 한계가 정리되어 있어. 이번엔 [원하는 작업: cell adjacency graph 구축 / 방 배치 알고리즘 시작 / 한계 X 처리 / ...] 를 해보고 싶어. 첨부 문서 먼저 읽고 [현재 prototype 실행해서 baseline 확인 / 개선안 토론 / 바로 구현 시작]."

---

## 10. v3 → v3.1 변경 요약

### 추가된 개념
- **재귀 progressive**: leftover가 충분히 크면 그 안에서도 LIR 다시 찾고 main+leftover 적용
- **Phase chain**: 부모-자식 관계에서 같은 theta면 phase 공유 (depth N까지 chain 가능)
- **Mirror/component info의 불필요성 확인**: auto LIR이 대부분의 사전 정보를 대체

### 추가된 함수
- `recursive_progressive_fill()`: 메인 재귀 알고리즘. `_depth`, `_parent_phase`, `_parent_theta` 인자.
- `auto_partition()`: footprint만 받는 깔끔한 entry point.

### 추가된 종료 조건
- `max_depth` (default 3): 깊이 한계
- `min_lir_ratio` (default 0.4): LIR이 polygon의 40% 미만이면 main+leftover 안 함
- `min_recurse_area` (default 8m²): 작은 leftover는 그냥 격자

### 새 테스트 케이스 (재귀의 진가 보임)
- **G**: nested wings (3 단계 회전: 0° → 25° → 50°)
- **H**: nested L (모두 0°이지만 다단계, phase chain 검증)
- **I**: 두 wing + 한쪽에 sub-wing (multi-branch nesting)

### 기존 v3 결과와의 비교
- 단순 케이스 (A, C, F): 동일 결과 (재귀 발동 안 함)
- Mid 케이스 (B, D, E): 1~2 piece 추가, 약간 더 정확한 transition cells
- **Nested 케이스 (G, I)**: 명확한 개선 — 제대로 된 multi-level grid

---

**문서 끝.**

본 알고리즘 v3.1은 단순 footprint부터 nested 복잡 footprint까지 robust하게 동작.
사전 정보 없이 footprint polygon 한 개로 fully automatic 분할.
다음 단계는 cell adjacency graph 구축 (방 배치 준비).
