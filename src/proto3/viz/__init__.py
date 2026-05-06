"""Visualization (Step 03 — D013).

SVG-first renderer with stable 12-layer order and a coded visual vocabulary.
"""
from __future__ import annotations

from proto3.viz.palette import (
    GRID_SPACING_MM,
    LABEL_FONT_FAMILY,
    LABEL_FONT_SIZE_RATIO,
    LAYER_COLORS,
    LAYER_ORDER,
    role_to_palette_key,
)

__all__ = [
    "GRID_SPACING_MM",
    "LABEL_FONT_FAMILY",
    "LABEL_FONT_SIZE_RATIO",
    "LAYER_COLORS",
    "LAYER_ORDER",
    "role_to_palette_key",
]
