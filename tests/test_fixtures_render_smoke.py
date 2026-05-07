"""Render smoke tests for all 5 fixtures (review followup #4).

Extends DoD-6 (round-trip only) with geometry sanity + render-time XML
validation across the full MATRIX, not just apartment_minimal.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from proto3.schema.input import BuildingInput
from proto3.schema.serialize import from_json
from proto3.viz import LAYER_ORDER, render

from .fixture_matrix import MATRIX, fixture_path

SVG_NS = "{http://www.w3.org/2000/svg}"


def _polygon_area(pts) -> float:
    n = len(pts)
    return abs(
        sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    ) / 2


@pytest.mark.parametrize("matrix_id", sorted(MATRIX.keys()))
def test_fixture_geometry_sanity(matrix_id):
    building = from_json(BuildingInput, fixture_path(matrix_id))
    assert len(building.floors) == 1
    floor = building.floors[0]
    assert len(floor.footprint) >= 4, f"{matrix_id}: footprint must have ≥4 vertices"
    assert floor.floor_root is not None, f"{matrix_id}: floor_root must be set"
    assert _polygon_area(floor.footprint) > 0, f"{matrix_id}: footprint area must be positive"


@pytest.mark.parametrize("matrix_id", sorted(MATRIX.keys()))
def test_fixture_render_smoke(matrix_id, tmp_path):
    building = from_json(BuildingInput, fixture_path(matrix_id))
    out = tmp_path / f"{matrix_id}.svg"
    render(building, out_path=str(out))

    assert out.exists() and out.stat().st_size > 0

    root = ET.parse(str(out)).getroot()
    assert root.tag == f"{SVG_NS}svg"

    layer_groups = root.findall(f"{SVG_NS}g")
    assert len(layer_groups) == 12
    for i, (g, expected_name) in enumerate(zip(layer_groups, LAYER_ORDER)):
        cls = g.attrib.get("class", "")
        assert cls == f"layer-{i:02d}-{expected_name}", f"{matrix_id} layer {i}: got {cls!r}"

    footprint_polys = layer_groups[0].findall(f"{SVG_NS}polygon")
    assert len(footprint_polys) >= 1, f"{matrix_id}: missing footprint polygon"
