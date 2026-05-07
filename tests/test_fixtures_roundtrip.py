"""Round-trip tests for all 5 fixtures in MATRIX (DoD-6)."""
from __future__ import annotations

import json

import pytest

from proto3.schema.input import BuildingInput
from proto3.schema.serialize import from_json, to_dict

from .fixture_matrix import MATRIX, fixture_path


@pytest.mark.parametrize("matrix_id", sorted(MATRIX.keys()))
def test_fixture_round_trip(matrix_id):
    p = fixture_path(matrix_id)
    raw = json.loads(p.read_text(encoding="utf-8"))
    rebuilt = to_dict(from_json(BuildingInput, p))
    assert raw == rebuilt
