"""``save_input_figure(floor, path)`` — render a floor's ShapePart parts.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.12 + S03-D4.

Selective port of Cell ``viz.py::save_input_figure``. Renders each part
colored with a ``P# / θ`` label + vertex dots, atop the footprint
outline. The input figure is a demo-only render (no golden — the input
IS the fixture); landed with the demo CLI.
"""

from pathlib import Path

import matplotlib.pyplot as plt

from room_layout.schema import FloorShape
from room_layout.viz._helpers import (
    PART_COLORS,
    _draw_footprint_outline,
    _draw_part,
    _draw_vertices,
    _finish_axis,
    configure_fonts,
)


def save_input_figure(
    floor: FloorShape,
    path,
    *,
    title: str | None = None,
    show_vertices: bool = True,
) -> Path:
    """Render a floor's parts colored by index with P#/θ labels."""
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    for idx, part in enumerate(floor.parts):
        color = PART_COLORS[idx % len(PART_COLORS)]
        _draw_part(ax, part, color, idx)
        if show_vertices:
            _draw_vertices(ax, part)

    _draw_footprint_outline(ax, floor)
    _finish_axis(ax, floor)
    ax.set_title(title or f"{len(floor.parts)} parts", fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path
