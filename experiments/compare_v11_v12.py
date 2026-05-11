"""Compare new clean algorithm (12) with previous (11)."""
import sys
from pathlib import Path
import numpy as np
import shapely.geometry as sg
from shapely.ops import unary_union
import matplotlib.pyplot as plt
from matplotlib import font_manager

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from roomlayout_cell.experiments import showcase_cases as p11
from roomlayout_cell.zoning import pipeline12 as p12


def configure_fonts():
    font_path = Path('/usr/share/fonts/truetype/nanum/NanumGothic.ttf')
    if font_path.exists():
        font_manager.fontManager.addfont(font_path)
        plt.rcParams['font.family'] = 'NanumGothic'
    plt.rcParams['axes.unicode_minus'] = False


def piece_quality_mrr(piece):
    """평가용 metric (알고리즘 외부)."""
    if piece.is_empty or piece.area < 1e-6:
        return {'aspect': 99, 'compactness': 0, 'score': 0}
    try:
        mbr = piece.minimum_rotated_rectangle
        coords = list(mbr.exterior.coords)
        e1 = np.hypot(coords[1][0] - coords[0][0], coords[1][1] - coords[0][1])
        e2 = np.hypot(coords[2][0] - coords[1][0], coords[2][1] - coords[1][1])
        if min(e1, e2) < 1e-6:
            return {'aspect': 99, 'compactness': 0, 'score': 0}
        aspect = max(e1, e2) / min(e1, e2)
        compactness = piece.area / mbr.area
    except Exception:
        return {'aspect': 99, 'compactness': 0, 'score': 0}
    if 1.0 <= aspect <= 2.5:
        asp_s = 1.0
    elif aspect <= 4.0:
        asp_s = 1.0 - (aspect - 2.5) / 1.5 * 0.5
    else:
        asp_s = 0.3
    return {
        'aspect': aspect, 'compactness': compactness,
        'score': 0.5 * compactness + 0.5 * asp_s,
    }


def compare():
    cases = p11.make_showcase_cases()
    
    print(f"{'#':>3} {'Case':<28} | {'v11 (점수)':^20} | {'v12 (clean)':^25}")
    print(f"{'':>3} {'':<28} | {'#zn  q   gap%':<18} | {'#zn  q   gap%  cuts':<25}")
    print("=" * 100)
    
    results = []
    for i, (name, fp) in enumerate(cases):
        try:
            # v11
            zones11, fams11 = p11.zone_footprint(fp)
            q11 = np.mean([piece_quality_mrr(z['polygon'])['score']
                            for z in zones11])
            gap11 = fp.difference(unary_union([z['polygon']
                                                 for z in zones11])).area
            gap11_pct = 100 * gap11 / fp.area
            
            # v12
            zones12, fams12 = p12.zone_footprint(fp)
            q12 = np.mean([piece_quality_mrr(z['polygon'])['score']
                            for z in zones12])
            gap12 = fp.difference(unary_union([z['polygon']
                                                 for z in zones12])).area
            gap12_pct = 100 * gap12 / fp.area
            
            # Cut type 통계
            cut_types = {}
            for z in zones12:
                for ct in z.get('cut_history', []):
                    cut_types[ct] = cut_types.get(ct, 0) + 1
            cuts_summary = ",".join(f"{k[:3]}{v}" for k, v in cut_types.items())
            
            improve = q12 - q11
            flag = " ★" if improve > 0.03 else (" ⚠" if improve < -0.03 else "")
            
            print(f"{i+1:>3} {name:<28} | "
                  f"#{len(zones11)} q{q11:.2f} g{gap11_pct:.1f}% | "
                  f"#{len(zones12)} q{q12:.2f} g{gap12_pct:.1f}% {cuts_summary} | "
                  f"{improve:>+5.2f}{flag}")
            
            results.append({
                'name': name, 'fp': fp,
                'zones11': zones11, 'zones12': zones12,
                'fams11': fams11, 'fams12': fams12,
                'q11': q11, 'q12': q12,
                'gap11': gap11_pct, 'gap12': gap12_pct,
                'improve': improve,
            })
        except Exception as e:
            print(f"{i+1:>3} {name:<28} | ERROR: {e}")
    
    return results


def visualize(results, n_per_fig=12):
    """Side-by-side per case (v11 left, v12 right)."""
    n_groups = (len(results) + n_per_fig - 1) // n_per_fig
    
    for g in range(n_groups):
        sub = results[g * n_per_fig: (g + 1) * n_per_fig]
        n = len(sub)
        fig, axes = plt.subplots(n, 2, figsize=(10, 4 * n))
        if n == 1:
            axes = axes.reshape(1, -1)
        
        for i, r in enumerate(sub):
            p11.plot_zone_result(r['fp'], r['zones11'], r['fams11'], axes[i, 0],
                                  title=f"v11: {r['name']}\n"
                                         f"#zones={len(r['zones11'])}, "
                                         f"q={r['q11']:.2f}, gap={r['gap11']:.1f}%")
            
            # v12 시각화 (간단 버전)
            colors = ['#9ad0c2', '#fdb462', '#a481c4', '#f4a3a3',
                       '#88c4dc', '#c2d57a', '#e1a8d4', '#a8c8e1',
                       '#ffd700', '#90ee90', '#ffb6c1', '#dda0dd']
            ax = axes[i, 1]
            for z in r['zones12']:
                poly = z['polygon']
                zid = z['zone_id']
                x, y = poly.exterior.xy
                ax.fill(x, y, color=colors[zid % len(colors)],
                        edgecolor='black', linewidth=1.0, alpha=0.75)
                cx_p, cy_p = poly.centroid.x, poly.centroid.y
                ax.text(cx_p, cy_p, f"Z{zid}\n{poly.area:.0f}",
                         ha='center', va='center', fontsize=7,
                         bbox=dict(boxstyle='round,pad=0.15',
                                    facecolor='white', alpha=0.85))
            xs, ys = r['fp'].exterior.xy
            ax.plot(xs, ys, color='black', linewidth=1.8, zorder=10)
            for hole in r['fp'].interiors:
                hx, hy = hole.xy
                ax.fill(hx, hy, color='#444', zorder=10)
            if len(r['fams12']) > 1:
                for f in r['fams12']:
                    xs, ys = f['polygon'].exterior.xy
                    ax.plot(xs, ys, '--', color='red', linewidth=1.3,
                             alpha=0.6, zorder=11)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            ax.set_title(f"v12 (clean): {r['name']}\n"
                          f"#zones={len(r['zones12'])}, q={r['q12']:.2f}, "
                          f"gap={r['gap12']:.1f}%, Δ={r['improve']:+.2f}",
                          fontsize=9, fontweight='bold')
        
        plt.suptitle(f"v11 (점수기반) vs v12 (deterministic, vertex-first) "
                     f"— Group {g+1}",
                     fontsize=13, fontweight='bold', y=1.001)
        plt.tight_layout()
        out = PROJECT_ROOT / 'outputs' / 'figures' / f'12_compare_g{g+1}.png'
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, dpi=100, bbox_inches='tight')
        plt.close(fig)
        print(f"saved: {out}")


if __name__ == "__main__":
    configure_fonts()
    results = compare()
    visualize(results)
