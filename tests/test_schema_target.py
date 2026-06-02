"""Tests for `room_layout.schema.target` — Plan §4.2 / S06-D1 (+ S05-D3).

Covers `TargetRules` construction, the minimal `__post_init__` guards
(density_factor in (0,1]; requestable Role keys, not corridor; non-negative
int counts; default_min_area_m2 full Role map of non-negative floats), the
empty `min_cardinality` default, frozen contract, and serialize round-trip.
"""

import pytest

from room_layout.schema import TargetRules, from_dict, to_dict

# A full Role map (S06-D1 requires every Role present, incl. corridor).
_FULL_DEFAULT_AREAS = {
    "public": 12.0,
    "private": 7.0,
    "service": 5.0,
    "wet": 3.0,
    "hub": 2.0,
    "corridor": 0.0,
    "vertical_circulation": 2.0,
}


def _rules(**kwargs) -> TargetRules:
    base = dict(
        density_factor=0.7,
        requires_single_floor=True,
        default_min_area_m2=dict(_FULL_DEFAULT_AREAS),
        min_cardinality={"wet": 1, "private": 2},
    )
    base.update(kwargs)
    return TargetRules(**base)


# --- construction + defaults ---


def test_target_rules_basic():
    r = _rules()
    assert r.density_factor == 0.7
    assert r.requires_single_floor is True
    assert r.min_cardinality == {"wet": 1, "private": 2}


def test_min_cardinality_defaults_to_empty():
    """Empty dict = no cardinality constraint (S05-D3)."""
    r = TargetRules(
        density_factor=0.5,
        requires_single_floor=False,
        default_min_area_m2=dict(_FULL_DEFAULT_AREAS),
    )
    assert r.min_cardinality == {}


def test_target_rules_is_frozen():
    from dataclasses import FrozenInstanceError

    r = _rules()
    with pytest.raises(FrozenInstanceError):
        r.density_factor = 0.9


# --- minimal value guards (S05-D3) ---


@pytest.mark.parametrize("bad", [0.0, -0.1, 1.5, 10.0])
def test_rejects_out_of_range_density_factor(bad):
    """0 < density_factor <= 1 — it is a usable-area fraction (review #8)."""
    with pytest.raises(ValueError, match="density_factor"):
        _rules(density_factor=bad)


def test_accepts_density_factor_at_one():
    """1.0 (100% usable) is the inclusive upper bound."""
    assert _rules(density_factor=1.0).density_factor == 1.0


def test_rejects_unknown_role_key():
    with pytest.raises(ValueError, match="not a valid cardinality key"):
        _rules(min_cardinality={"bedroom": 1})


def test_rejects_negative_count():
    with pytest.raises(ValueError, match="non-negative"):
        _rules(min_cardinality={"wet": -1})


def test_rejects_corridor_role_key():
    """`corridor` is not user-requestable (S02-D9), so a corridor cardinality
    rule is unsatisfiable by construction — reject it as a rule-authoring
    mistake (review 4.8), even at count 0, for a single clear contract."""
    with pytest.raises(ValueError, match="corridor"):
        _rules(min_cardinality={"corridor": 0})
    with pytest.raises(ValueError, match="corridor"):
        _rules(min_cardinality={"corridor": 1})


def test_accepts_vertical_circulation_key():
    """vertical_circulation IS requestable (anchor-bound) → valid key."""
    r = _rules(min_cardinality={"vertical_circulation": 1})
    assert r.min_cardinality["vertical_circulation"] == 1


# --- serialize ---


def test_target_rules_round_trips():
    r = _rules()
    assert from_dict(TargetRules, to_dict(r)) == r


def test_target_rules_round_trips_empty_cardinality():
    r = TargetRules(
        density_factor=0.6,
        requires_single_floor=False,
        default_min_area_m2=dict(_FULL_DEFAULT_AREAS),
    )
    assert from_dict(TargetRules, to_dict(r)) == r


# --- default_min_area_m2 guards (S06-D1) ---


def test_rejects_incomplete_default_area_map():
    """Must cover every Role (full map) so expand_program can't KeyError."""
    partial = {"public": 12.0}  # missing the rest
    with pytest.raises(ValueError, match="full Role map"):
        _rules(default_min_area_m2=partial)


def test_rejects_unknown_role_in_default_area_map():
    bad = {**_FULL_DEFAULT_AREAS, "bedroom": 5.0}
    with pytest.raises(ValueError, match="full Role map"):
        _rules(default_min_area_m2=bad)


def test_rejects_negative_default_area():
    bad = {**_FULL_DEFAULT_AREAS, "private": -1.0}
    with pytest.raises(ValueError, match="default_min_area_m2"):
        _rules(default_min_area_m2=bad)


def test_corridor_zero_default_area_ok():
    """corridor IS in the full map (carving emits corridor rooms); 0.0 is fine."""
    assert _rules().default_min_area_m2["corridor"] == 0.0
