"""
Pipeline 12 — Clean Deterministic Zoning (논문용).

설계 원칙:
1. Vertex first-class: cut 후보 = vertex와의 관계로 정의
2. 점수 함수 X: 결정론적 우선순위 + balance criterion만
3. Magic number 최소화: 모든 threshold는 외부 parameter

Cut 후보 (2 종류 + fallback):
- Type 2 (reflex-pair):  두 reflex vertex 잇는 line     ← 우선
- Type 1 (vertex-aligned): vertex 좌표 통과 axis-aligned line
- Type 0 (axis-mid):     bbox 중간 fraction line       ← fallback

Selection: hierarchical (Type 2 → 1 → 0), 각 layer에서 balance best 채택.
Balance = min(piece_area) / max(piece_area), 50:50 = 1.0.

Rotation:
- Single-axis: dominant theta로 frame transform (cell decomposition family theta)
- Multi-axis: family별로 separate, 각자 single-axis 처리
"""
import sys
import numpy as np
import shapely.geometry as sg
import shapely.affinity as sa
from shapely.ops import unary_union, split
from typing import List, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, '/home/claude/work')
from importlib import import_module
p2M = import_module('02M_per_family')


# ============================================================
# Parameters (external, not magic)
# ============================================================
DEFAULT_MIN_ZONE_AREA = 8.0       # m²: 건축 최소 (조정 가능)
DEFAULT_BOUNDARY_MARGIN = 0.5     # m: vertex가 boundary 가까울 때 cut 제외
DEFAULT_MIN_CUT_LENGTH = 1.0      # m: reflex pair line 최소 polygon 내부 길이
DEFAULT_MAX_PIECE_ASPECT = 4.0    # 건축적 constraint: 방의 max aspect ratio
DEFAULT_BALANCE_THRESHOLD = 0.4   # "한 zone ≥ 다른 zone의 28%" — Tier 1, 2 적용


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


# ============================================================
# 2. Cut candidate generators
# ============================================================
def vertex_aligned_lines(polygon, margin=DEFAULT_BOUNDARY_MARGIN,
                          simplify_tol=0.15):
    """Type 1: vertex 좌표 통과 axis-aligned line.
    
    각 vertex의 x 좌표 → vertical line, y 좌표 → horizontal line.
    Boundary와 너무 가까운 좌표는 제외 (margin).
    
    simplify_tol: cut 후보 생성 시 polygon 단순화. 
    - saw-tooth (sub-grid noise) 제거
    - 곡면 vertex 폭증 방지
    - 실제 polygon은 변경 X (cut 후보의 좌표만 단순화된 vertex 사용)
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
        # tie-break: 짧은 line 우선
        valid.sort(key=lambda x: (-x[2], x[0].length))
    else:
        # tie-break: 더 정사각형 piece 우선 (max aspect 작은 것)
        valid.sort(key=lambda x: (-x[2],
                                    max(piece_aspect(p) for p in x[1])))
    
    return valid[0]


# ============================================================
# 4. Hierarchical selection (Type 2 > 1 > 0)
# ============================================================
def select_cut(polygon, min_zone_area, margin, min_cut_length,
                max_aspect=DEFAULT_MAX_PIECE_ASPECT,
                balance_threshold=DEFAULT_BALANCE_THRESHOLD):
    """3-tier hierarchical selection:
    
    Tier 1: vertex_aligned (axis-aligned)
        balance ≥ threshold 중 best
    Tier 2: oblique reflex_pair (사선)
        balance ≥ threshold 중 best, 짧은 순 tie-break
    Tier 3: axis_mid (fallback)
        threshold 무관 (마지막 안전망), balance best
    
    이러면 axis-aligned이 충분히 좋으면 우선, 안 좋으면 사선,
    그것도 안 되면 axis_mid가 무조건 자름.
    """
    # Tier 1: vertex_aligned (axis-aligned only by definition)
    cuts = vertex_aligned_lines(polygon, margin)
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
                          min_cut_length=DEFAULT_MIN_CUT_LENGTH):
    """k zones로 분할. Frame transform by -theta, partition, rotate back.
    
    sub-recursion에서는 theta=0 (이미 axis-aligned frame).
    """
    if k <= 1 or polygon.area < min_zone_area * 2:
        return [{'polygon': polygon, 'cut_history': []}]
    
    # Frame transform (rotate to axis-aligned)
    cx, cy = polygon.centroid.x, polygon.centroid.y
    if abs(theta) > 1e-3:
        P = sa.rotate(polygon, -np.degrees(theta), origin=(cx, cy))
    else:
        P = polygon
    
    # Recurse in rotated frame
    zones_rot = _partition_in_frame(P, k, min_zone_area, margin, min_cut_length)
    
    # Rotate back
    if abs(theta) > 1e-3:
        for z in zones_rot:
            z['polygon'] = sa.rotate(z['polygon'], np.degrees(theta),
                                       origin=(cx, cy))
    
    return zones_rot


def _partition_in_frame(P, k, min_zone_area, margin, min_cut_length):
    """Axis-aligned frame에서만 작동. theta 회전은 호출자가 처리."""
    if k <= 1 or P.area < min_zone_area * 2:
        return [{'polygon': P, 'cut_history': []}]
    
    selection = select_cut(P, min_zone_area, margin, min_cut_length)
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
        sub = _partition_in_frame(p, kk, min_zone_area, margin, min_cut_length)
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
                    min_cut_length=DEFAULT_MIN_CUT_LENGTH):
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
                                    min_cut_length=min_cut_length)
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
