"""Tests for proto3.geometry.decompose (S05-D1, D5) — high-level integration.

**Unit conversion note (R-S05-7)**: proto3 schema uses mm (D006), v3.2 algorithm
uses m. Direct fixture loading without conversion blows the LIR rasterize mask
(8000mm × 6000mm at 0.05m grid → 160000×120000 bool = 19 GB). Stage 00 unit
normalization (mm → m) is Step 07's responsibility (Plan §5 Def-14); for now,
this test file converts fixture coordinates inline before calling auto_partition.

Memory budget: smaller subset (A1 + R2) at converted m-unit; A2 (13×10m) is
also small enough but kept out for parametrize compactness.
"""
from __future__ import annotations

import shapely.geometry as sg
import shapely.ops
import pytest

from proto3.geometry.decompose import auto_partition, to_schema
from proto3.schema.geometry import Decomposition, GeometricPiece
from proto3.schema.input import BuildingInput
from proto3.schema.region_atom import Atom
from proto3.schema.serialize import from_dict, from_json, to_dict

from .fixture_matrix import MATRIX, fixture_path


def _footprint_polygon_m(matrix_id):
    """Load fixture and convert mm → m for v3.2 algorithm consumption.

    proto3 schema stores coordinates in mm (D006); v3.2 algorithm expects m.
    Stage 00 normalization will own this conversion in Step 07; here we do it
    inline so the LIR rasterize mask stays small.
    """
    b = from_json(BuildingInput, fixture_path(matrix_id))
    coords_m = [(x / 1000.0, y / 1000.0) for x, y in b.floors[0].footprint]
    return sg.Polygon(coords_m)


@pytest.mark.parametrize("matrix_id", ["A1", "R2", "D1"])
def test_auto_partition_small_fixtures_zero_gap(matrix_id):
    """A1 (8×6m), R2 (4×4m), D1 (~9.5×8.4m rotated 20°) decompose with effectively zero gap (≤ 0.5%).

    D1 exercises the mm→m conversion path together with v3.2 LIR rotation auto-detection
    (Step 05 §4.7, S04 Def-1 resolved).
    """
    poly = _footprint_polygon_m(matrix_id)
    raw = auto_partition(poly)
    total = sum(c.area for c, _ in raw['cells'])
    gap = (poly.area - total) / poly.area
    assert abs(gap) < 0.005, f"{matrix_id} gap {gap*100:.4f}% exceeds 0.5%"


def test_auto_partition_returns_pieces_and_cells():
    """A1 fixture (m-unit converted) should produce ≥1 piece, ≥1 cell, root main rect."""
    poly = _footprint_polygon_m("A1")
    raw = auto_partition(poly)
    assert len(raw['pieces']) >= 1
    assert len(raw['cells']) >= 1
    assert raw['root_main_rect'] is not None


def test_to_schema_atom_to_piece_mapping_consistent():
    """Each atom's parent_piece_id indexes a valid piece, family_id is consistent."""
    poly = sg.box(0, 0, 5, 5)  # synthetic small m-unit polygon
    schema = to_schema(auto_partition(poly))
    n_pieces = len(schema.pieces)
    for atom in schema.atoms:
        assert atom.parent_piece_id is not None
        assert 0 <= atom.parent_piece_id < n_pieces
        assert atom.family_id == schema.pieces[atom.parent_piece_id].family_id


def test_decomposition_round_trip():
    """Decomposition → to_dict → from_dict round-trip preserves piece + atom data."""
    poly = _footprint_polygon_m("R2")  # 4×4m, smallest
    schema = to_schema(auto_partition(poly))

    d = to_dict(schema)
    schema2 = from_dict(Decomposition, d)

    assert len(schema.pieces) == len(schema2.pieces)
    assert len(schema.atoms) == len(schema2.atoms)
    assert schema.pieces[0].theta == schema2.pieces[0].theta
    assert schema.pieces[0].family_id == schema2.pieces[0].family_id
    assert schema.atoms[0].vertices == schema2.atoms[0].vertices
    assert schema.atoms[0].parent_piece_id == schema2.atoms[0].parent_piece_id
    assert schema.root_main_rect_vertices == schema2.root_main_rect_vertices
