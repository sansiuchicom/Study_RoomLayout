"""Tests for stages.stage01_program (S04-D4, S04-D11, S04-D12)."""
from __future__ import annotations

import pytest

from proto3.schema.input import BuildingInput
from proto3.schema.program import ProgramInstance
from proto3.schema.serialize import from_json
from proto3.schema.validation import ProgramInstantiationFailure
from proto3.stages import stage01_program
from proto3.target import ApartmentAdapter

from .fixture_matrix import fixture_path


def _load(matrix_id: str) -> BuildingInput:
    return from_json(BuildingInput, fixture_path(matrix_id))


@pytest.mark.parametrize("matrix_id", ["A1", "A2", "B1", "R2"])
def test_stage01_passes_when_cardinality_satisfied(matrix_id):
    b = _load(matrix_id)
    inst = stage01_program.run(b, adapter=ApartmentAdapter())
    assert isinstance(inst, ProgramInstance)
    assert len(inst.space_units) == len(b.program_request["spaces"])


def test_stage01_r1_raises_program_instantiation_failure():
    b = _load("R1")
    with pytest.raises(ProgramInstantiationFailure) as exc_info:
        stage01_program.run(b, adapter=ApartmentAdapter())
    failure = exc_info.value.failure
    assert failure.failure_type == "program_cardinality_insufficient"
    assert failure.affected_space == "wet"
    assert failure.evidence == {"role": "wet", "required": 1, "actual": 0}
    assert failure.detected_stage == "01"


def test_stage01_raises_when_spaces_not_list():
    b = BuildingInput(program_request={"spaces": "not_a_list"})
    with pytest.raises(ProgramInstantiationFailure) as exc_info:
        stage01_program.run(b, adapter=ApartmentAdapter())
    assert exc_info.value.failure.failure_type == "program_request_schema_invalid"


def test_stage01_raises_when_space_missing_role():
    b = BuildingInput(program_request={"spaces": [{"name": "living"}]})
    with pytest.raises(ProgramInstantiationFailure) as exc_info:
        stage01_program.run(b, adapter=ApartmentAdapter())
    assert exc_info.value.failure.failure_type == "program_request_schema_invalid"


def test_stage01_raises_when_space_item_not_dict():
    b = BuildingInput(program_request={"spaces": ["just_a_string"]})
    with pytest.raises(ProgramInstantiationFailure) as exc_info:
        stage01_program.run(b, adapter=ApartmentAdapter())
    assert exc_info.value.failure.failure_type == "program_request_schema_invalid"
