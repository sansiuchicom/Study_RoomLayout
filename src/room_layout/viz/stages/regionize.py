"""Regionize visualization — ``save_region_figure``.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.9 + S03-D4.

Selective port of Cell ``viz.py::save_region_figure``. Renderer takes
the already-computed ``atoms`` + ``regions`` as parameters (decoupled
from the algorithm per Plan §6). Regions are filled by a tab20 color
keyed on ``region_id``, atop a faint atom backdrop, with ``R# / area``
labels. ``save_region_graph_figure`` (region adjacency overlay) lands
in 4.10.
"""

from pathlib import Path

import matplotlib.pyplot as plt

from room_layout.schema import FloorShape
from room_layout.stages._helpers import to_shapely
from room_layout.stages.atomize import Atom
from room_layout.stages.regionize import Region
from room_layout.viz._helpers import (
    _draw_footprint_outline,
    _finish_axis,
    configure_fonts,
)


def save_region_figure(
    floor: FloorShape,
    atoms: tuple[Atom, ...],
    regions: tuple[Region, ...],
    path,
    *,
    title: str | None = None,
    show_atoms: bool = True,
) -> Path:
    """Render regions as colored areas atop a faint atom grid."""
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    if show_atoms:
        for atom in atoms:
            xs, ys = zip(*atom.shape.exterior, strict=True)
            ax.fill(
                [*xs, xs[0]],
                [*ys, ys[0]],
                facecolor="#eeeeee",
                edgecolor="#bbbbbb",
                alpha=0.6,
                linewidth=0.25,
                zorder=1,
            )

    cmap = plt.get_cmap("tab20")
    for r in regions:
        color = cmap(r.region_id % 20)
        poly = to_shapely(r.shape)
        xs, ys = poly.exterior.xy
        ax.fill(xs, ys, facecolor=color, edgecolor="#222222", alpha=0.55, linewidth=1.1, zorder=4)
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.fill(
                hx, hy, facecolor="#444444", edgecolor="#111111", alpha=1.0, linewidth=0.7, zorder=5
            )
        rp = poly.representative_point()
        ax.text(
            rp.x,
            rp.y,
            f"R{r.region_id}\n{poly.area:.1f}m²",
            ha="center",
            va="center",
            fontsize=7,
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": "white",
                "edgecolor": "#777777",
                "linewidth": 0.4,
                "alpha": 0.9,
            },
            zorder=10,
        )

    _draw_footprint_outline(ax, floor)
    _finish_axis(ax, floor)
    n_regions = len(regions)
    avg_area = sum(to_shapely(r.shape).area for r in regions) / max(n_regions, 1)
    ax.set_title(title or f"{n_regions} regions (avg {avg_area:.1f}m²)", fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path
