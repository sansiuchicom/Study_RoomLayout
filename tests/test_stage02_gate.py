"""Stage 02 integration tests + R2 regression circuit (Step 06 §4.6).

Stage 02 = fail-only domain feasibility gate (D020). This test suite wires
fixture matrix (Stage 00 → Stage 01 → Stage 02) end-to-end:

- A1 / A2 / B1 / D1 fixtures must pass Stage 02 (false-reject regression).
- R2 fixture must raise AreaGateFailure — the gate's first live trigger
  (Plan §4.6, S06-D6, S06-D24). Plan v2 had R2 metadata
  `expected_failure: AreaGateFailure / verified_at: Step 06`; this test
  verifies it.
- R1 is upstream (Stage 01 cardinality fail) and never reaches Stage 02;
  not parametrized here.
"""
from __future__ import annotations

import pytest

from proto3.schema.input import BuildingInput
from proto3.schema.program import ProgramInstance
from proto3.schema.serialize import from_json
from proto3.schema.validation import (
    AreaGateFailure,
    DimGateFailure,
    DomainGateFailure,
)
from proto3.stages import stage01_program, stage02_gate
from proto3.target import DEFAULT_APARTMENT_RULES_PATH, TargetAdapter

from .fixture_matrix import MATRIX, fixture_path


def _adapter() -> TargetAdapter:
    return TargetAdapter(DEFAULT_APARTMENT_RULES_PATH)


def _stage01(matrix_id: str) -> tuple[BuildingInput, ProgramInstance]:
    b = from_json(BuildingInput, fixture_path(matrix_id))
    inst = stage01_program.run(b, adapter=_adapter())
    return b, inst


# --- Fixture × Stage 02 matrix -----------------------------------------------------

@pytest.mark.parametrize("matrix_id", ["A1", "A2", "B1", "D1"])
def test_stage02_passes_for_feasible_fixtures(matrix_id):
    """A1 / A2 / B1 / D1 must pass Stage 02 (false-reject regression)."""
    b, inst = _stage01(matrix_id)
    out = stage02_gate.run(b, instance=inst, adapter=_adapter())
    assert isinstance(out, ProgramInstance)
    # Stage 02 is identity on accept (D020 fail-only).
    assert out is inst


def test_stage02_r2_raises_area_gate_failure():
    """R2 fixture: 4×4=16 m² × 0.85 = 13.6 m² capacity vs ~34 m² required.

    This is the first live AreaGateFailure trigger. fixture_matrix has
    `expected_failure: AreaGateFailure / verified_at: Step 06` since Plan v2.
    """
    b, inst = _stage01("R2")
    with pytest.raises(AreaGateFailure) as exc_info:
        stage02_gate.run(b, instance=inst, adapter=_adapter())

    fr = exc_info.value.failure
    assert fr.failure_type == "domain_area_gate_fail"
    assert fr.detected_stage == "02"
    # 16 m² footprint × 0.85 density = 13.6 m² capacity
    assert fr.evidence["footprint_area_m2"] == pytest.approx(16.0)
    assert fr.evidence["density_factor"] == 0.85
    assert fr.evidence["usable_capacity_m2"] == pytest.approx(13.6)
    # required-only sum (D023) — 5 spaces × role defaults: 12 + 5 + 7 + 7 + 3 = 34
    assert fr.evidence["total_required_area_m2"] == pytest.approx(34.0)
    assert fr.evidence["required_space_count"] == 5


def test_stage02_r2_subclass_caught_by_parent():
    """Catching DomainGateFailure (parent) catches AreaGateFailure (child)."""
    b, inst = _stage01("R2")
    with pytest.raises(DomainGateFailure):
        stage02_gate.run(b, instance=inst, adapter=_adapter())


def test_stage02_fixture_matrix_metadata_consistent_with_r2():
    """fixture_matrix.MATRIX['R2'].expected_failure should be 'AreaGateFailure'
    (set in Plan v2 at Step 04 forward-projection, verified now)."""
    assert MATRIX["R2"]["expected_failure"] == "AreaGateFailure"
    assert MATRIX["R2"]["verified_at"] == "Step 06"


# --- Stage 02 dim gate (synthetic) -------------------------------------------------

def test_stage02_dim_gate_raises_when_min_dim_exceeds_bbox(tmp_path):
    """Synthetic fixture: very long narrow footprint (2m × 30m = 60 m²) so the
    area gate passes but the bbox short side (2m) cannot host a 3m min_dim space."""
    import json
    fixture = {
        "target_type": "apartment",
        "floors": [
            {
                "footprint": [[0, 0], [2000, 0], [2000, 30000], [0, 30000]],  # 2m × 30m
                "floor_root": [1000, 0],
                "floor_program": None,
                "anchor_projections": [],
            }
        ],
        "program_request": {
            "spaces": [
                {"name": "living", "role": "public", "min_dimension_mm": 3000},
                {"name": "bedroom", "role": "private"},
                {"name": "bathroom", "role": "wet"},
            ]
        },
        "persistent_anchors": [],
    }
    p = tmp_path / "narrow.json"
    p.write_text(json.dumps(fixture), encoding="utf-8")
    b = from_json(BuildingInput, p)
    inst = stage01_program.run(b, adapter=_adapter())

    # area: 60 m² × 0.85 = 51 m² capacity vs 12+7+3 = 22 m² required → pass.
    # dim: bbox short = 2000mm; living min_dimension_mm = 3000mm → fail.
    with pytest.raises(DimGateFailure) as exc_info:
        stage02_gate.run(b, instance=inst, adapter=_adapter())
    fr = exc_info.value.failure
    assert fr.affected_space == "living"
    assert fr.evidence["min_dimension_mm"] == 3000
    assert fr.evidence["footprint_bbox_short_side_mm"] == 2000


# --- Stage 02 multi-floor placeholder (synthetic) -----------------------------------

def test_stage02_rejects_multi_floor_for_apartment(tmp_path):
    """apartment.json sets requires_single_floor=true — multi-floor BuildingInput
    must trip the multi-floor gate."""
    import json

    floor = {
        "footprint": [[0, 0], [8000, 0], [8000, 6000], [0, 6000]],
        "floor_root": [4000, 0],
        "floor_program": None,
        "anchor_projections": [],
    }
    fixture = {
        "target_type": "apartment",
        "floors": [floor, floor],  # two floors
        "program_request": {
            "spaces": [
                {"name": "living", "role": "public"},
                {"name": "bedroom", "role": "private"},
                {"name": "bathroom", "role": "wet"},
            ]
        },
        "persistent_anchors": [],
    }
    p = tmp_path / "two_floor_apt.json"
    p.write_text(json.dumps(fixture), encoding="utf-8")
    b = from_json(BuildingInput, p)
    inst = stage01_program.run(b, adapter=_adapter())

    with pytest.raises(DomainGateFailure) as exc_info:
        stage02_gate.run(b, instance=inst, adapter=_adapter())
    fr = exc_info.value.failure
    assert fr.failure_type == "domain_multi_floor_not_supported"
    assert fr.evidence["actual_floor_count"] == 2
