"""Palette completeness (Step 08 §4.7 / S08-D6).

The single visual-vocabulary source: 12-layer stack, 7-role color coverage,
tolerant ``role_color``. Pure constants — no matplotlib needed.
"""

from __future__ import annotations

from typing import get_args

from room_layout.schema.program import Role
from room_layout.viz import palette


def test_layer_order_is_twelve_unique():
    assert len(palette.LAYER_ORDER) == 12
    assert len(set(palette.LAYER_ORDER)) == 12, "layer names must be unique"
    # first/last are the documented z-extremes (backdrop / overlay)
    assert palette.LAYER_ORDER[0] == "grid"
    assert palette.LAYER_ORDER[-1] == "failure"


def test_role_colors_cover_all_seven_roles():
    assert set(get_args(Role)) <= set(palette.ROLE_COLORS)


def test_role_color_is_tolerant():
    assert palette.role_color("public") == palette.ROLE_COLORS["public"]
    assert palette.role_color("not_a_role") == palette.ROLE_FALLBACK_COLOR


def test_lit_layers_have_a_color():
    # the structural/debug layers the renderer fills with a single color
    for name in ("grid", "footprint", "anchors", "corridor", "failure"):
        assert name in palette.LAYER_COLORS, name
