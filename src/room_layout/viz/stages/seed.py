"""Seed-placement visualization — ``save_seed_figure``.

Plan reference: ``004_Step04_AlgorithmCore_Plan.md`` §4.12 + S04-D7.

Dev-bridge renderer for the auto seed placement (``auto_place_seeds_by_cells``):
regions as a faint backdrop, each placed seed marked at its region centroid and
colored by the phase that placed it (hub / coverage / fps). Takes the computed
``SeedPlacement`` tuple as a parameter (decoupled from the algorithm per Plan §6).
"""

from pathlib import Path

import matplotlib.pyplot as plt

from room_layout.schema import FloorShape
from room_layout.stages._helpers import to_shapely
from room_layout.stages.regionize import Region
from room_layout.stages.seed_placement import SeedPlacement
from room_layout.viz._helpers import _draw_footprint_outline, _finish_axis, configure_fonts

# Phase → (marker, color, label) for the auto-placement phases.
_PHASE_STYLE = {
    "hub": ("*", "#cc2222", "hub"),
    "coverage": ("o", "#2266cc", "coverage"),
    "fps": ("^", "#22aa44", "fps"),
}


def save_seed_figure(
    floor: FloorShape,
    regions: tuple[Region, ...],
    placements: tuple[SeedPlacement, ...],
    path,
    *,
    title: str | None = None,
) -> Path:
    """Render auto-placed seeds over a faint region backdrop, colored by phase."""
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    # Faint region backdrop.
    for r in regions:
        poly = to_shapely(r.shape)
        xs, ys = poly.exterior.xy
        ax.fill(xs, ys, facecolor="#eeeeee", edgecolor="#bbbbbb", linewidth=0.4, zorder=1)
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.fill(hx, hy, facecolor="#444444", edgecolor="#111111", linewidth=0.7, zorder=2)

    region_poly = {r.region_id: to_shapely(r.shape) for r in regions}
    seen_phases: set[str] = set()
    for order, sp in enumerate(placements):
        marker, color, label = _PHASE_STYLE.get(sp.phase, ("s", "#666666", sp.phase))
        c = region_poly[sp.region.region_id].centroid
        ax.plot(
            c.x,
            c.y,
            marker=marker,
            markersize=14,
            color=color,
            markeredgecolor="#111111",
            markeredgewidth=0.6,
            zorder=10,
            label=label if label not in seen_phases else None,
        )
        seen_phases.add(label)
        ax.text(
            c.x,
            c.y,
            str(order),
            ha="center",
            va="center",
            fontsize=6,
            color="white",
            zorder=11,
        )

    _draw_footprint_outline(ax, floor)
    _finish_axis(ax, floor)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
    ax.set_title(title or f"{len(placements)} seeds (number = placement order)", fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path
