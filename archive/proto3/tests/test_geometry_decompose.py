"""Tests for proto3.geometry.decompose (S05-D1, D5) — high-level integration.

Uses `proto3.geometry.decompose.run()` (mm-friendly proto3 entry; R-S05-7
mitigation) for fixture-based tests. Synthetic m-unit polygons still call
`auto_partition()` directly to exercise the v3.2 origin path.

Memory budget: smaller subset (A1 + R2 + D1). A2 (13×10m) is excluded for
parametrize compactness; broader fixture coverage lives in the §4.8 notebook
and the v3.2 stress-test artifacts in `references/`.
"""
from __future__ import annotations

import shapely.geometry as sg
import shapely.ops
import pytest

from proto3.geometry.decompose import auto_partition, run, to_schema
from proto3.schema.geometry import Decomposition, GeometricPiece
from proto3.schema.input import BuildingInput
from proto3.schema.region_atom import Atom
from proto3.schema.serialize import from_dict, from_json, to_dict

from .fixture_matrix import MATRIX, fixture_path


def _footprint_polygon_mm(matrix_id):
    """Load fixture and return its first floor's footprint as a shapely Polygon (mm)."""
    b = from_json(BuildingInput, fixture_path(matrix_id))
    return sg.Polygon(b.floors[0].footprint)


@pytest.mark.parametrize("matrix_id", ["A1", "R2", "D1"])
def test_run_small_fixtures_zero_gap(matrix_id):
    """A1 (8×6m), R2 (4×4m), D1 (~9.5×8.4m rotated 20°) decompose with effectively zero gap.

    D1 exercises the v3.2 LIR rotation auto-detection through the proto3
    mm-friendly `run()` wrapper (Step 05 §4.7, S04 Def-1 resolved).
    """
    poly_mm = _footprint_polygon_mm(matrix_id)
    raw = run(poly_mm)
    total = sum(c.area for c, _ in raw['cells'])
    gap = (poly_mm.area - total) / poly_mm.area
    assert abs(gap) < 0.005, f"{matrix_id} gap {gap*100:.4f}% exceeds 0.5%"


def test_run_returns_pieces_and_cells():
    """A1 fixture (mm) should produce ≥1 piece, ≥1 cell, root main rect."""
    poly_mm = _footprint_polygon_mm("A1")
    raw = run(poly_mm)
    assert len(raw['pieces']) >= 1
    assert len(raw['cells']) >= 1
    assert raw['root_main_rect'] is not None


def test_run_output_in_mm():
    """`run()` should return cells/pieces in mm (proto3 schema convention)."""
    poly_mm = _footprint_polygon_mm("A1")
    raw = run(poly_mm)
    sample_cell = raw['cells'][0][0]
    minx, miny, maxx, maxy = sample_cell.bounds
    # A 300mm-target cell should be on the order of hundreds of mm, not <1
    assert (maxx - minx) > 50, f"cell width {maxx-minx} too small — output may still be in m"
    assert (maxy - miny) > 50


def test_to_schema_atom_to_piece_mapping_consistent():
    """Each atom's parent_piece_id indexes a valid piece, family_id is consistent."""
    poly = sg.box(0, 0, 5, 5)  # synthetic small m-unit polygon for the auto_partition path
    schema = to_schema(auto_partition(poly))
    n_pieces = len(schema.pieces)
    for atom in schema.atoms:
        assert atom.parent_piece_id is not None
        assert 0 <= atom.parent_piece_id < n_pieces
        assert atom.family_id == schema.pieces[atom.parent_piece_id].family_id


def test_decomposition_round_trip():
    """Decomposition → to_dict → from_dict round-trip preserves piece + atom data.

    Uses the mm-unit `run()` wrapper on R2 (4×4m), since that is the proto3 default path.
    """
    poly_mm = _footprint_polygon_mm("R2")
    schema = to_schema(run(poly_mm))

    d = to_dict(schema)
    schema2 = from_dict(Decomposition, d)

    assert len(schema.pieces) == len(schema2.pieces)
    assert len(schema.atoms) == len(schema2.atoms)
    assert schema.pieces[0].theta == schema2.pieces[0].theta
    assert schema.pieces[0].family_id == schema2.pieces[0].family_id
    assert schema.atoms[0].vertices == schema2.atoms[0].vertices
    assert schema.atoms[0].parent_piece_id == schema2.atoms[0].parent_piece_id
    assert schema.root_main_rect_vertices == schema2.root_main_rect_vertices
