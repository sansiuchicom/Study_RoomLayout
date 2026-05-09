"""Tests for proto3.geometry.recursive (S05-D1, D4) — per-family decomposition."""
from __future__ import annotations

import numpy as np
import shapely.affinity as sa
import shapely.geometry as sg
import shapely.ops

from proto3.geometry.recursive import recursive_progressive_per_family


def _families(pieces):
    return {p['family_id'] for p in pieces}


def test_simple_rect_one_family():
    """Axis-aligned rect → single family, all cells inside it."""
    rect = sg.box(0, 0, 8, 6)
    cells, pieces, root_main, _ = recursive_progressive_per_family(rect)
    assert len(_families(pieces)) == 1
    total = sum(c.area for c, _ in cells)
    assert abs(total - rect.area) < 1e-6


def test_l_shape_one_family_zero_gap():
    """L-shape: same theta everywhere → 1 family, 0% gap."""
    l_shape = shapely.ops.unary_union([sg.box(0, 0, 8, 6), sg.box(0, 0, 4, 10)])
    cells, pieces, root_main, _ = recursive_progressive_per_family(l_shape)
    assert len(_families(pieces)) == 1, "axis-aligned L must be a single family"
    total = sum(c.area for c, _ in cells)
    assert abs(total - l_shape.area) / l_shape.area < 1e-3


def test_rotated_rect_theta_detected():
    """30° rotated rect: family should adopt theta ≈ 30°."""
    rotated = sa.rotate(sg.box(0, 0, 10, 6), 30, origin=(0, 0))
    _, pieces, _, _ = recursive_progressive_per_family(rotated)
    assert len(_families(pieces)) == 1
    theta = pieces[0]['theta']
    assert abs(np.degrees(theta) - 30) < 1.5


def test_mirror_wings_multiple_families():
    """Main + ±30° wings: should yield multiple families."""
    main = sg.box(0, 0, 12, 8)
    wing_r = sa.translate(sa.rotate(sg.box(0, 0, 5, 3), 30, origin=(0, 0)), xoff=11, yoff=7)
    wing_l = sa.translate(sa.rotate(sg.box(0, 0, 5, 3), -30, origin=(5, 0)), xoff=-3, yoff=7)
    multi = shapely.ops.unary_union([main, wing_r, wing_l])

    cells, pieces, _, _ = recursive_progressive_per_family(multi)
    assert len(_families(pieces)) >= 3, \
        f"multi-axis footprint should split into ≥3 families; got {len(_families(pieces))}"
    total = sum(c.area for c, _ in cells)
    assert abs(total - multi.area) / multi.area < 1e-3
