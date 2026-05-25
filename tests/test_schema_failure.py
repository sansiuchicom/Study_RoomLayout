"""Tests for `room_layout.schema.failure` — work item 4.8 / Plan §4.8.

Covers: `FailureRecord` (mutability + default `data`), `DomainGateFailure`
hierarchy + record-carrying behavior, raise/catch via base class.
"""

import pytest

from room_layout.schema.failure import (
    AccessSchemaFailure,
    AreaGateFailure,
    DimGateFailure,
    DomainGateFailure,
    FailureRecord,
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
