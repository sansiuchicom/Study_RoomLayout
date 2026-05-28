"""Regionize visualization — ``save_region_figure`` + ``save_region_graph_figure``.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.9 / §4.10 + S03-D4.

Selective port of Cell ``viz.py::save_region_figure`` +
``save_region_graph_figure``. Renderers take already-computed outputs as
parameters (decoupled from the algorithm per Plan §6).
``save_region_figure``: regions filled by tab20 on ``region_id`` atop a
faint atom backdrop, ``R#/area`` labels. ``save_region_graph_figure``:
region adjacency overlay — edges as a ``LineCollection`` colored by type
(same-theta grey / exterior blue / hole orange / cross-theta red).
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from room_layout.schema import FloorShape
from room_layout.stages._helpers import to_shapely
from room_layout.stages.atomize import Atom
from room_layout.stages.region_graph import RegionGraph
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


def save_region_graph_figure(
    floor: FloorShape,
    graph: RegionGraph,
    path,
    *,
    title: str | None = None,
) -> Path:
    """Render the region adjacency graph (nodes at region centroids).

    Edges are drawn as a ``LineCollection`` colored by type: same-theta
    grey, exterior-contact blue, hole-contact orange, cross-theta red.
    """
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    cmap = plt.get_cmap("tab20")
    centroids: dict[int, tuple[float, float]] = {}
    for region in graph.regions:
        color = cmap(region.region_id % 20)
        poly = to_shapely(region.shape)
        xs, ys = poly.exterior.xy
        ax.fill(xs, ys, facecolor=color, edgecolor="#222222", alpha=0.38, linewidth=0.9, zorder=2)
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.fill(
                hx, hy, facecolor="#444444", edgecolor="#111111", alpha=1.0, linewidth=0.7, zorder=3
            )
        c = poly.centroid
        centroids[region.region_id] = (float(c.x), float(c.y))
        ax.text(
            c.x,
            c.y,
            f"R{region.region_id}",
            ha="center",
            va="center",
            fontsize=7,
            bbox={
                "boxstyle": "round,pad=0.16",
                "facecolor": "white",
                "edgecolor": "#777777",
                "linewidth": 0.35,
                "alpha": 0.9,
            },
            zorder=10,
        )

    buckets: dict[str, list] = {"same": [], "exterior": [], "hole": [], "cross": []}
    for edge in graph.edges:
        seg = (centroids[edge.region_a], centroids[edge.region_b])
        if edge.hole_contact:
            buckets["hole"].append(seg)
        elif edge.exterior_contact:
            buckets["exterior"].append(seg)
        elif not edge.same_theta_group:
            buckets["cross"].append(seg)
        else:
            buckets["same"].append(seg)

    styles = {
        "same": ("#444444", 0.8, 0.65, 5),
        "exterior": ("#2266cc", 1.0, 0.8, 6),
        "hole": ("#dd8822", 1.0, 0.9, 6),
        "cross": ("#cc2222", 1.2, 0.9, 7),
    }
    for kind, segs in buckets.items():
        if segs:
            color, lw, alpha, z = styles[kind]
            ax.add_collection(
                LineCollection(segs, colors=color, linewidths=lw, alpha=alpha, zorder=z)
            )

    if centroids:
        cxs = [p[0] for p in centroids.values()]
        cys = [p[1] for p in centroids.values()]
        ax.plot(cxs, cys, ".", color="#111111", markersize=2.2, zorder=11)

    _draw_footprint_outline(ax, floor)
    _finish_axis(ax, floor)
    ax.set_title(title or f"{len(graph.regions)} regions, {len(graph.edges)} edges", fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path
