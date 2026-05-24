"""Visualization helpers for the atomic zoning testfield."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager

from .geometry import iter_linework, polygon_parts


ZONE_COLORS = [
    "#9ad0c2",
    "#fdb462",
    "#a6cee3",
    "#fb9a99",
    "#b2df8a",
    "#cab2d6",
    "#fdd087",
    "#b3cde3",
    "#ccebc5",
    "#decbe4",
    "#fed9a6",
    "#ffffcc",
]

FACE_COLOR = "#d9e8f5"
CUT_COLOR = "#c0392b"
BOUNDARY_COLOR = "#111111"
HOLE_COLOR = "#404040"


def configure_fonts():
    """Use a local Korean-capable font when available."""
    font_path = Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
    if font_path.exists():
        font_manager.fontManager.addfont(font_path)
        plt.rcParams["font.family"] = "NanumGothic"
    plt.rcParams["axes.unicode_minus"] = False


def save_zoning_figure(result, footprint, path, *, title: str | None = None):
    """Save a three-panel diagnostic figure for a zoning result."""
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    _plot_faces(axes[0], footprint, result)
    _plot_cuts(axes[1], footprint, result)
    _plot_zones(axes[2], footprint, result)

    if title:
        fig.suptitle(title, fontsize=11, fontweight="bold")

    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_faces(ax, footprint, result):
    for face in result.subdivision.faces:
        _fill_geom(ax, face.polygon, FACE_COLOR, "#6688aa", alpha=0.65, linewidth=0.5)
        x, y = face.centroid
        ax.text(x, y, f"F{face.face_id}", ha="center", va="center", fontsize=6)
    _draw_footprint(ax, footprint)
    ax.set_title(f"Atomic Faces ({len(result.subdivision.faces)})", fontsize=9)
    _finish_axis(ax, footprint)


def _plot_cuts(ax, footprint, result):
    _fill_geom(ax, footprint, "#f6f6f6", "#999999", alpha=0.8, linewidth=0.5)
    for cut in result.planning.cuts:
        clipped = cut.line.intersection(footprint)
        for line in iter_linework([clipped]):
            _plot_line(ax, line, CUT_COLOR, linewidth=1.4, linestyle="--", alpha=0.85)
    _draw_footprint(ax, footprint)
    ax.set_title(f"Planned Cuts ({len(result.planning.cuts)})", fontsize=9)
    _finish_axis(ax, footprint)


def _plot_zones(ax, footprint, result):
    for zone in result.zones:
        color = ZONE_COLORS[zone.zone_id % len(ZONE_COLORS)]
        _fill_geom(ax, zone.polygon, color, "#222222", alpha=0.78, linewidth=0.8)
        cx, cy = zone.polygon.representative_point().coords[0]
        ax.text(
            cx,
            cy,
            f"Z{zone.zone_id}\n{zone.polygon.area:.1f}",
            ha="center",
            va="center",
            fontsize=6,
            bbox={
                "boxstyle": "round,pad=0.15",
                "facecolor": "white",
                "edgecolor": "#777777",
                "linewidth": 0.4,
                "alpha": 0.85,
            },
        )
    _draw_footprint(ax, footprint)
    status = result.validation.short_status()
    ax.set_title(
        f"Zones ({len(result.zones)}/{result.planning.requested_k}) - {status}",
        fontsize=9,
    )
    _finish_axis(ax, footprint)


def _fill_geom(ax, geom, facecolor, edgecolor, *, alpha=1.0, linewidth=0.8):
    for poly in polygon_parts(geom):
        x, y = poly.exterior.xy
        ax.fill(
            x,
            y,
            facecolor=facecolor,
            edgecolor=edgecolor,
            alpha=alpha,
            linewidth=linewidth,
        )
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.fill(hx, hy, facecolor=HOLE_COLOR, edgecolor=BOUNDARY_COLOR, alpha=1.0)


def _draw_footprint(ax, footprint):
    for poly in polygon_parts(footprint):
        x, y = poly.exterior.xy
        ax.plot(x, y, color=BOUNDARY_COLOR, linewidth=1.5, zorder=20)
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.fill(hx, hy, facecolor=HOLE_COLOR, edgecolor=BOUNDARY_COLOR, zorder=19)


def _plot_line(ax, line, color, *, linewidth=1.0, linestyle="-", alpha=1.0):
    if line.geom_type in ("LineString", "LinearRing"):
        x, y = line.xy
        ax.plot(x, y, color=color, linewidth=linewidth, linestyle=linestyle, alpha=alpha)
    elif line.geom_type == "MultiLineString":
        for part in line.geoms:
            _plot_line(ax, part, color, linewidth=linewidth, linestyle=linestyle, alpha=alpha)


def _finish_axis(ax, footprint):
    minx, miny, maxx, maxy = footprint.bounds
    pad = max(maxx - minx, maxy - miny, 1.0) * 0.06
    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)
    ax.set_aspect("equal")
    ax.grid(True, color="#dddddd", linewidth=0.5, alpha=0.8)
    ax.tick_params(labelsize=7)
