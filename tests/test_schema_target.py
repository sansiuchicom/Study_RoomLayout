"""Tests for `room_layout.schema.target` — Plan §4.3 / S05-D3.

Covers `TargetRules` construction, the minimal `__post_init__` guards
(density_factor > 0; valid Role keys; non-negative int counts), the empty
`min_cardinality` default, frozen contract, and serialize round-trip
(incl. the `dict[Role, int]` field).
"""

import pytest

from room_layout.schema import TargetRules, from_dict, to_dict


def _rules(**kwargs) -> TargetRules:
    base = dict(
        density_factor=0.7,
        requires_single_floor=True,
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
    r = TargetRules(density_factor=0.5, requires_single_floor=False)
    assert r.min_cardinality == {}


def test_target_rules_is_frozen():
    from dataclasses import FrozenInstanceError

    r = _rules()
    with pytest.raises(FrozenInstanceError):
        r.density_factor = 0.9


# --- minimal value guards (S05-D3) ---


@pytest.mark.parametrize("bad", [0.0, -0.1])
def test_rejects_nonpositive_density_factor(bad):
    with pytest.raises(ValueError, match="density_factor"):
        _rules(density_factor=bad)


def test_rejects_unknown_role_key():
    with pytest.raises(ValueError, match="Role Literal"):
        _rules(min_cardinality={"bedroom": 1})


def test_rejects_negative_count():
    with pytest.raises(ValueError, match="non-negative"):
        _rules(min_cardinality={"wet": -1})


def test_rejects_corridor_role_key():
    """`corridor` is a Role Literal member but still a valid cardinality key
    here — it is rejected only as a *space input* (S02-D9), not as a rule
    key. This documents that TargetRules does not re-apply that asymmetry."""
    r = _rules(min_cardinality={"corridor": 0})
    assert r.min_cardinality["corridor"] == 0


# --- serialize ---


def test_target_rules_round_trips():
    r = _rules()
    assert from_dict(TargetRules, to_dict(r)) == r


def test_target_rules_round_trips_empty_cardinality():
    r = TargetRules(density_factor=0.6, requires_single_floor=False)
    assert from_dict(TargetRules, to_dict(r)) == r
