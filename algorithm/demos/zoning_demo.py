"""Run zoning on showcase cases and save side-by-side figures.

Usage:
    python demo.py                # all 33 cases → outputs/g{1,2,3}.png
    python demo.py 11 14 29       # only specified case indices (1-based)
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from shapely.ops import unary_union

ALGORITHM_ROOT = Path(__file__).resolve().parents[1]
if str(ALGORITHM_ROOT) not in sys.path:
    sys.path.insert(0, str(ALGORITHM_ROOT))

from celllayout import cases as case_mod
from celllayout import graph as graph_mod
from celllayout import zoning


OUT_DIR = ALGORITHM_ROOT / 'outputs' / 'zoning'
COLORS = ['#9ad0c2', '#fdb462', '#a481c4', '#f4a3a3', '#88c4dc',
          '#c2d57a', '#e1a8d4', '#a8c8e1', '#ffd700', '#90ee90',
          '#ffb6c1', '#dda0dd', '#b0e0e6', '#ffdab9', '#cd9b9b',
          '#98fb98', '#f0e68c', '#d8bfd8', '#afeeee', '#ffa07a']


def configure_fonts():
    fp = Path('/usr/share/fonts/truetype/nanum/NanumGothic.ttf')
    if fp.exists():
        font_manager.fontManager.addfont(fp)
        plt.rcParams['font.family'] = 'NanumGothic'
    plt.rcParams['axes.unicode_minus'] = False


def quality(piece):
    """Informational MRR-based quality (not used by algorithm)."""
    asp = zoning.piece_aspect(piece)
    try:
        cmp = piece.area / piece.minimum_rotated_rectangle.area
    except Exception:
        cmp = 0
    if 1.0 <= asp <= 2.5:
        asp_s = 1.0
    elif asp <= 4.0:
        asp_s = 1.0 - (asp - 2.5) / 1.5 * 0.5
    else:
        asp_s = 0.3
    return 0.5 * cmp + 0.5 * asp_s


def stats(zones, fp, zone_graph=None):
    polys = [z['polygon'] for z in zones]
    areas = [p.area for p in polys]
    avg_q = float(np.mean([quality(p) for p in polys])) if polys else 0
    gap_pct = 100 * fp.difference(unary_union(polys)).area / fp.area
    out = {'n': len(zones), 'q': avg_q, 'gap': gap_pct,
           'min': min(areas), 'max': max(areas), 'mean': float(np.mean(areas))}
    if zone_graph is not None:
        out.update({f"graph_{k}": v for k, v in graph_mod.graph_stats(zone_graph).items()})
    return out


def plot_zone_graph(ax, zones, zone_graph):
    """Overlay actual shared-boundary graph contacts and centroid nodes."""
    by_id = {z['zone_id']: z for z in zones}
    for edge in zone_graph['edges']:
        za = by_id[edge['zone_a']]['polygon']
        zb = by_id[edge['zone_b']]['polygon']
        _plot_centroid_connector(ax, za, zb, edge['door_capable'])
        contact = graph_mod.shared_boundary_geometry(za, zb)
        _plot_contact(ax, contact, edge['door_capable'])
    for node in zone_graph['nodes']:
        x, y = node['centroid']
        ax.plot(x, y, marker='o', markersize=2.7, color='#12395d', zorder=13)


def _plot_centroid_connector(ax, poly_a, poly_b, door_capable):
    color = '#0d3b66' if door_capable else '#5d7f9f'
    ax.plot(
        [poly_a.centroid.x, poly_b.centroid.x],
        [poly_a.centroid.y, poly_b.centroid.y],
        color=color,
        linewidth=0.65 if door_capable else 0.45,
        linestyle='--',
        alpha=0.55,
        zorder=11.5,
    )


def _plot_contact(ax, geom, door_capable):
    color = '#1f4e79' if door_capable else '#6f8fb3'
    linewidth = 2.4 if door_capable else 1.2
    if geom.is_empty:
        return
    if geom.geom_type in ('LineString', 'LinearRing'):
        xs, ys = geom.xy
        ax.plot(xs, ys, color=color, linewidth=linewidth, alpha=0.9, zorder=12)
    elif geom.geom_type == 'MultiLineString':
        for part in geom.geoms:
            _plot_contact(ax, part, door_capable)
    elif geom.geom_type == 'GeometryCollection':
        for part in geom.geoms:
            _plot_contact(ax, part, door_capable)


def plot_zones(ax, fp, zones, families, title, zone_graph=None):
    for z in zones:
        p = z['polygon']
        if p.is_empty:
            continue
        x, y = p.exterior.xy
        ax.fill(x, y, color=COLORS[z['zone_id'] % len(COLORS)],
                edgecolor='black', linewidth=0.8, alpha=0.75)
        cx, cy = p.centroid.x, p.centroid.y
        ax.text(cx, cy, f"Z{z['zone_id']}\n{p.area:.0f}",
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
    if zone_graph is not None:
        plot_zone_graph(ax, zones, zone_graph)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_title(title, fontsize=8, fontweight='bold')


def visualize(results, n_per_fig=12):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_groups = (len(results) + n_per_fig - 1) // n_per_fig
    for g in range(n_groups):
        sub = results[g * n_per_fig: (g + 1) * n_per_fig]
        n = len(sub)
        fig, axes = plt.subplots(n, 1, figsize=(8, 4 * n))
        if n == 1:
            axes = [axes]
        for ax, r in zip(axes, sub):
            s = r['s']
            plot_zones(ax, r['fp'], r['zones'], r['fams'],
                       f"{r['name']}  #z={s['n']} q={s['q']:.2f} "
                       f"gap={s['gap']:.1f}%  "
                       f"avg={s['mean']:.1f} [min={s['min']:.1f}/max={s['max']:.1f}]  "
                       f"edges={s['graph_edges']} comps={s['graph_component_count']} "
                       f"iso={len(s['graph_isolated_nodes'])}",
                       r.get('graph'))
        plt.suptitle(f"celllayout zoning — Group {g + 1}",
                     fontsize=12, fontweight='bold', y=1.001)
        plt.tight_layout()
        out = OUT_DIR / f'g{g + 1}.png'
        plt.savefig(out, dpi=100, bbox_inches='tight')
        plt.close(fig)
        print(f'saved: {out}')


def main(argv):
    cases = case_mod.make_cases()
    if argv:
        idx = [int(a) - 1 for a in argv]
        cases = [cases[i] for i in idx if 0 <= i < len(cases)]
    print(f"{'#':>3} {'Case':<26} | #zn   q   gap%  avg[min/max]")
    print('=' * 70)
    results = []
    for i, (name, fp) in enumerate(cases):
        try:
            zones, fams = zoning.zone_footprint(fp)
            zone_graph = graph_mod.build_zone_graph(zones)
            s = stats(zones, fp, zone_graph)
            print(f"{i + 1:>3} {name:<26} | "
                  f"#{s['n']:<2} q{s['q']:.2f} g{s['gap']:.1f}% "
                  f"a{s['mean']:.1f} [{s['min']:.1f}/{s['max']:.1f}] "
                  f"E{s['graph_edges']} D{s['graph_door_edges']} "
                  f"C{s['graph_component_count']} iso{len(s['graph_isolated_nodes'])}")
            results.append({'name': name, 'fp': fp, 'zones': zones,
                            'fams': fams, 'graph': zone_graph, 's': s})
        except Exception as e:
            print(f"{i + 1:>3} {name:<26} | ERROR: {e}")
    visualize(results)


if __name__ == '__main__':
    configure_fonts()
    main(sys.argv[1:])
