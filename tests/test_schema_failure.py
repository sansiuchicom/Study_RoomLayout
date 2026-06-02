"""Tests for `room_layout.schema.failure`.

Covers: `FailureRecord` (mutability + default `data`), `DomainGateFailure`
hierarchy + record-carrying behavior, raise/catch via base class, and the
sibling `ProgramInstantiationFailure` (S05-D5 — distinct family, not a
`DomainGateFailure` subclass).
"""

import pytest

from room_layout.schema.failure import (
    AccessSchemaFailure,
    AreaGateFailure,
    DimGateFailure,
    DomainGateFailure,
    FailureRecord,
    ProgramInstantiationFailure,
)


def test_failure_record_minimal_has_empty_data():
    fr = FailureRecord(code="X", stage="s", message="m")
    assert fr.code == "X"
    assert fr.stage == "s"
    assert fr.message == "m"
    assert fr.data == {}


def test_failure_record_with_data():
    fr = FailureRecord(code="X", stage="s", message="m", data={"k": 1})
    assert fr.data == {"k": 1}


def test_failure_record_is_mutable():
    """S02-D3: FailureRecord is mutable — algorithm accumulates per stage."""
    fr = FailureRecord(code="X", stage="s", message="m")
    fr.code = "Y"
    fr.data["new"] = 42
    assert fr.code == "Y"
    assert fr.data == {"new": 42}


def test_domain_gate_failure_carries_record():
    fr = FailureRecord(code="X", stage="s", message="boom")
    exc = DomainGateFailure(fr)
    assert exc.record is fr
    assert str(exc) == "boom"


@pytest.mark.parametrize("cls", [AreaGateFailure, DimGateFailure, AccessSchemaFailure])
def test_subclasses_inherit_from_domain_gate_failure(cls):
    """proto3:D020 — Area / Dim / AccessSchema all share the base hierarchy."""
    fr = FailureRecord(code="X", stage="s", message="m")
    exc = cls(fr)
    assert isinstance(exc, DomainGateFailure)
    assert isinstance(exc, Exception)
    assert exc.record is fr


def test_subclass_can_be_caught_as_base():
    fr = FailureRecord(code="AREA", stage="area_gate", message="too small")
    with pytest.raises(DomainGateFailure) as exc_info:
        raise AreaGateFailure(fr)
    assert exc_info.value.record.code == "AREA"


# --- ProgramInstantiationFailure (S05-D5) ---


def test_program_instantiation_failure_carries_record():
    fr = FailureRecord(code="PROG", stage="01", message="bad program")
    exc = ProgramInstantiationFailure(fr)
    assert exc.record is fr
    assert str(exc) == "bad program"


def test_program_instantiation_failure_is_not_a_domain_gate_failure():
    """S05-D5 (option 가): the two families are siblings, not parent/child.
    Catching DomainGateFailure must NOT swallow an instantiation failure."""
    fr = FailureRecord(code="PROG", stage="01", message="m")
    exc = ProgramInstantiationFailure(fr)
    assert isinstance(exc, Exception)
    assert not isinstance(exc, DomainGateFailure)
    with pytest.raises(ProgramInstantiationFailure):
        raise ProgramInstantiationFailure(fr)
