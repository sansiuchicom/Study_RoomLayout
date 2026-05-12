"""Phase 1/2 diagnostic visualization.

Phase 1 renders a ``ShapeInput`` with each part in a distinct translucent
color so that overlapping parts (e.g. wing protrusions) remain visible.

Phase 2 renders a panel of sample interval splits showing how
``split_interval`` decomposes various lengths under the dimension policy.
"""

from __future__ import annotations

from math import degrees
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import shapely.geometry as sg
from matplotlib import font_manager
from shapely.ops import unary_union

from .dimensions import DimensionPolicy, is_quantum_aligned, split_interval
from .schema import ShapeInput, ShapePart, part_theta
from .territory import Territory, resolve_territories


PART_COLORS = [
    "#9ad0c2",
    "#fdb462",
    "#a6cee3",
    "#fb9a99",
    "#b2df8a",
    "#cab2d6",
    "#fdd087",
    "#b3cde3",
]


def configure_fonts():
    font_path = Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
    if font_path.exists():
        font_manager.fontManager.addfont(font_path)
        plt.rcParams["font.family"] = "NanumGothic"
    plt.rcParams["axes.unicode_minus"] = False


def save_input_figure(
    shape: ShapeInput,
    path,
    *,
    title: str | None = None,
    show_vertices: bool = True,
) -> Path:
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    for idx, part in enumerate(shape.parts):
        color = PART_COLORS[idx % len(PART_COLORS)]
        _draw_part(ax, part, color, idx)
        if show_vertices:
            _draw_vertices(ax, part)

    _draw_footprint_outline(ax, shape)
    _finish_axis(ax, shape)
    ax.set_title(title or shape.name, fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def _draw_part(ax, part: ShapePart, color: str, idx: int):
    xs, ys = zip(*part.exterior)
    ax.fill(
        list(xs) + [xs[0]],
        list(ys) + [ys[0]],
        facecolor=color,
        edgecolor="#333333",
        alpha=0.55,
        linewidth=1.0,
    )
    for hole in part.holes:
        hx, hy = zip(*hole)
        ax.fill(
            list(hx) + [hx[0]],
            list(hy) + [hy[0]],
            facecolor="#444444",
            edgecolor="#111111",
            alpha=1.0,
            linewidth=0.8,
        )

    poly = _to_shapely(part)
    if not poly.is_empty:
        rp = poly.representative_point()
        theta_deg = degrees(part_theta(part))
        ax.text(
            rp.x,
            rp.y,
            f"P{idx}\n{theta_deg:.1f}°",
            ha="center",
            va="center",
            fontsize=8,
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": "white",
                "edgecolor": "#777777",
                "linewidth": 0.4,
                "alpha": 0.88,
            },
        )


def _draw_vertices(ax, part: ShapePart):
    for x, y in part.exterior:
        ax.plot(x, y, "o", markersize=3, color="#222222", zorder=10)
    for hole in part.holes:
        for x, y in hole:
            ax.plot(x, y, "o", markersize=2.5, color="#660000", zorder=10)


def _draw_footprint_outline(ax, shape: ShapeInput):
    footprint = unary_union([_to_shapely(p) for p in shape.parts])
    for poly in _polygon_parts(footprint):
        x, y = poly.exterior.xy
        ax.plot(x, y, color="#111111", linewidth=1.5, zorder=20)
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.plot(hx, hy, color="#111111", linewidth=1.2, zorder=20)


def _finish_axis(ax, shape: ShapeInput):
    footprint = unary_union([_to_shapely(p) for p in shape.parts])
    minx, miny, maxx, maxy = footprint.bounds
    pad = max(maxx - minx, maxy - miny, 1.0) * 0.08
    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)
    ax.set_aspect("equal")
    ax.grid(True, color="#dddddd", linewidth=0.5, alpha=0.8)
    ax.tick_params(labelsize=7)


def save_territory_figure(
    shape: ShapeInput,
    path,
    *,
    title: str | None = None,
) -> Path:
    """Render the input parts (faint, dashed) and their resolved territories on top.

    The faint dashed outlines show the original design parts including overlap;
    the filled regions show each part's final territory after overlap resolution.
    """
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    territories = resolve_territories(shape)

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    # 1. faint original parts (design outline, before resolution)
    for idx, part in enumerate(shape.parts):
        color = PART_COLORS[idx % len(PART_COLORS)]
        xs, ys = zip(*part.exterior)
        ax.fill(
            list(xs) + [xs[0]], list(ys) + [ys[0]],
            facecolor=color, edgecolor=color, alpha=0.15, linewidth=0,
        )
        ax.plot(
            list(xs) + [xs[0]], list(ys) + [ys[0]],
            color="#888888", linewidth=0.7, linestyle="--", zorder=2,
        )

    # 2. resolved territories on top — one label per piece
    for t in territories:
        color = PART_COLORS[t.part_id % len(PART_COLORS)]
        multi_piece = len(t.pieces) > 1
        for piece_idx, piece in enumerate(t.pieces):
            xs, ys = zip(*piece.exterior)
            ax.fill(
                list(xs) + [xs[0]], list(ys) + [ys[0]],
                facecolor=color, edgecolor="#333333",
                alpha=0.75, linewidth=1.1, zorder=5,
            )
            for hole in piece.holes:
                hx, hy = zip(*hole)
                ax.fill(
                    list(hx) + [hx[0]], list(hy) + [hy[0]],
                    facecolor="#444444", edgecolor="#111111",
                    alpha=1.0, linewidth=0.8, zorder=6,
                )

            poly = sg.Polygon(piece.exterior, [list(h) for h in piece.holes])
            if poly.is_empty:
                continue
            rp = poly.representative_point()
            label_id = f"P{t.part_id}.{piece_idx}" if multi_piece else f"P{t.part_id}"
            ax.text(
                rp.x, rp.y,
                f"{label_id}\n{degrees(t.theta):.1f}°\n[{t.kind}]",
                ha="center", va="center", fontsize=7,
                bbox={
                    "boxstyle": "round,pad=0.2", "facecolor": "white",
                    "edgecolor": "#777777", "linewidth": 0.4, "alpha": 0.88,
                },
                zorder=10,
            )

    # 3. footprint outline for reference
    _draw_footprint_outline(ax, shape)
    _finish_axis(ax, shape)
    ax.set_title(title or f"{shape.name} (resolved territories)", fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def save_dimension_examples_figure(
    path,
    *,
    lengths: tuple[float, ...] = (0.18, 0.55, 1.00, 1.03, 2.05, 3.70, 4.10, 5.50, 8.40, 12.30),
    policy: DimensionPolicy | None = None,
) -> Path:
    """Render a stacked-bar panel of ``split_interval`` outputs for sample lengths."""
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    policy = policy or DimensionPolicy()

    fig, ax = plt.subplots(figsize=(10, max(3.5, len(lengths) * 0.5)), constrained_layout=True)

    target_color = "#9ad0c2"
    deviation_color = "#fdb462"
    non_quantum_color = "#fb9a99"
    edge_color = "#333333"

    for row, length in enumerate(lengths):
        widths = split_interval(length, policy)
        y = len(lengths) - row - 1
        cursor = 0.0
        for w in widths:
            if not is_quantum_aligned(w, policy):
                color = non_quantum_color
            elif abs(w - policy.target_atom_size) < 1e-9:
                color = target_color
            else:
                color = deviation_color
            ax.barh(
                y, w, left=cursor, height=0.7,
                color=color, edgecolor=edge_color, linewidth=0.7,
            )
            ax.text(
                cursor + w / 2, y, f"{w:.2f}",
                ha="center", va="center", fontsize=7, color="#222222",
            )
            cursor += w

        ax.text(
            -0.05, y, f"{length:.2f}m",
            ha="right", va="center", fontsize=8, color="#333333",
            transform=ax.get_yaxis_transform(),
        )
        ax.text(
            cursor + 0.10, y, f"n={len(widths)}, sum={sum(widths):.2f}",
            ha="left", va="center", fontsize=7, color="#555555",
        )

    ax.set_xlim(-0.10, max(lengths) * 1.15)
    ax.set_ylim(-0.5, len(lengths) - 0.5)
    ax.set_yticks([])
    ax.set_xlabel("meters")
    ax.tick_params(labelsize=8)
    ax.grid(True, axis="x", color="#dddddd", linewidth=0.5, alpha=0.8)

    legend = (
        f"target = {policy.target_atom_size}m  (teal)   |   "
        f"quantum-deviation (orange)   |   non-quantum (pink)   |   "
        f"quantum = {policy.module_quantum}m"
    )
    ax.set_title(f"Phase 2: split_interval examples\n{legend}", fontsize=9)

    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def _to_shapely(part: ShapePart) -> sg.Polygon:
    return sg.Polygon(part.exterior, [list(h) for h in part.holes])


def _polygon_parts(geom) -> list:
    if geom.is_empty:
        return []
    if isinstance(geom, sg.Polygon):
        return [geom]
    if isinstance(geom, sg.MultiPolygon):
        return list(geom.geoms)
    if hasattr(geom, "geoms"):
        out = []
        for part in geom.geoms:
            out.extend(_polygon_parts(part))
        return out
    return []
