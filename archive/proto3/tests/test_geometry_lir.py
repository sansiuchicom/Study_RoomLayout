"""Tests for proto3.geometry.lir (S05-D1)."""
from __future__ import annotations

import numpy as np
import shapely.geometry as sg
import shapely.ops

from proto3.geometry.lir import (
    candidate_angles_from_boundary,
    find_main_rect_refined,
    lir_at_angle,
    max_rect_in_histogram,
    max_rect_in_mask,
    rasterize_polygon,
)


def test_rasterize_polygon_rect_count():
    """8×6 rect rasterized at resolution 0.5 should have ~192 interior cells (16×12)."""
    rect = sg.box(0, 0, 8, 6)
    mask, (minx, miny, res) = rasterize_polygon(rect, resolution=0.5)
    assert minx == 0.0
    assert miny == 0.0
    assert res == 0.5
    assert mask.shape == (13, 17)  # ny=ceil(6/0.5)+1, nx=ceil(8/0.5)+1
    # Cells whose centers are inside the rect
    assert mask.sum() == 16 * 12  # 16 columns × 12 rows of centers within [0,8]×[0,6]


def test_max_rect_in_histogram_known():
    """Stack-based histogram max rect on a known case."""
    # Heights [2, 1, 4, 5, 1, 3, 3] → maximal rect at indices 5..6, height 3, width 2 → area 6.
    # But indices 2..3 have heights [4, 5] → maximal rect at index 3, height 4, width 2 → area 8.
    left, h, w = max_rect_in_histogram([2, 1, 4, 5, 1, 3, 3])
    assert h * w == 8


def test_max_rect_in_mask_full_rect():
    """All-True mask returns full-extent rectangle."""
    mask = np.ones((10, 8), dtype=bool)
    result = max_rect_in_mask(mask)
    assert result == (0, 0, 8, 10)  # i0, j0, w, h


def test_lir_at_angle_axis_aligned_rect_recovers_full_area():
    """LIR of an 8×6 rect at theta=0 should recover (effectively) the full rect."""
    rect = sg.box(0, 0, 8, 6)
    lir = lir_at_angle(rect, theta=0.0, resolution=0.1)
    assert lir is not None
    assert abs(lir.area - rect.area) / rect.area < 0.05  # within 5% (rasterization slack)


def test_candidate_angles_axis_aligned_rect_only_zero():
    """Axis-aligned rect's exterior is all 0° / 90° edges (mod π/2 = 0°)."""
    rect = sg.box(0, 0, 8, 6)
    angles = candidate_angles_from_boundary(rect)
    assert any(abs(a) < np.radians(2) for a in angles), \
        f"expected axis-aligned candidate; got {[np.degrees(a) for a in angles]}"


def test_find_main_rect_refined_l_shape():
    """L-shape's main inscribed rect should be the larger leg."""
    l_shape = shapely.ops.unary_union([sg.box(0, 0, 8, 6), sg.box(0, 0, 4, 10)])
    rect, theta, info = find_main_rect_refined(l_shape, resolution=0.2)
    assert rect is not None
    # Main leg is 8×6=48. The other leg is 4×10=40. LIR must pick the larger.
    assert rect.area >= 47.0  # rasterization slack


def test_find_main_rect_refined_rotated_rect_recovers_theta():
    """Rotated rectangle's LIR theta should match the rotation."""
    import shapely.affinity as sa
    rotated = sa.rotate(sg.box(0, 0, 10, 6), 30, origin=(0, 0))
    rect, theta, info = find_main_rect_refined(rotated, resolution=0.1)
    assert rect is not None
    # theta is in [0, π/2); 30° → 0.524 rad
    assert abs(np.degrees(theta) - 30) < 1.5, f"got {np.degrees(theta):.2f}°"
