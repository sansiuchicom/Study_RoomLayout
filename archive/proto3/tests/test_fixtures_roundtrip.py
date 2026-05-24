"""Round-trip tests for all fixtures in MATRIX (DoD-6 + Step 05 D1 extension).

Step 06 §4.2 update: comparison switched from raw-dict equality to object
equality (deserialize → serialize → deserialize → equal). Raw-dict equality
broke once `program_request` became a typed dataclass: `to_dict` emits
default-valued fields (e.g., SpaceUnitSpec.required, min_area_m2=None) that
the raw fixture doesn't list. Object equality is the cleaner invariant —
"the schema can losslessly represent the fixture content".
"""
from __future__ import annotations

import pytest

from proto3.schema.input import BuildingInput
from proto3.schema.serialize import from_dict, from_json, to_dict

from .fixture_matrix import MATRIX, fixture_path


@pytest.mark.parametrize("matrix_id", sorted(MATRIX.keys()))
def test_fixture_round_trip(matrix_id):
    p = fixture_path(matrix_id)
    obj1 = from_json(BuildingInput, p)
    obj2 = from_dict(BuildingInput, to_dict(obj1))
    assert obj1 == obj2
