"""Shared draw helpers for the dev-bridge matplotlib renderers.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §3 + S03-D4.

Visual vocabulary ported selectively from Cell ``viz.py`` (color
palette, footprint outline, axis framing) and written against the new
``room_layout.schema.FloorShape`` / ``ShapePart``. Imports matplotlib at
module load — only pulled in when a renderer is actually used (the
``viz`` extra), never by ``import room_layout`` or the golden tests.

Grows incrementally: 4.8 lands what ``save_atom_figure`` needs
(``PART_COLORS`` / ``configure_fonts`` / ``_draw_footprint_outline`` /
``_finish_axis``). ``_draw_part`` for the input renderer lands with the
demo CLI (4.12).
"""

from math import degrees
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from room_layout.schema import FloorShape, ShapePart  # noqa: E402
from room_layout.stages._helpers import part_theta, polygon_parts, to_shapely  # noqa: E402

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

_NANUM = Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")


def configure_fonts() -> None:
    """Register NanumGothic for Korean case names if present (else default).

    Graceful: when the font is absent, matplotlib falls back to its
    default family (Korean renders as tofu boxes but no crash) — the
    figures stay usable for shape inspection.
    """
    if _NANUM.exists():
        font_manager.fontManager.addfont(str(_NANUM))
        plt.rcParams["font.family"] = "NanumGothic"
    plt.rcParams["axes.unicode_minus"] = False


def _floor_footprint(floor: FloorShape):
    """Union of a floor's parts as a shapely geometry."""
    return unary_union([to_shapely(p) for p in floor.parts])


def _draw_footprint_outline(ax, floor: FloorShape) -> None:
    for poly in polygon_parts(_floor_footprint(floor)):
        x, y = poly.exterior.xy
        ax.plot(x, y, color="#111111", linewidth=1.5, zorder=20)
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.plot(hx, hy, color="#111111", linewidth=1.2, zorder=20)


def _finish_axis(ax, floor: FloorShape) -> None:
    minx, miny, maxx, maxy = _floor_footprint(floor).bounds
    pad = max(maxx - minx, maxy - miny, 1.0) * 0.08
    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)
    ax.set_aspect("equal")
    ax.grid(True, color="#dddddd", linewidth=0.5, alpha=0.8)
    ax.tick_params(labelsize=7)


def _draw_part(ax, part: ShapePart, color: str, idx: int) -> None:
    """Fill a single ``ShapePart`` (exterior + holes) with a P# / θ label."""
    xs, ys = zip(*part.exterior, strict=True)
    ax.fill(
        [*xs, xs[0]], [*ys, ys[0]], facecolor=color, edgecolor="#333333", alpha=0.55, linewidth=1.0
    )
    for hole in part.holes:
        hx, hy = zip(*hole, strict=True)
        ax.fill(
            [*hx, hx[0]],
            [*hy, hy[0]],
            facecolor="#444444",
            edgecolor="#111111",
            alpha=1.0,
            linewidth=0.8,
        )
    poly = to_shapely(part)
    if not poly.is_empty:
        rp = poly.representative_point()
        ax.text(
            rp.x,
            rp.y,
            f"P{idx}\n{degrees(part_theta(part)):.1f}°",
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


def _draw_vertices(ax, part: ShapePart) -> None:
    for x, y in part.exterior:
        ax.plot(x, y, "o", markersize=3, color="#222222", zorder=10)
