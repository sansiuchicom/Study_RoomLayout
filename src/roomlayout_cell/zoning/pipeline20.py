"""
Pipeline 20 — Fine-grained Zoning (zone = sub-room building block).

Pipeline 12와의 차이 (컨셉):
- Pipeline 12: zone = 방. 각 zone이 직접 하나의 방.
- Pipeline 20: zone = sub-room unit. 1개 또는 여러 zone을 합쳐서 방 구성.
  + 추후 atom cell로 연결 안 된 zone 묶음 사이에 복도 생성 예정.

알고리즘 차이:
- min_zone_area: 8 → 3 m² (더 잘게 분할 허용)
- balance_threshold: 0.4 → 0.15 (1:7까지 비대칭 split 허용 → 작은 zone carve off)
- balance_threshold를 zone_footprint까지 외부 parameter로 노출.
- Tier 1을 sub-tier로 분할 (cross cut 도입):
    T1a (NEW): cross_cut — vertex (x,y)에서 V+H line 동시 적용 (3-4 piece)
    T1b:       vertex_aligned — single V or H line (2 piece)
    T2:        oblique reflex_pair
    T3:        axis_mid fallback
  reflex vertex에서 cross cut이 자연스럽게 3-4 zone을 한 번에 생성.
"""
import numpy as np
import shapely.geometry as sg
import shapely.affinity as sa
from shapely.ops import unary_union, split
from typing import List, Optional, Tuple
from collections import defaultdict

from roomlayout_cell.atom import per_family as p2M


# ============================================================
# Parameters (external, not magic)
# ============================================================
DEFAULT_MIN_ZONE_AREA = 3.0       # m²: sub-room unit 최소 (pipeline12: 8.0)
DEFAULT_BOUNDARY_MARGIN = 0.5     # m: vertex가 boundary 가까울 때 cut 제외
DEFAULT_MIN_CUT_LENGTH = 1.0      # m: reflex pair line 최소 polygon 내부 길이
DEFAULT_MAX_PIECE_ASPECT = 4.0    # 건축적 constraint: 방의 max aspect ratio
DEFAULT_BALANCE_THRESHOLD = 0.15  # 1:7까지 비대칭 split 허용 (pipeline12: 0.4)
BALANCE_TIE_DECIMALS = 6          # sort tie-break: balance 6자리에서 동률 처리.
                                  # 회전 polygon의 float drift (~1e-16)가 micro-balance 차이를
                                  # 만들어 tie-break를 뒤집는 bug 방지.


# ============================================================
# 1. Reflex vertex 찾기
# ============================================================
def find_reflex_vertices(polygon):
    """exterior + holes의 reflex vertex.
    
    Returns: list of (x, y)
    """
    if not polygon.exterior.is_ccw:
        polygon = sg.Polygon(list(polygon.exterior.coords)[::-1],
                              [list(h.coords)[::-1] for h in polygon.interiors])
    
    reflex = []
    
    def process_ring(coords, is_hole):
        n = len(coords)
        for i in range(n):
            p_prev = np.array(coords[(i - 1) % n])
            p_curr = np.array(coords[i])
            p_next = np.array(coords[(i + 1) % n])
            v1 = p_curr - p_prev
            v2 = p_next - p_curr
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            if cross < -1e-6:
                reflex.append(tuple(p_curr))
    
    process_ring(list(polygon.exterior.coords)[:-1], False)

    for hole in polygon.interiors:
        h_coords = list(hole.coords)[:-1]
        if hole.is_ccw:
            h_coords = h_coords[::-1]
        process_ring(h_coords, True)

    return reflex


def extract_structural_coords(polygon, simplify_tol=0.15):
    """Reflex vertex의 x, y 좌표 set — sub-recursion에 alignment hint로 전파.

    Cross cut이나 single cut으로 polygon이 sub-pieces로 나뉘면, 원본 polygon의
    다른 reflex 좌표들이 sub-piece의 boundary에서 사라져 후속 cut 후보에서 빠짐
    (e.g., ㄷ자에서 cross at (4, 6.2) 후 y=3.8 vertex 정보 유실).
    이 set을 recursion에 전달해서 vertex_aligned_lines가 sub-piece bbox 내부의
    structural 좌표를 추가 후보로 emit하도록 함.
    """
    if simplify_tol > 0:
        simp = polygon.simplify(simplify_tol, preserve_topology=True)
        target = (simp if (isinstance(simp, sg.Polygon) and not simp.is_empty)
                  else polygon)
    else:
        target = polygon
    reflex = find_reflex_vertices(target)
    xs = set(round(x, 6) for x, _ in reflex)
    ys = set(round(y, 6) for _, y in reflex)
    return {'xs': xs, 'ys': ys}


# ============================================================
# 2. Cut candidate generators
# ============================================================
def vertex_aligned_lines(polygon, margin=DEFAULT_BOUNDARY_MARGIN,
                          simplify_tol=0.15, structural_coords=None):
    """Type 1: vertex 좌표 통과 axis-aligned line.

    각 vertex의 x 좌표 → vertical line, y 좌표 → horizontal line.
    Boundary와 너무 가까운 좌표는 제외 (margin).

    simplify_tol: cut 후보 생성 시 polygon 단순화.
    - saw-tooth (sub-grid noise) 제거
    - 곡면 vertex 폭증 방지
    - 실제 polygon은 변경 X (cut 후보의 좌표만 단순화된 vertex 사용)

    structural_coords: optional {'xs': set, 'ys': set}. parent polygon의 reflex 좌표.
    sub-piece의 bbox 내부에 들어오는 structural 좌표를 추가 cut 후보로 emit해
    형제 piece와의 alignment를 보존 (cross cut 후 잊혀진 reflex 정보 회복용).
    """
    # Cut 후보용 단순화 (실제 split은 원본 polygon에)
    if simplify_tol > 0:
        simp = polygon.simplify(simplify_tol, preserve_topology=True)
        if isinstance(simp, sg.Polygon) and not simp.is_empty:
            poly_for_vertices = simp
        else:
            poly_for_vertices = polygon
    else:
        poly_for_vertices = polygon

    minx, miny, maxx, maxy = polygon.bounds  # bbox는 원본 기준

    all_coords = list(poly_for_vertices.exterior.coords)[:-1]
    for hole in poly_for_vertices.interiors:
        all_coords.extend(list(hole.coords)[:-1])

    # Structural coords from parent polygon (alignment hint).
    # x 좌표는 (x, miny)로 추가 → V line 후보로만 작용 (y=miny는 boundary라
    # margin filter에 걸려 H line은 안 생김). y 좌표도 동일 원리.
    if structural_coords:
        for x in structural_coords.get('xs', ()):
            all_coords.append((x, miny))
        for y in structural_coords.get('ys', ()):
            all_coords.append((minx, y))

    cuts = []
    seen_x, seen_y = set(), set()
    for x, y in all_coords:
        x_key = round(x, 2)
        y_key = round(y, 2)
        if (minx + margin < x < maxx - margin) and x_key not in seen_x:
            seen_x.add(x_key)
            cuts.append(sg.LineString([(x, miny - 1), (x, maxy + 1)]))
        if (miny + margin < y < maxy - margin) and y_key not in seen_y:
            seen_y.add(y_key)
            cuts.append(sg.LineString([(minx - 1, y), (maxx + 1, y)]))

    return cuts


def cross_cut_pairs(polygon, margin=DEFAULT_BOUNDARY_MARGIN,
                     simplify_tol=0.15):
    """Type 1a: vertex의 V+H 동시 cut candidate (cross cut).

    각 vertex (x, y)에서 (vertical at x, horizontal at y) 쌍을 emit.
    margin 안에 x, y *둘 다* 들어와야 emit — boundary 근접 좌표는 제외하고,
    single cut과 동치인 경우(한쪽 좌표만 valid)도 자동 제외 (T1b가 처리).

    Reflex vertex에서 자연스럽게 3 piece(또는 4 piece) 분할을 만듦.
    Convex outer corner는 보통 좌표가 boundary라 margin filter로 제외됨.
    """
    if simplify_tol > 0:
        simp = polygon.simplify(simplify_tol, preserve_topology=True)
        if isinstance(simp, sg.Polygon) and not simp.is_empty:
            poly_for_vertices = simp
        else:
            poly_for_vertices = polygon
    else:
        poly_for_vertices = polygon

    minx, miny, maxx, maxy = polygon.bounds

    all_coords = list(poly_for_vertices.exterior.coords)[:-1]
    for hole in poly_for_vertices.interiors:
        all_coords.extend(list(hole.coords)[:-1])

    pairs = []
    seen = set()
    for x, y in all_coords:
        key = (round(x, 2), round(y, 2))
        if key in seen:
            continue
        seen.add(key)
        if not (minx + margin < x < maxx - margin):
            continue
        if not (miny + margin < y < maxy - margin):
            continue
        v_line = sg.LineString([(x, miny - 1), (x, maxy + 1)])
        h_line = sg.LineString([(minx - 1, y), (maxx + 1, y)])
        pairs.append((v_line, h_line))
    return pairs


def reflex_pair_lines(polygon, min_length=DEFAULT_MIN_CUT_LENGTH):
    """Type 2: 두 reflex vertex 잇는 line.
    
    Polygon 내부에서 min_length 이상 통과해야 valid.
    """
    reflex = find_reflex_vertices(polygon)
    cuts = []
    for i in range(len(reflex)):
        for j in range(i + 1, len(reflex)):
            p1, p2 = reflex[i], reflex[j]
            line = sg.LineString([p1, p2])
            inter = line.intersection(polygon)
            if hasattr(inter, 'length') and inter.length >= min_length:
                cuts.append(line)
    return cuts


def axis_mid_lines(polygon, n=9):
    """Type 0 (fallback): bbox 중간 fraction line."""
    minx, miny, maxx, maxy = polygon.bounds
    cuts = []
    for frac in np.linspace(0.3, 0.7, n):
        x = minx + frac * (maxx - minx)
        cuts.append(sg.LineString([(x, miny - 1), (x, maxy + 1)]))
        y = miny + frac * (maxy - miny)
        cuts.append(sg.LineString([(minx - 1, y), (maxx + 1, y)]))
    return cuts


# ============================================================
# 3. Split & balance
# ============================================================
def split_polygon(polygon, line):
    """Line으로 polygon split. 모든 piece 반환 (큰 순)."""
    try:
        result = split(polygon, line)
    except Exception:
        return None
    pieces = list(result.geoms) if hasattr(result, 'geoms') else [result]
    pieces = [p for p in pieces if isinstance(p, sg.Polygon) and p.area > 0.01]
    if len(pieces) < 2:
        return None
    pieces.sort(key=lambda p: -p.area)
    return pieces


def split_polygon_multi(polygon, lines):
    """여러 line으로 polygon 순차 split. ≥ 2 piece 반환 (큰 순) or None.

    cross cut 같은 multi-line cut을 위함. 각 line을 차례로 적용해서 누적.
    """
    pieces = [polygon]
    for line in lines:
        next_pieces = []
        for p in pieces:
            try:
                result = split(p, line)
                parts = (list(result.geoms) if hasattr(result, 'geoms')
                          else [result])
                for q in parts:
                    if isinstance(q, sg.Polygon) and q.area > 0.01:
                        next_pieces.append(q)
            except Exception:
                next_pieces.append(p)
        if not next_pieces:
            return None
        pieces = next_pieces
    if len(pieces) < 2:
        return None
    pieces.sort(key=lambda p: -p.area)
    return pieces


def balance(pieces):
    """min/max area ratio. 50:50 = 1.0."""
    areas = [p.area for p in pieces]
    return min(areas) / max(areas)


def piece_aspect(piece):
    """MRR-based aspect ratio. axis-aligned이면 BBOX와 같음."""
    if piece.is_empty or piece.area < 1e-6:
        return 99
    try:
        mbr = piece.minimum_rotated_rectangle
        coords = list(mbr.exterior.coords)
        e1 = np.hypot(coords[1][0] - coords[0][0], coords[1][1] - coords[0][1])
        e2 = np.hypot(coords[2][0] - coords[1][0], coords[2][1] - coords[1][1])
        if min(e1, e2) < 1e-6:
            return 99
        return max(e1, e2) / min(e1, e2)
    except Exception:
        return 99


def is_axis_aligned(line):
    """Line이 axis-aligned (horizontal or vertical)인지."""
    coords = list(line.coords)
    if len(coords) < 2:
        return False
    p1, p2 = coords[0], coords[-1]
    return abs(p1[0] - p2[0]) < 1e-3 or abs(p1[1] - p2[1]) < 1e-3


def best_cross_cut_above_threshold(pairs, polygon, min_zone_area,
                                     max_aspect=DEFAULT_MAX_PIECE_ASPECT,
                                     balance_threshold=0.0):
    """Cross cut candidate(pair list) 중 best.

    각 pair = (v_line, h_line). 두 line으로 polygon split → 보통 3 또는 4 piece.

    Validity: 모든 piece area ≥ min_zone_area, aspect ≤ max_aspect,
              balance = min/max ≥ balance_threshold.
    Tie-break: balance ↓, max_piece_aspect ↑ (best_cut과 동일).

    Returns: ((v_line, h_line), pieces, balance) or None
    """
    valid = []
    for v_line, h_line in pairs:
        pieces = split_polygon_multi(polygon, [v_line, h_line])
        if pieces is None:
            continue
        if min(p.area for p in pieces) < min_zone_area:
            continue
        if any(piece_aspect(p) > max_aspect for p in pieces):
            continue
        b = balance(pieces)
        if b < balance_threshold:
            continue
        valid.append(((v_line, h_line), pieces, b))

    if not valid:
        return None

    valid.sort(key=lambda x: (-round(x[2], BALANCE_TIE_DECIMALS),
                               max(piece_aspect(p) for p in x[1])))
    return valid[0]


def best_cut_above_threshold(candidates, polygon, min_zone_area,
                                max_aspect=DEFAULT_MAX_PIECE_ASPECT,
                                balance_threshold=0.0,
                                prefer_shorter=False):
    """Validity 통과 + balance ≥ threshold 중 best.
    
    Validity:
    - 모든 piece area ≥ min_zone_area
    - 모든 piece aspect ≤ max_aspect
    
    Selection: balance desc; prefer_shorter면 line 길이 짧은 순 tie-break.
    
    Returns: (line, pieces, balance) or None
    """
    valid = []
    for line in candidates:
        pieces = split_polygon(polygon, line)
        if pieces is None:
            continue
        if min(p.area for p in pieces) < min_zone_area:
            continue
        if any(piece_aspect(p) > max_aspect for p in pieces):
            continue
        b = balance(pieces)
        if b < balance_threshold:
            continue
        valid.append((line, pieces, b))
    
    if not valid:
        return None
    
    if prefer_shorter:
        # tie-break: 짧은 line 우선 (balance는 epsilon-동률 처리)
        valid.sort(key=lambda x: (-round(x[2], BALANCE_TIE_DECIMALS),
                                    x[0].length))
    else:
        # tie-break: 더 정사각형 piece 우선 (max aspect 작은 것)
        valid.sort(key=lambda x: (-round(x[2], BALANCE_TIE_DECIMALS),
                                    max(piece_aspect(p) for p in x[1])))
    
    return valid[0]


# ============================================================
# 4. Hierarchical selection (Type 2 > 1 > 0)
# ============================================================
def select_cut(polygon, min_zone_area, margin, min_cut_length,
                max_aspect=DEFAULT_MAX_PIECE_ASPECT,
                balance_threshold=DEFAULT_BALANCE_THRESHOLD,
                structural_coords=None):
    """Hierarchical selection (T1은 sub-tier로 분할):

    Tier 1a: cross_cut — vertex의 V+H 동시 (3-4 piece)
        balance ≥ threshold 중 best
    Tier 1b: vertex_aligned — single axis-aligned (2 piece)
        balance ≥ threshold 중 best, structural_coords로 parent 정보 회복
    Tier 2:  oblique reflex_pair (사선)
        balance ≥ threshold 중 best, 짧은 순 tie-break
    Tier 3:  axis_mid (fallback)
        threshold 무관 (마지막 안전망), balance best

    structural_coords: parent polygon의 reflex 좌표 (T1b의 추가 후보로 흘림).
    """
    # Tier 1a: cross cut (vertex V+H 동시) — vertex 정보 가장 적극 활용
    pairs = cross_cut_pairs(polygon, margin)
    result = best_cross_cut_above_threshold(pairs, polygon, min_zone_area,
                                              max_aspect, balance_threshold)
    if result is not None:
        return ('cross_cut', *result)

    # Tier 1b: vertex_aligned (axis-aligned single line) + structural coords
    cuts = vertex_aligned_lines(polygon, margin,
                                  structural_coords=structural_coords)
    result = best_cut_above_threshold(cuts, polygon, min_zone_area,
                                          max_aspect, balance_threshold,
                                          prefer_shorter=False)
    if result is not None:
        return ('vertex_aligned', *result)
    
    # Tier 2: reflex_pair, 사선만 (axis-aligned reflex_pair는 Tier 1에 포함됨)
    all_pairs = reflex_pair_lines(polygon, min_cut_length)
    oblique = [c for c in all_pairs if not is_axis_aligned(c)]
    result = best_cut_above_threshold(oblique, polygon, min_zone_area,
                                          max_aspect, balance_threshold,
                                          prefer_shorter=True)
    if result is not None:
        return ('reflex_pair', *result)
    
    # Tier 3: axis_mid fallback (no balance threshold)
    cuts = axis_mid_lines(polygon)
    result = best_cut_above_threshold(cuts, polygon, min_zone_area,
                                          max_aspect, balance_threshold=0.0,
                                          prefer_shorter=False)
    if result is not None:
        return ('axis_mid', *result)
    
    return None


# ============================================================
# 5. Recursive partition (within single-axis frame)
# ============================================================
def recursive_partition(polygon, k, theta=0.0,
                          min_zone_area=DEFAULT_MIN_ZONE_AREA,
                          margin=DEFAULT_BOUNDARY_MARGIN,
                          min_cut_length=DEFAULT_MIN_CUT_LENGTH,
                          balance_threshold=DEFAULT_BALANCE_THRESHOLD):
    """k zones로 분할. Frame transform by -theta, partition, rotate back.

    sub-recursion에서는 theta=0 (이미 axis-aligned frame).
    family polygon의 reflex 좌표를 structural_coords로 추출해 sub-recursion에 전파.
    """
    if k <= 1 or polygon.area < min_zone_area * 2:
        return [{'polygon': polygon, 'cut_history': []}]

    # Frame transform (rotate to axis-aligned)
    cx, cy = polygon.centroid.x, polygon.centroid.y
    if abs(theta) > 1e-3:
        P = sa.rotate(polygon, -np.degrees(theta), origin=(cx, cy))
    else:
        P = polygon

    # Family-local frame의 structural coord (reflex 좌표 set)
    structural = extract_structural_coords(P)

    # Recurse in rotated frame
    zones_rot = _partition_in_frame(P, k, min_zone_area, margin,
                                     min_cut_length, balance_threshold,
                                     structural_coords=structural)

    # Rotate back
    if abs(theta) > 1e-3:
        for z in zones_rot:
            z['polygon'] = sa.rotate(z['polygon'], np.degrees(theta),
                                       origin=(cx, cy))

    return zones_rot


def _partition_in_frame(P, k, min_zone_area, margin, min_cut_length,
                         balance_threshold, structural_coords=None):
    """Axis-aligned frame에서만 작동. theta 회전은 호출자가 처리.

    structural_coords는 family polygon에서 한 번 추출되어 모든 sub-recursion에
    동일하게 전파 (sub-piece bbox 안에 들어오면 vertex_aligned_lines가 자동 사용).
    """
    if k <= 1 or P.area < min_zone_area * 2:
        return [{'polygon': P, 'cut_history': []}]

    selection = select_cut(P, min_zone_area, margin, min_cut_length,
                            balance_threshold=balance_threshold,
                            structural_coords=structural_coords)
    if selection is None:
        return [{'polygon': P, 'cut_history': []}]

    cut_type, line, pieces, b = selection

    # Allocate k by area
    total = sum(p.area for p in pieces)
    k_alloc = []
    acc = 0
    for i, p in enumerate(pieces):
        if i == len(pieces) - 1:
            kk = max(1, k - acc)
        else:
            kk = max(1, round(k * p.area / total))
            acc += kk
        k_alloc.append(kk)

    zones = []
    for p, kk in zip(pieces, k_alloc):
        sub = _partition_in_frame(p, kk, min_zone_area, margin,
                                    min_cut_length, balance_threshold,
                                    structural_coords=structural_coords)
        for z in sub:
            z['cut_history'].insert(0, cut_type)
        zones.extend(sub)
    return zones


# ============================================================
# 6. Family decomposition (for multi-axis)
# ============================================================
def get_families(footprint, target_cell_size=0.3):
    """02M에서 family 추출. 같은 fid라도 disjoint이면 별도 entry."""
    all_cells, pieces_info, _, _ = p2M.recursive_progressive_per_family(
        footprint, target_cell_size=target_cell_size, seed=42)
    
    family_data = defaultdict(lambda: {'polygons': [], 'theta': 0})
    for piece in pieces_info:
        fid = piece['family_id']
        family_data[fid]['polygons'].append(piece['polygon'])
        family_data[fid]['theta'] = piece['theta']
    
    families = []
    next_id = 0
    for fid, d in family_data.items():
        poly = unary_union(d['polygons'])
        parts = list(poly.geoms) if isinstance(poly, sg.MultiPolygon) else [poly]
        for part in parts:
            if part.area < 0.01:
                continue
            families.append({
                'id': next_id,
                'polygon': part,
                'theta': d['theta'],
                'area': part.area,
            })
            next_id += 1
    
    families.sort(key=lambda x: -x['area'])
    return families


def filter_big_families(families, threshold):
    """Big family만 추출. Small family는 drop.
    
    Small family 영역은 partition 후 final coverage check에서 
    nearest zone에 자동 합쳐짐. 이게 main polygon 깔끔하게 유지.
    """
    big = [f for f in families if f['area'] >= threshold]
    if not big:
        if families:
            big = [families[0]]  # 최소한 하나는 보장
    return sorted(big, key=lambda x: -x['area'])


# ============================================================
# 7. Main interface
# ============================================================
def auto_target_zones(footprint, area_per_zone=25.0):
    """Footprint area에 비례. 외부 parameter.
    
    25m²는 한국 평균 방 크기 + 거실 일부 비례.
    """
    return max(2, min(10, round(footprint.area / area_per_zone)))


def zone_footprint(footprint, k=None,
                    min_zone_area=DEFAULT_MIN_ZONE_AREA,
                    margin=DEFAULT_BOUNDARY_MARGIN,
                    min_cut_length=DEFAULT_MIN_CUT_LENGTH,
                    balance_threshold=DEFAULT_BALANCE_THRESHOLD):
    """Footprint를 k zones로 분할. Multi-axis aware.

    Algorithm:
        1. Family decomposition (02M)
        2. Absorb small families
        3. Allocate k by area to each family
        4. Recursive partition each family with hierarchical cut selection

    Returns: (zones, families)
    """
    if k is None:
        k = auto_target_zones(footprint)
    
    families = get_families(footprint)
    threshold = max(min_zone_area * 0.6, footprint.area * 0.04)
    big = filter_big_families(families, threshold)
    
    if not big:
        big = [{'polygon': footprint, 'theta': 0.0,
                'area': footprint.area, 'id': 0}]
    
    # Allocate
    total = sum(f['area'] for f in big)
    k_alloc = []
    acc = 0
    for i, f in enumerate(big):
        if i == len(big) - 1:
            kk = max(1, k - acc)
        else:
            kk = max(1, round(k * f['area'] / total))
            acc += kk
        k_alloc.append(kk)
    
    # Partition each family
    all_zones = []
    zid = 0
    for f, kk in zip(big, k_alloc):
        sub = recursive_partition(f['polygon'], kk, f['theta'],
                                    min_zone_area=min_zone_area,
                                    margin=margin,
                                    min_cut_length=min_cut_length,
                                    balance_threshold=balance_threshold)
        for s in sub:
            all_zones.append({
                'polygon': s['polygon'],
                'zone_id': zid,
                'family_id': f['id'],
                'family_theta': f['theta'],
                'cut_history': s.get('cut_history', []),
            })
            zid += 1
    
    # Final coverage check: zones union이 footprint와 같도록
    # (small family 흡수 누락이나 simplify 변형으로 인한 gap 처리)
    union_zones = unary_union([z['polygon'] for z in all_zones])
    gap = footprint.difference(union_zones)
    if gap.area > 0.01:
        gap_parts = (list(gap.geoms) if isinstance(gap, sg.MultiPolygon)
                      else [gap])
        for part in gap_parts:
            if part.area < 0.01:
                continue
            # 가장 boundary 공유하는 zone에 합침
            best_z = max(all_zones,
                         key=lambda z: z['polygon'].buffer(0.3)
                                       .intersection(part.boundary).length
                              if part.boundary.length > 0 else 0)
            best_z['polygon'] = unary_union([best_z['polygon'], part])
    
    # Zone polygon이 footprint 밖으로 나간 부분도 정리 (overlap 방지)
    for z in all_zones:
        z['polygon'] = z['polygon'].intersection(footprint)
        if isinstance(z['polygon'], sg.MultiPolygon):
            parts = sorted(z['polygon'].geoms, key=lambda p: -p.area)
            z['polygon'] = parts[0]
    
    return all_zones, big
