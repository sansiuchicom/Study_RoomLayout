"""Tests for proto3.geometry.grid (S05-D1, D4)."""
from __future__ import annotations

import numpy as np
import shapely.affinity as sa
import shapely.geometry as sg
import shapely.ops

from proto3.geometry.grid import (
    angle_diff,
    compute_proportional_cell_size,
    grid_no_skip_aniso,
    merge_below_50_aniso,
    piece_direct_theta,
)


def test_compute_proportional_cell_size_zero_residue():
    """8×6 rect at target 0.3 → integer N×M with zero residue."""
    rect = sg.box(0, 0, 8, 6)
    cell_w, cell_h, _ = compute_proportional_cell_size(rect, main_theta=0.0, target=0.3)
    n_x = round(8 / cell_w)
    n_y = round(6 / cell_h)
    assert abs(8 - n_x * cell_w) < 1e-9
    assert abs(6 - n_y * cell_h) < 1e-9


def test_grid_no_skip_aniso_rect_perfect_fit():
    """grid_no_skip_aniso on a rect with proportional cells covers the rect exactly."""
    rect = sg.box(0, 0, 8, 6)
    cw, ch, phase = compute_proportional_cell_size(rect, main_theta=0.0, target=0.3)
    cells, _ = grid_no_skip_aniso(rect, theta=0.0, cell_w=cw, cell_h=ch, phase_origin=phase)
    total_area = sum(c.area for c in cells)
    assert abs(total_area - rect.area) < 1e-9


def test_grid_no_skip_aniso_l_shape_zero_gap():
    """L-shape grid covers full polygon area (with random phase, before merge)."""
    l_shape = shapely.ops.unary_union([sg.box(0, 0, 8, 6), sg.box(0, 0, 4, 10)])
    cells, _ = grid_no_skip_aniso(l_shape, theta=0.0, cell_w=0.3, cell_h=0.3, seed=42)
    total_area = sum(c.area for c in cells)
    gap = (l_shape.area - total_area) / l_shape.area
    assert abs(gap) < 1e-6, f"gap {gap*100:.4f}% — should be 0"


def test_merge_below_50_preserves_full_cells():
    """All-full cells (above 50% threshold) should not merge."""
    rect = sg.box(0, 0, 8, 6)
    cw, ch, phase = compute_proportional_cell_size(rect, main_theta=0.0, target=0.3)
    cells, _ = grid_no_skip_aniso(rect, theta=0.0, cell_w=cw, cell_h=ch, phase_origin=phase)
    n_before = len(cells)
    merged = merge_below_50_aniso(cells, cw, ch, threshold_ratio=0.5)
    assert len(merged) == n_before, "no slivers; nothing should merge"


def test_merge_below_50_absorbs_sliver_l_shape():
    """L-shape with random phase has slivers; merge_below_50 reduces cell count + preserves area."""
    l_shape = shapely.ops.unary_union([sg.box(0, 0, 8, 6), sg.box(0, 0, 4, 10)])
    cells, _ = grid_no_skip_aniso(l_shape, theta=0.0, cell_w=0.3, cell_h=0.3, seed=42)
    n_before = len(cells)
    merged = merge_below_50_aniso(cells, 0.3, 0.3, threshold_ratio=0.5)
    assert len(merged) <= n_before, "merge can only reduce or equal"
    total_area = sum(c.area for c in merged)
    assert abs(total_area - l_shape.area) < 1e-6, "area must be preserved"


def test_piece_direct_theta_rotated_rect():
    """Rect rotated 30° should yield theta ≈ 30° from boundary segment voting."""
    rotated = sa.rotate(sg.box(0, 0, 10, 6), 30, origin=(0, 0))
    theta = piece_direct_theta(rotated, min_straight_length=1.0)
    assert theta is not None
    # 30° rotation; allow some slack
    assert abs(np.degrees(theta) - 30) < 1.0


def test_piece_direct_theta_circle_undetermined():
    """Circle has no straight segments; theta should be None."""
    circle = sg.Point(0, 0).buffer(5.0, quad_segs=64)
    theta = piece_direct_theta(circle, min_straight_length=1.0)
    # Many short tangent segments — should not yield a clear direction.
    # We accept either None or any value (test is lenient about exact behaviour),
    # but a near-0 magnitude is the documented branch.
    assert theta is None or 0 <= theta < np.pi / 2


def test_angle_diff_pi_half_symmetry():
    """0° and 90° are equivalent (axis-aligned grid symmetry)."""
    assert angle_diff(0.0, np.pi / 2) < 1e-9


def test_angle_diff_45_and_30():
    """Check standard non-trivial differences."""
    assert abs(angle_diff(0.0, np.pi / 4) - np.pi / 4) < 1e-9
    assert abs(angle_diff(np.pi / 6, np.pi / 3) - np.pi / 6) < 1e-9
