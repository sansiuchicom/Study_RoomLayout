"""Final layout visualization — ``save_labeled_floor_figure`` (Step 07 §4.8).

Plan reference: ``007_Step07_EntryPoint_Plan.md`` §4.8 + S07-D4 + S01-D10.

Dev-bridge matplotlib renderer for the ``run()`` output (one
``LabeledFloorLayout``): each room filled by its 7-class ``Role`` color
(D004 taxonomy) with an id / usage / role / area label; corridor polygons
hatched; ``vertical_circulation`` (anchor-fixed) rooms drawn with a distinct
hatch + heavy border so the fixed anchor reads apart from grown rooms.

This is the development-bridge path only — the canonical 12-layer SVG renderer
+ ``make_gif()`` are Step 08 (S07-D4). Like the other stage renderers it
imports ``matplotlib`` at module load, so it is behind the optional ``viz``
extra (``import room_layout.viz`` without it still succeeds).
"""

from pathlib import Path

import matplotlib.pyplot as plt

from room_layout.schema import FloorShape, LabeledFloorLayout
from room_layout.viz._helpers import _draw_footprint_outline, _finish_axis, configure_fonts

# 7-class Role → fill color (D004) now lives in the single palette source
# (S08-D6). Re-imported here so existing `from viz.stages.final import
# ROLE_COLORS` callers (+ test_viz_final) keep working unchanged.
from room_layout.viz.palette import ROLE_COLORS, ROLE_FALLBACK_COLOR


def _draw_holes(ax, poly, zorder: int) -> None:
    for ring in poly.interiors:
        hx, hy = ring.xy
        ax.fill(hx, hy, facecolor="#ffffff", edgecolor="#111111", linewidth=0.6, zorder=zorder)


def save_labeled_floor_figure(
    floor: FloorShape,
    layout: LabeledFloorLayout,
    path,
    *,
    title: str | None = None,
) -> Path:
    """Render one labeled floor: rooms by role + corridors + vc anchors."""
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    # Corridors first (under rooms), hatched.
    for poly in layout.corridor_polygons:
        xs, ys = poly.exterior.xy
        ax.fill(
            xs,
            ys,
            facecolor=ROLE_COLORS["corridor"],
            edgecolor="#888888",
            hatch="////",
            alpha=0.7,
            linewidth=0.6,
            zorder=2,
        )

    # Rooms by role; vc rooms get a distinct hatch + heavy border (fixed anchor).
    for room in layout.rooms:
        is_vc = room.role == "vertical_circulation"
        xs, ys = room.polygon.exterior.xy
        ax.fill(
            xs,
            ys,
            facecolor=ROLE_COLORS.get(room.role, ROLE_FALLBACK_COLOR),
            edgecolor="#7a3b3b" if is_vc else "#222222",
            linewidth=2.2 if is_vc else 0.9,
            hatch="xxx" if is_vc else None,
            alpha=0.85,
            zorder=3,
        )
        _draw_holes(ax, room.polygon, zorder=4)

        rp = room.polygon.representative_point()
        label = room.id
        if room.usage:
            label += f"\n{room.usage}"
        label += f"\n[{room.role}] {room.area_m2:.1f}m²"
        ax.text(
            rp.x,
            rp.y,
            label,
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
    n_corr = len(layout.corridor_polygons)
    ax.set_title(
        title or f"floor {layout.level}: {len(layout.rooms)} rooms, {n_corr} corridor poly",
        fontsize=10,
    )
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path
