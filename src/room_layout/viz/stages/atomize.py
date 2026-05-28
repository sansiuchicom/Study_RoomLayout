"""``save_atom_figure(floor, atoms, path)`` — render atomize output.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.8 + S03-D4.

Selective port of Cell ``viz.py::save_atom_figure``. Unlike Cell, the
renderer takes the already-computed ``atoms`` as a parameter rather than
running ``atomize`` internally (Plan §6 — decouple viz from algorithm;
the demo CLI / bootstrap orchestrates run → render). The faint territory
backdrop is dropped (atoms are already colored by ``part_id``); the core
diagnostic is colored atoms + footprint outline + sliver markers.
"""

from pathlib import Path

import matplotlib.pyplot as plt

from room_layout.schema import FloorShape
from room_layout.stages.atomize import Atom
from room_layout.viz._helpers import (
    PART_COLORS,
    _draw_footprint_outline,
    _finish_axis,
    configure_fonts,
)


def save_atom_figure(
    floor: FloorShape,
    atoms: tuple[Atom, ...],
    path,
    *,
    title: str | None = None,
) -> Path:
    """Render atoms filled by owning-part color, with sliver markers.

    Sliver atoms (``is_feature_sliver``) get a small red dot at their
    centroid. Footprint outline drawn on top.
    """
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    for atom in atoms:
        color = PART_COLORS[atom.part_id % len(PART_COLORS)]
        xs, ys = zip(*atom.shape.exterior, strict=True)
        ax.fill(
            [*xs, xs[0]],
            [*ys, ys[0]],
            facecolor=color,
            edgecolor="#555555",
            alpha=0.55,
            linewidth=0.35,
            zorder=5,
        )
        if atom.is_feature_sliver:
            cx, cy = atom.centroid
            ax.plot(cx, cy, ".", color="#aa0000", markersize=2.5, zorder=10)

    _draw_footprint_outline(ax, floor)
    _finish_axis(ax, floor)
    n_atoms = len(atoms)
    n_slivers = sum(1 for a in atoms if a.is_feature_sliver)
    ax.set_title(title or f"{n_atoms} atoms ({n_slivers} slivers)", fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path
