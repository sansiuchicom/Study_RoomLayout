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

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from room_layout.schema import FloorShape  # noqa: E402
from room_layout.stages._helpers import polygon_parts, to_shapely  # noqa: E402

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
