"""Layout (partition growth) visualization — ``save_layout_figure``.

Plan reference: ``004_Step04_AlgorithmCore_Plan.md`` §4.11 + S04-D4.

Dev-bridge renderer for ``region_partition_growth`` output (``GrowthResult``):
regions colored by their assigned room, unassigned regions (Phase 8 corridor
candidates) hatched grey, each room's seed region (``region_ids[0]``) marked,
room label at the room's union centroid. Takes already-computed outputs as
parameters (decoupled from the algorithm per Plan §6).

The phase-colored *seed* renderer (hub / coverage / fps) is an auto-placement
artifact — it lands in 4.12 with the auto seed golden.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from shapely.ops import unary_union

from room_layout.schema import FloorShape
from room_layout.stages._helpers import to_shapely
from room_layout.stages.regionize import Region
from room_layout.stages.room_growth import GrowthResult
from room_layout.viz._helpers import _draw_footprint_outline, _finish_axis, configure_fonts


def save_layout_figure(
    floor: FloorShape,
    regions: tuple[Region, ...],
    result: GrowthResult,
    path,
    *,
    title: str | None = None,
) -> Path:
    """Render grown rooms: regions colored by room, seeds marked, leftovers grey."""
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    region_poly = {r.region_id: to_shapely(r.shape) for r in regions}
    room_of: dict[int, int] = {}
    seed_of: dict[int, int] = {}  # room_idx → seed region_id
    for room_idx, gr in enumerate(result.rooms):
        for rid in gr.region_ids:
            room_of[rid] = room_idx
        if gr.region_ids:
            seed_of[room_idx] = gr.region_ids[0]

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)
    cmap = plt.get_cmap("tab20")

    # Regions colored by room; unassigned hatched grey.
    for rid, poly in region_poly.items():
        xs, ys = poly.exterior.xy
        if rid in room_of:
            color = cmap(room_of[rid] % 20)
            ax.fill(
                xs, ys, facecolor=color, edgecolor="#222222", alpha=0.6, linewidth=0.8, zorder=3
            )
        else:
            ax.fill(
                xs,
                ys,
                facecolor="#dddddd",
                edgecolor="#999999",
                alpha=0.7,
                linewidth=0.6,
                hatch="////",
                zorder=2,
            )
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.fill(hx, hy, facecolor="#444444", edgecolor="#111111", linewidth=0.7, zorder=5)

    # Seed markers + room labels (at the room's union centroid).
    for room_idx, gr in enumerate(result.rooms):
        if not gr.region_ids:
            continue
        sc = region_poly[seed_of[room_idx]].centroid
        ax.plot(sc.x, sc.y, marker="*", markersize=13, color="#111111", zorder=12)
        union = unary_union([region_poly[rid] for rid in gr.region_ids])
        rp = union.representative_point()
        ax.text(
            rp.x,
            rp.y,
            f"{gr.name}\n{gr.role}\n{gr.area_m2:.1f}m²",
            ha="center",
            va="center",
            fontsize=7,
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": "white",
                "edgecolor": "#555555",
                "linewidth": 0.5,
                "alpha": 0.92,
            },
            zorder=11,
        )

    _draw_footprint_outline(ax, floor)
    _finish_axis(ax, floor)
    n_un = len(result.unassigned_region_ids)
    ax.set_title(title or f"{len(result.rooms)} rooms, {n_un} leftover region(s)", fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path
