"""Compare pipeline12 (zone=room) vs pipeline20 (zone=sub-room unit).

p12는 zone 하나가 곧 방. p20은 zone을 잘게 쪼개서 추후 합쳐 방을 만들거나
복도(atom-cell 기반) 자리로 쓰기 위한 sub-room building block.

비교 방식:
- p12: 기존 auto_target (25m²/zone, cap 10)
- p20: fine_target (10m²/zone, no cap) — sub-room 컨셉을 실제로 보이게.
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
from shapely.ops import unary_union

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from roomlayout_cell.experiments import showcase_cases as cases_mod
from roomlayout_cell.zoning import pipeline12 as p12
from roomlayout_cell.zoning import pipeline20 as p20


def configure_fonts():
    font_path = Path('/usr/share/fonts/truetype/nanum/NanumGothic.ttf')
    if font_path.exists():
        font_manager.fontManager.addfont(font_path)
        plt.rcParams['font.family'] = 'NanumGothic'
    plt.rcParams['axes.unicode_minus'] = False


def piece_quality_mrr(piece):
    """평가용 metric (알고리즘 외부). compare_v11_v12.py와 동일."""
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


def fine_target_zones(fp, area_per_zone=10.0):
    """p20용 임시 target zones. cap 없음.

    p20.auto_target_zones는 아직 cap=10이라 sub-room 분할이 안 보임.
    auto_target_zones 본격 수정 시 흡수/폐기 예정.
    """
    return max(2, round(fp.area / area_per_zone))


def stats(zones, fp):
    polys = [z['polygon'] for z in zones]
    areas = [p.area for p in polys]
    avg_q = float(np.mean([piece_quality_mrr(p)['score'] for p in polys]))
    gap_pct = 100 * fp.difference(unary_union(polys)).area / fp.area
    return {
        'n': len(zones),
        'q': avg_q,
        'gap': gap_pct,
        'min_area': min(areas) if areas else 0,
        'max_area': max(areas) if areas else 0,
        'mean_area': float(np.mean(areas)) if areas else 0,
    }


def compare():
    cases = cases_mod.make_showcase_cases()

    print(f"{'#':>3} {'Case':<26} | "
          f"{'p12 (room)':<24} | {'p20 (sub-room)':<32} | Δq")
    print(f"{'':>3} {'':<26} | "
          f"{'#z   q   gap%  area':<24} | "
          f"{'#z   q   gap%  area  min/max':<32} |")
    print("=" * 110)

    results = []
    for i, (name, fp) in enumerate(cases):
        try:
            zones12, fams12 = p12.zone_footprint(fp)
            k20 = fine_target_zones(fp)
            zones20, fams20 = p20.zone_footprint(fp, k=k20)

            s12 = stats(zones12, fp)
            s20 = stats(zones20, fp)

            dq = s20['q'] - s12['q']
            flag = " ★" if dq > 0.03 else (" ⚠" if dq < -0.03 else "")

            print(f"{i+1:>3} {name:<26} | "
                  f"#{s12['n']:<2} q{s12['q']:.2f} g{s12['gap']:.1f}% "
                  f"a{s12['mean_area']:.1f} | "
                  f"#{s20['n']:<2} q{s20['q']:.2f} g{s20['gap']:.1f}% "
                  f"a{s20['mean_area']:.1f} "
                  f"[{s20['min_area']:.1f}/{s20['max_area']:.1f}] | "
                  f"{dq:>+5.2f}{flag}")

            results.append({
                'name': name, 'fp': fp,
                'zones12': zones12, 'fams12': fams12,
                'zones20': zones20, 'fams20': fams20,
                's12': s12, 's20': s20,
                'dq': dq, 'k20': k20,
            })
        except Exception as e:
            print(f"{i+1:>3} {name:<26} | ERROR: {e}")

    return results


_COLORS = ['#9ad0c2', '#fdb462', '#a481c4', '#f4a3a3', '#88c4dc',
           '#c2d57a', '#e1a8d4', '#a8c8e1', '#ffd700', '#90ee90',
           '#ffb6c1', '#dda0dd', '#b0e0e6', '#ffdab9', '#cd9b9b',
           '#98fb98', '#f0e68c', '#d8bfd8', '#afeeee', '#ffa07a']


def plot_zones(ax, fp, zones, families, title, show_zid=True):
    for z in zones:
        poly = z['polygon']
        zid = z['zone_id']
        if poly.is_empty:
            continue
        x, y = poly.exterior.xy
        ax.fill(x, y, color=_COLORS[zid % len(_COLORS)],
                edgecolor='black', linewidth=0.8, alpha=0.75)
        if show_zid:
            cx, cy = poly.centroid.x, poly.centroid.y
            ax.text(cx, cy, f"Z{zid}\n{poly.area:.0f}",
                    ha='center', va='center', fontsize=6,
                    bbox=dict(boxstyle='round,pad=0.1',
                              facecolor='white', alpha=0.8))
    xs, ys = fp.exterior.xy
    ax.plot(xs, ys, color='black', linewidth=1.6, zorder=10)
    for hole in fp.interiors:
        hx, hy = hole.xy
        ax.fill(hx, hy, color='#444', zorder=10)
    if len(families) > 1:
        for f in families:
            xs, ys = f['polygon'].exterior.xy
            ax.plot(xs, ys, '--', color='red', linewidth=1.0,
                    alpha=0.55, zorder=11)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_title(title, fontsize=8, fontweight='bold')


def visualize(results, n_per_fig=12):
    n_groups = (len(results) + n_per_fig - 1) // n_per_fig

    for g in range(n_groups):
        sub = results[g * n_per_fig: (g + 1) * n_per_fig]
        n = len(sub)
        fig, axes = plt.subplots(n, 2, figsize=(10, 3.6 * n))
        if n == 1:
            axes = axes.reshape(1, -1)

        for i, r in enumerate(sub):
            s12, s20 = r['s12'], r['s20']
            plot_zones(
                axes[i, 0], r['fp'], r['zones12'], r['fams12'],
                f"p12 (room): {r['name']}\n"
                f"#z={s12['n']} q={s12['q']:.2f} gap={s12['gap']:.1f}% "
                f"ā={s12['mean_area']:.1f}m²",
            )
            plot_zones(
                axes[i, 1], r['fp'], r['zones20'], r['fams20'],
                f"p20 (sub-room, k={r['k20']}): {r['name']}\n"
                f"#z={s20['n']} q={s20['q']:.2f} gap={s20['gap']:.1f}% "
                f"ā={s20['mean_area']:.1f} "
                f"[min={s20['min_area']:.1f}/max={s20['max_area']:.1f}]"
                f"  Δq={r['dq']:+.2f}",
            )

        plt.suptitle(
            f"p12 (zone=room) vs p20 (zone=sub-room unit) — Group {g+1}",
            fontsize=12, fontweight='bold', y=1.001,
        )
        plt.tight_layout()
        out = PROJECT_ROOT / 'outputs' / 'figures' / f'p12_vs_p20_g{g+1}.png'
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, dpi=100, bbox_inches='tight')
        plt.close(fig)
        print(f"saved: {out}")


if __name__ == "__main__":
    configure_fonts()
    results = compare()
    visualize(results)
