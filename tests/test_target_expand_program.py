"""Tests for `room_layout.target.expand_program` — Plan §4.6 / S06-D1/D2/D3/D6.

Covers the field policy ({role:count} → SpaceUnitSpec list: ids, area_min from
rules, area_target/usage None, required True), target_type stamping, invalid-
role delegation, and the DoD check: expand output passes stage01 + stage02.
"""

import pytest

from room_layout.schema.geometry import FloorShape, ShapePart
from room_layout.stages import stage01_program, stage02_gate
from room_layout.target import DEFAULT_APARTMENT_RULES_PATH, expand_program, load_target_rules

RULES = load_target_rules(DEFAULT_APARTMENT_RULES_PATH)


def _floor(w=12.0, h=12.0) -> FloorShape:
    part = ShapePart(exterior=((0.0, 0.0), (w, 0.0), (w, h), (0.0, h)))
    return FloorShape(level=1, parts=[part], floor_to_floor_height=3.0)


# --- field policy ---


def test_expands_counts_to_specs():
    pr = expand_program({"public": 1, "private": 2}, "apartment", rules=RULES)
    specs = pr.floor_programs[1]
    assert [s.id for s in specs] == ["public_1", "private_1", "private_2"]


def test_area_min_sourced_from_rules():
    pr = expand_program({"private": 1, "wet": 1}, "apartment", rules=RULES)
    by_id = {s.id: s for s in pr.floor_programs[1]}
    assert by_id["private_1"].area_min_m2 == 7.0  # apartment default
    assert by_id["wet_1"].area_min_m2 == 2.5


def test_area_target_and_usage_are_none():
    pr = expand_program({"public": 1}, "apartment", rules=RULES)
    s = pr.floor_programs[1][0]
    assert s.area_target_m2 is None  # S06-D2
    assert s.usage is None  # S06-D3


def test_all_required():
    pr = expand_program({"public": 1, "wet": 1}, "apartment", rules=RULES)
    assert all(s.required for s in pr.floor_programs[1])


def test_target_type_stamped():
    pr = expand_program({"public": 1}, "house", rules=RULES)
    assert pr.target_type == "house"  # S06-D6: caller's value, not validated vs rules


def test_level_routing():
    pr = expand_program({"public": 1}, "apartment", rules=RULES, level=3)
    assert set(pr.floor_programs) == {3}


def test_zero_count_produces_no_rooms():
    pr = expand_program({"public": 1, "private": 0}, "apartment", rules=RULES)
    assert [s.role for s in pr.floor_programs[1]] == ["public"]


# --- guards / delegation ---


def test_negative_count_rejected():
    with pytest.raises(ValueError, match="negative"):
        expand_program({"public": -1}, "apartment", rules=RULES)


def test_invalid_input_role_delegated_to_spec():
    """corridor is not a valid input role — SpaceUnitSpec.__post_init__ rejects
    it (S02-D9); expand does not re-screen (S05-D8 spirit)."""
    with pytest.raises(ValueError, match="corridor"):
        expand_program({"corridor": 1}, "apartment", rules=RULES)


# --- DoD: expand output is admissible ---


def test_output_passes_stage01_cardinality():
    pr = expand_program({"public": 1, "private": 1, "wet": 1}, "apartment", rules=RULES)
    # apartment min_cardinality {public,private,wet:1} → satisfied
    out = stage01_program.run(pr.floor_programs[1], rules=RULES)
    assert out is pr.floor_programs[1]


def test_output_passes_stage02_gates():
    pr = expand_program({"public": 1, "private": 2, "wet": 1}, "apartment", rules=RULES)
    specs = pr.floor_programs[1]
    # 9 + 7 + 7 + 2.5 = 25.5 ≤ 144 * 0.85 = 122.4 → admits
    out = stage02_gate.run(_floor(), specs, rules=RULES)
    assert out is specs


def test_output_fails_stage01_when_cardinality_unmet():
    """A program with no public room fails apartment cardinality (public>=1)."""
    pr = expand_program({"private": 1, "wet": 1}, "apartment", rules=RULES)
    from room_layout.schema.failure import ProgramInstantiationFailure

    with pytest.raises(ProgramInstantiationFailure):
        stage01_program.run(pr.floor_programs[1], rules=RULES)
