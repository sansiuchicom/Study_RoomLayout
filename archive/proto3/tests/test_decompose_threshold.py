"""atom_inclusion_threshold wiring test (Step 06 §4.7, S06-D14, 외부 review #3).

Before §4.7 the threshold was hardcoded `0.5` inside
`recursive_progressive_per_family`, making `RunConfig.atom_inclusion_threshold`
a dead config. §4.7 plumbs the parameter through `decompose.run` →
`auto_partition` → `recursive_progressive_per_family` → `merge_below_50_aniso`.

These tests verify the wiring by varying the threshold and checking that the
output cell count changes — different thresholds keep / merge different
boundary cells, so the count must respond.
"""
from __future__ import annotations

import shapely.geometry as sg

from proto3.geometry.decompose import auto_partition, run


def _l_shape_m() -> sg.Polygon:
    """L-shape polygon in m units. Boundary cells will vary with threshold."""
    return sg.Polygon([(0, 0), (9, 0), (9, 5), (5, 5), (5, 8), (0, 8)])


def _l_shape_mm() -> sg.Polygon:
    return sg.Polygon([(0, 0), (9000, 0), (9000, 5000),
                       (5000, 5000), (5000, 8000), (0, 8000)])


def test_auto_partition_threshold_default_matches_explicit_05():
    """Default = 0.5; explicit 0.5 must be identical."""
    poly = _l_shape_m()
    a = auto_partition(poly, target_cell_size=0.4, seed=42)
    b = auto_partition(poly, target_cell_size=0.4, seed=42,
                       atom_inclusion_threshold=0.5)
    assert len(a["cells"]) == len(b["cells"])


def test_auto_partition_lower_threshold_keeps_more_cells():
    """threshold=0.05 keeps almost every boundary fragment;
    threshold=0.95 merges most fragments away. Cell count must differ."""
    poly = _l_shape_m()
    permissive = auto_partition(poly, target_cell_size=0.4, seed=42,
                                atom_inclusion_threshold=0.05)
    strict = auto_partition(poly, target_cell_size=0.4, seed=42,
                            atom_inclusion_threshold=0.95)
    # If the threshold were still hardcoded, both would produce identical counts.
    assert len(permissive["cells"]) != len(strict["cells"])
    # Lower threshold keeps more cells (merges fewer).
    assert len(permissive["cells"]) >= len(strict["cells"])


def test_run_mm_wrapper_threshold_propagates():
    """proto3-friendly mm entry point also forwards atom_inclusion_threshold."""
    poly = _l_shape_mm()
    permissive = run(poly, target_cell_size_mm=400, seed=42,
                     atom_inclusion_threshold=0.05)
    strict = run(poly, target_cell_size_mm=400, seed=42,
                 atom_inclusion_threshold=0.95)
    assert len(permissive["cells"]) != len(strict["cells"])
    assert len(permissive["cells"]) >= len(strict["cells"])
