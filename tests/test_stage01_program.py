"""Tests for stages.stage01_program (S04-D4, S04-D11, S04-D12).

Step 06 §4.2 transitional: shape-validity tests (spaces-not-list etc.) moved
to test_program_request.py since `ProgramRequest.__post_init__` now owns that
boundary. This file keeps cardinality-fail (R1) + happy paths.

§4.5 will reintroduce duplicate-name / unknown-role / type-mismatch guards
at the Stage 01 layer (S06-D7).
"""
from __future__ import annotations

import pytest

from proto3.schema.input import BuildingInput
from proto3.schema.program import ProgramInstance
from proto3.schema.serialize import from_json
from proto3.schema.validation import ProgramInstantiationFailure
from proto3.stages import stage01_program
from proto3.target import DEFAULT_APARTMENT_RULES_PATH, TargetAdapter

from .fixture_matrix import fixture_path


def _load(matrix_id: str) -> BuildingInput:
    return from_json(BuildingInput, fixture_path(matrix_id))


def _adapter() -> TargetAdapter:
    return TargetAdapter(DEFAULT_APARTMENT_RULES_PATH)


@pytest.mark.parametrize("matrix_id", ["A1", "A2", "B1", "R2"])
def test_stage01_passes_when_cardinality_satisfied(matrix_id):
    b = _load(matrix_id)
    inst = stage01_program.run(b, adapter=_adapter())
    assert isinstance(inst, ProgramInstance)
    assert len(inst.space_units) == len(b.program_request.spaces)


def test_stage01_r1_raises_program_instantiation_failure():
    b = _load("R1")
    with pytest.raises(ProgramInstantiationFailure) as exc_info:
        stage01_program.run(b, adapter=_adapter())
    failure = exc_info.value.failure
    assert failure.failure_type == "program_cardinality_insufficient"
    assert failure.affected_space == "wet"
    assert failure.evidence == {"role": "wet", "required": 1, "actual": 0}
    assert failure.detected_stage == "01"
