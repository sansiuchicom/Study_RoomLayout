"""Tests for `room_layout.stages.stage01_program` — Plan §4.6 / S05-D5, D8.

Stage 01 owns the rules-based cardinality gate only (S05-D8). It returns the
specs unchanged on success (S05-D5) and raises ProgramInstantiationFailure on
required-only cardinality under-supply (D023). Structural / cross-ref checks
live in __post_init__ / validate_input and are NOT re-tested here.
"""

import pytest

from room_layout.schema.failure import ProgramInstantiationFailure
from room_layout.schema.program import SpaceUnitSpec
from room_layout.schema.target import TargetRules
from room_layout.stages import stage01_program


def _sus(id, role, required=True) -> SpaceUnitSpec:
    return SpaceUnitSpec(
        id=id, role=role, usage=None, area_min_m2=5.0, required=required
    )


def _rules(min_cardinality) -> TargetRules:
    return TargetRules(
        density_factor=0.7,
        requires_single_floor=True,
        min_cardinality=min_cardinality,
    )


def test_returns_specs_unchanged_on_success():
    specs = [_sus("a", "hub"), _sus("b", "private"), _sus("c", "private")]
    rules = _rules({"hub": 1, "private": 2})
    out = stage01_program.run(specs, rules=rules)
    assert out is specs  # S05-D5: identity, no concretization


def test_empty_cardinality_always_passes():
    specs = [_sus("a", "private")]
    out = stage01_program.run(specs, rules=_rules({}))
    assert out is specs


def test_fails_when_role_count_below_min():
    specs = [_sus("a", "hub"), _sus("b", "private")]
    rules = _rules({"private": 2})  # only 1 private present
    with pytest.raises(ProgramInstantiationFailure) as exc:
        stage01_program.run(specs, rules=rules)
    rec = exc.value.record
    assert rec.code == "PROGRAM_CARDINALITY_INSUFFICIENT"
    assert rec.data == {"role": "private", "required_min": 2, "actual": 1}


def test_optional_spaces_do_not_satisfy_cardinality():
    """D023: an optional private room does not count toward min_cardinality."""
    specs = [_sus("a", "hub"), _sus("b", "private", required=False)]
    rules = _rules({"private": 1})
    with pytest.raises(ProgramInstantiationFailure) as exc:
        stage01_program.run(specs, rules=rules)
    assert exc.value.record.data["actual"] == 0


def test_missing_role_entirely_counts_as_zero():
    specs = [_sus("a", "hub")]
    rules = _rules({"wet": 1})  # no wet space at all
    with pytest.raises(ProgramInstantiationFailure) as exc:
        stage01_program.run(specs, rules=rules)
    assert exc.value.record.data["actual"] == 0


def test_exact_cardinality_passes():
    specs = [_sus("a", "wet")]
    out = stage01_program.run(specs, rules=_rules({"wet": 1}))
    assert out is specs


def test_first_failing_role_reported():
    """Multiple roles short → the first one Counter/dict iterates is raised
    (fail-fast; we only assert a valid under-supplied role is reported)."""
    specs = [_sus("a", "hub")]
    rules = _rules({"private": 2, "wet": 1})
    with pytest.raises(ProgramInstantiationFailure) as exc:
        stage01_program.run(specs, rules=rules)
    assert exc.value.record.data["role"] in {"private", "wet"}
    assert exc.value.record.data["actual"] == 0
