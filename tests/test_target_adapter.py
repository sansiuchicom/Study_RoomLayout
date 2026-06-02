"""Tests for `room_layout.target.adapter` — Plan §4.4 / S06-D5, D6.

TargetAdapter is a validated rules provider: it loads + validates at
construction and exposes target_rules(). No target_type introspection (S06-D6)
and no load_fixture (S06-D5 / 4.4 가).
"""

import json

import pytest

from room_layout.schema import TargetRules
from room_layout.target import TargetAdapter

_FULL_AREAS = {
    "public": 12.0,
    "private": 7.0,
    "service": 5.0,
    "wet": 3.0,
    "hub": 2.0,
    "corridor": 0.0,
    "vertical_circulation": 2.0,
}

_VALID = {
    "density_factor": 0.85,
    "requires_single_floor": True,
    "default_min_area_m2": _FULL_AREAS,
    "min_cardinality": {"public": 1, "private": 1, "wet": 1},
}


def _write(tmp_path, obj, *, raw=None):
    p = tmp_path / "rules.json"
    p.write_text(raw if raw is not None else json.dumps(obj), encoding="utf-8")
    return p


def test_provides_validated_rules(tmp_path):
    a = TargetAdapter(_write(tmp_path, _VALID))
    rules = a.target_rules()
    assert isinstance(rules, TargetRules)
    assert rules.density_factor == 0.85
    assert rules.default_min_area_m2["public"] == 12.0


def test_same_instance_returned(tmp_path):
    """target_rules() returns the construction-time validated object."""
    a = TargetAdapter(_write(tmp_path, _VALID))
    assert a.target_rules() is a.target_rules()


def test_validates_at_construction(tmp_path):
    """A bad rules file fails when the adapter is built, not later."""
    with pytest.raises(ValueError):
        TargetAdapter(_write(tmp_path, {**_VALID, "density_factor": 1.5}))


def test_accepts_str_path(tmp_path):
    a = TargetAdapter(str(_write(tmp_path, _VALID)))
    assert a.target_rules().requires_single_floor is True


def test_no_target_type_property(tmp_path):
    """S06-D6: no target_type introspection (nothing downstream reads it)."""
    a = TargetAdapter(_write(tmp_path, _VALID))
    assert not hasattr(a, "target_type")
