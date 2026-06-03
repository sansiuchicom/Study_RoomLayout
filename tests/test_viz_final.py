"""Final-layout renderer smoke test (Step 07 §4.8).

The dev-bridge renderer imports matplotlib at module load, so it is behind the
optional ``viz`` extra — skip cleanly when matplotlib is absent (CI runs the
data goldens without it). The assertion is a smoke check (PNG written,
non-empty); matplotlib output is not golden-compared (font/version drift) —
the repo regresses on data digests, not pixels.
"""

from __future__ import annotations

from typing import get_args

import pytest
from shapely.geometry import Polygon

from room_layout.schema import FloorShape, LabeledFloorLayout, LabeledRoom, Role, ShapePart

pytest.importorskip("matplotlib")  # the renderer imports matplotlib at module load

from room_layout.viz.stages.final import ROLE_COLORS, save_labeled_floor_figure  # noqa: E402


def _floor() -> FloorShape:
    return FloorShape(
        level=0,
        parts=[ShapePart(exterior=((0, 0), (6, 0), (6, 5), (0, 5)))],
        floor_to_floor_height=None,
    )


def test_save_labeled_floor_figure_writes_png(tmp_path):
    # a public room, a fixed vc anchor room, and a corridor — all 3 visual paths
    layout = LabeledFloorLayout(
        level=0,
        rooms=[
            LabeledRoom(
                id="liv",
                polygon=Polygon([(0, 0), (4, 0), (4, 5), (0, 5)]),
                role="public",
                usage="living",
                area_m2=20.0,
            ),
            LabeledRoom(
                id="vc1",
                polygon=Polygon([(4, 0), (6, 0), (6, 2), (4, 2)]),
                role="vertical_circulation",
                usage="stair",
                area_m2=4.0,
                anchor_id="a",
            ),
        ],
        corridor_polygons=[Polygon([(4, 2), (6, 2), (6, 5), (4, 5)])],
    )
    out = save_labeled_floor_figure(_floor(), layout, tmp_path / "final.png")
    assert out.exists()
    assert out.stat().st_size > 0


def test_role_colors_cover_all_seven_roles():
    assert set(get_args(Role)) <= set(ROLE_COLORS)
