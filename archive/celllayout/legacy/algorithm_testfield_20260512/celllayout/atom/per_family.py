"""
Pipeline 2M — Per-family proportional 0.3m + 50% rule

핵심:
- "Family" = 같은 theta + phase chain으로 묶이는 piece들
- 각 family는 자기 main rect의 dimension에 맞춰 proportional cell 크기 결정
- 같은 family 안의 모든 piece는 같은 cell 크기 + 같은 phase (seamless)
- 다른 family는 자체 cell 크기 (target 0.3m 근처)

이전 버전 대비:
- 02L: 0.3m 고정 모든 piece에 — sliver는 50% rule로 처리
- 02M: 0.3m target, 각 family별 proportional fit — 같은 family 안엔 sliver 0
       + 50% rule도 그대로 적용
"""
import numpy as np
import shapely.geometry as sg
import shapely.affinity as sa
from shapely.ops import unary_union
import matplotlib.pyplot as plt

from pathlib import Path

from celllayout.atom import angles as p2h
from celllayout.atom import fixed_grid as p2L
from celllayout.atom import lir_progressive as p2i
from celllayout.atom import theta as p2e


# ============================================================
# 1. Proportional cell size from main rect
# ============================================================
def compute_proportional_cell_size(main_rect, main_theta, target):
    """main_rect의 dimension에서 proportional cell_w, cell_h 계산.
    main을 정확히 N×M으로 나눠서 sliver 없게 함.
    
    Returns: (cell_w, cell_h, base_phase)
        base_phase = (cx, cy, ox, oy) — main의 grid 시작점 (sliver 0 보장)
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
# 2. Anisotropic grid (cell_w, cell_h) — 흰 공간 0
# ============================================================
def grid_no_skip_aniso(piece, theta, cell_w, cell_h,
                        phase_origin=None, seed=42, min_create_area=1e-6):
    """[v2 fix] cell의 intersection이 MultiPolygon이면 모든 부분 보존
    (이전: 가장 큰 부분만 살리고 나머지 버려서 polygon 안 빈 공간 발생)
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
            # MultiPolygon이면 모든 부분을 별도 cell로 (전엔 큰 것만 살림)
            if isinstance(inter, sg.MultiPolygon):
                parts = [g for g in inter.geoms
                         if isinstance(g, sg.Polygon) and g.area >= min_create_area]
            elif isinstance(inter, sg.Polygon):
                parts = [inter] if inter.area >= min_create_area else []
            else:
                # GeometryCollection 등 — Polygon 부분만 추출
                parts = []
                if hasattr(inter, 'geoms'):
                    for g in inter.geoms:
                        if isinstance(g, sg.Polygon) and g.area >= min_create_area:
                            parts.append(g)
            cells.extend(parts)
    
    return ([sa.rotate(c, np.degrees(theta), origin=(cx, cy)) for c in cells],
            (cx, cy, ox, oy))


def merge_below_50_aniso(cells, cell_w, cell_h,
                          threshold_ratio=0.5, max_iter=100):
    """50% 미만 cell을 가장 큰 인접 cell에 흡수.
    
    [v2 fix] 두 가지 손실 이슈 해결:
    1. Buffer 없이 실제 공유 boundary만 이웃으로 인식 (MultiPolygon merge 방지)
    2. Orphan (이웃 없는 작은 cell)을 nullify 안 함 — 그대로 보존
       (작은 cell이라도 빈 공간보단 낫다)
    """
    threshold = cell_w * cell_h * threshold_ratio
    cells = list(cells)
    skip_indices = set()  # orphan으로 판정된 cell — 다음 iteration에서 skip
    
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
        # 실제 공유 boundary 있는 이웃만 (buffer 사용 X)
        neighbors = []
        for j, other in enumerate(cells):
            if j == smallest_idx or other is None:
                continue
            inter = small.intersection(other)
            if inter.is_empty:
                continue
            # 1D intersection (line) — 실제 boundary 공유
            if hasattr(inter, 'length') and inter.length > 0.001:
                neighbors.append((j, other.area, inter.length))
        
        if not neighbors:
            # 진짜 orphan — 빈 공간 만드느니 그대로 둠
            skip_indices.add(smallest_idx)
            continue
        
        # 가장 긴 boundary 공유 이웃 우선 (가장 자연스러운 merge)
        biggest_j = max(neighbors, key=lambda x: x[2])[0]
        merged = small.union(cells[biggest_j])
        # 실제 boundary 공유 cell이면 union이 단일 polygon이어야 함
        if isinstance(merged, sg.Polygon):
            cells[biggest_j] = merged
        elif isinstance(merged, sg.MultiPolygon):
            # 안전장치: 그래도 MultiPolygon이면 모든 부분 보존
            # 가장 큰 부분만 biggest_j 자리에, 나머지는 새 cell로 추가
            geoms = sorted(merged.geoms, key=lambda g: -g.area)
            cells[biggest_j] = geoms[0]
            for extra in geoms[1:]:
                cells.append(extra)
        cells[smallest_idx] = None
    
    return [c for c in cells if c is not None]


# ============================================================
# 3. Recursive with per-family proportional + 50% rule
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
    Per-family proportional cell sizing.
    
    Family = same theta + phase chain. 한 family 안 모든 piece가 같은 cell_w, cell_h.
    Theta가 parent와 다르면 새 family로 cell_w, cell_h 다시 계산.
    
    Returns: (cells, pieces_info, root_main_rect, next_family_id)
    """
    if _next_family_id is None:
        _next_family_id = [_family_id + 1]  # 가변 카운터
    
    rng = np.random.default_rng(seed)
    all_cells = []
    pieces_info = []
    
    main_rect, main_theta, _ = p2i.find_main_rect_refined(
        polygon, resolution=lir_resolution)
    
    can_recurse = (_depth < max_depth and
                   polygon.area >= min_recurse_area and
                   main_rect is not None)
    has_meaningful_lir = (main_rect is not None and
                          main_rect.area >= polygon.area * min_lir_ratio)
    
    # 이 호출의 effective theta 결정
    if main_rect is not None and has_meaningful_lir:
        effective_theta = main_theta
    else:
        effective_theta = p2e.piece_direct_theta(polygon, polygon, 1.0)
        if effective_theta is None:
            effective_theta = _parent_theta if _parent_theta is not None else 0.0
    
    # Family 결정
    is_same_family = (_parent_theta is not None and
                       p2h.angle_diff(effective_theta, _parent_theta)
                       < np.radians(2))
    
    if is_same_family:
        # 같은 family — parent의 cell 크기와 phase 그대로
        family_id = _family_id
        cell_w = _parent_cell_w
        cell_h = _parent_cell_h
        phase = _parent_phase
        effective_theta = _parent_theta  # 정확히 일치
    else:
        # 새 family — 이 polygon의 main rect로 proportional 재계산
        family_id = _next_family_id[0]
        _next_family_id[0] += 1
        if main_rect is not None:
            cell_w, cell_h, phase = compute_proportional_cell_size(
                main_rect, effective_theta, target_cell_size)
        else:
            # LIR 못 찾음 — polygon bbox 기반 fallback
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
    
    if not (can_recurse and has_meaningful_lir):
        # === TERMINAL ===
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


def auto_partition_per_family(footprint, target_cell_size=0.3, seed=42,
                                max_depth=3, min_lir_ratio=0.4,
                                min_recurse_area=8.0):
    cells, pieces, root_main, _ = recursive_progressive_per_family(
        footprint, target_cell_size=target_cell_size, seed=seed,
        max_depth=max_depth, min_lir_ratio=min_lir_ratio,
        min_recurse_area=min_recurse_area,
    )
    return {'cells': cells, 'pieces': pieces,
            'root_main_rect': root_main}


# ============================================================
# 4. Test cases
# ============================================================
def make_cases():
    cases = []
    cases.append(('A: awkward dim (12.3x8.7)', sg.box(0, 0, 12.3, 8.7)))
    main = sg.box(0, 0, 12, 8)
    wing = sa.translate(sa.rotate(sg.box(0, 0, 6, 4), 25, origin=(0, 0)),
                        xoff=10, yoff=6)
    cases.append(('B: rotated wing 25deg', unary_union([main, wing])))
    bump = sg.Point(0, 4).buffer(2.0, resolution=20)
    cases.append(('C: curved bump', unary_union([main, bump])))
    outer = unary_union([main, wing, bump])
    core1 = sg.box(3, 2.5, 5.5, 4.5)
    core2 = sa.translate(sa.rotate(sg.box(0, 0, 1.5, 1.5), 25, origin=(0, 0)),
                         xoff=12.5, yoff=8.5)
    cases.append(('D: full complex (2 holes)',
                  outer.difference(unary_union([core1, core2]))))
    main_rot = sa.rotate(sg.box(0, 0, 10.7, 6.3), 15, origin=(5, 3))
    extra = sa.translate(sa.rotate(sg.box(0, 0, 4, 3), 15, origin=(5, 3)),
                          xoff=8, yoff=2)
    cases.append(('E: rotated main 15deg', unary_union([main_rot, extra])))
    return cases


# ============================================================
# 5. Visualization — color by family
# ============================================================
def plot_per_family(footprint, cells, pieces, ax, title):
    family_colors = ['#9ad0c2', '#fdb462', '#a481c4', '#f4a3a3',
                     '#88c4dc', '#c2d57a']
    family_edges = ['#2a5a51', '#a85e16', '#4a2e6e', '#7a3030',
                    '#1f5a72', '#5a6e30']
    
    for cell, piece_id in cells:
        if isinstance(cell, sg.Polygon):
            polys = [cell]
        elif hasattr(cell, 'geoms'):
            polys = list(cell.geoms)
        else: continue
        info = pieces[piece_id]
        fid = info.get('family_id', 0)
        face = family_colors[fid % len(family_colors)]
        edge = family_edges[fid % len(family_edges)]
        for p in polys:
            if p.is_empty: continue
            x, y = p.exterior.xy
            ax.fill(x, y, color=face, edgecolor=edge,
                    linewidth=0.3, alpha=0.85)
    
    xs, ys = footprint.exterior.xy
    ax.plot(xs, ys, color='black', linewidth=2.0, zorder=10)
    for hole in footprint.interiors:
        hx, hy = hole.xy
        ax.fill(hx, hy, color='#333', alpha=0.85, zorder=10)
    
    # Family별 cell 크기 라벨 (대표 piece 한 개씩)
    family_labeled = set()
    for info in pieces:
        fid = info.get('family_id', 0)
        if fid in family_labeled or info.get('n_cells', 0) < 5:
            continue
        family_labeled.add(fid)
        cx_p = info['polygon'].centroid.x
        cy_p = info['polygon'].centroid.y
        cw, ch = info.get('cell_w', 0), info.get('cell_h', 0)
        edge = family_edges[fid % len(family_edges)]
        ax.text(cx_p, cy_p,
                f"fam{fid}\n{cw:.3f}x{ch:.3f}m",
                color=edge, fontsize=8, fontweight='bold', ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                         edgecolor=edge, linewidth=0.6, alpha=0.9))
    
    ax.set_aspect('equal'); ax.grid(True, alpha=0.3)
    n_cells = sum(p.get('n_cells', 0) for p in pieces)
    n_families = len(set(p.get('family_id', 0) for p in pieces))
    ax.set_title(f"{title}\n#families={n_families}, #pieces={len(pieces)}, "
                 f"#cells={n_cells}",
                 fontsize=10, fontweight='bold')


def main():
    cases = make_cases()
    fig, axes = plt.subplots(len(cases), 2, figsize=(20, 4.5 * len(cases)))
    
    for row, (name, footprint) in enumerate(cases):
        print(f"\n=== {name} ===")
        
        # NEW: per-family proportional 0.3m
        result_new = auto_partition_per_family(footprint, target_cell_size=0.3,
                                                seed=42)
        n_new = sum(p['n_cells'] for p in result_new['pieces'])
        n_fam = len(set(p['family_id'] for p in result_new['pieces']))
        print(f"  NEW (per-family proportional 0.3m + 50%): "
              f"{n_fam} families, {len(result_new['pieces'])} pieces, "
              f"{n_new} cells")
        for fid in sorted(set(p['family_id'] for p in result_new['pieces'])):
            ps = [p for p in result_new['pieces'] if p['family_id'] == fid]
            cw, ch = ps[0]['cell_w'], ps[0]['cell_h']
            theta_deg = np.degrees(ps[0]['theta'])
            print(f"    family {fid}: cell={cw:.4f}x{ch:.4f}m, "
                  f"theta={theta_deg:.1f}deg, "
                  f"{len(ps)} pieces, {sum(p['n_cells'] for p in ps)} cells")
        
        # OLD: fixed 0.3m
        result_old = p2L.auto_partition_final(footprint, cell_size=0.3, seed=42)
        n_old = sum(p['n_cells'] for p in result_old['pieces'])
        print(f"  OLD (fixed 0.3m + 50%): "
              f"{len(result_old['pieces'])} pieces, {n_old} cells")
        
        plot_per_family(footprint, result_new['cells'], result_new['pieces'],
                        axes[row, 0], f"{name} [NEW: per-family]")
        # OLD plot에선 family_id 없으니 piece_id로 색
        for p in result_old['pieces']:
            p['family_id'] = p['depth']  # 임시
        plot_per_family(footprint, result_old['cells'], result_old['pieces'],
                        axes[row, 1], f"{name} [OLD: fixed 0.3m]")
    
    plt.suptitle("Per-family proportional 0.3m + 50% rule (left)\n"
                 "vs Fixed 0.3m + 50% rule (right)",
                 fontsize=14, fontweight='bold', y=1.001)
    plt.tight_layout()
    out = Path(__file__).resolve().parents[3] / 'outputs' / 'figures' / '02M_per_family.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=110,
                bbox_inches='tight')
    print(f"\nsaved: {out}")


if __name__ == "__main__":
    main()
