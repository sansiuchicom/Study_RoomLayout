"""Tests for `room_layout.target.rules_loader` — Plan §4.3 / S06-D4, D2(가).

The loader owns JSON-boundary concerns (file/parse/finite); domain invariants
are delegated to TargetRules.__post_init__ via from_dict. Tests cover both:
the loader's own rejects (unreadable / malformed / non-object / non-finite)
and that delegated domain rejects still surface (with the path).
"""

import json

import pytest

from room_layout.schema import TargetRules
from room_layout.target import load_target_rules

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


# --- happy path ---


def test_loads_valid_file(tmp_path):
    r = load_target_rules(_write(tmp_path, _VALID))
    assert isinstance(r, TargetRules)
    assert r.density_factor == 0.85
    assert r.default_min_area_m2["public"] == 12.0
    assert r.min_cardinality == {"public": 1, "private": 1, "wet": 1}


def test_accepts_str_path(tmp_path):
    p = _write(tmp_path, _VALID)
    assert load_target_rules(str(p)).density_factor == 0.85


# --- loader-owned rejects (JSON boundary) ---


def test_rejects_missing_file(tmp_path):
    with pytest.raises(ValueError, match="unreadable"):
        load_target_rules(tmp_path / "nope.json")


def test_rejects_malformed_json(tmp_path):
    with pytest.raises(ValueError, match="malformed"):
        load_target_rules(_write(tmp_path, None, raw="{not json"))


def test_rejects_non_object_root(tmp_path):
    with pytest.raises(ValueError, match="must be an object"):
        load_target_rules(_write(tmp_path, [1, 2, 3]))


def test_rejects_nan_density(tmp_path):
    """NaN parses via json but must be rejected at the boundary (S06-D4)."""
    with pytest.raises(ValueError, match="non-finite"):
        load_target_rules(
            _write(tmp_path, None, raw=json.dumps({**_VALID, "density_factor": float("nan")}))
        )


def test_rejects_inf_in_default_area(tmp_path):
    bad = {**_VALID, "default_min_area_m2": {**_FULL_AREAS, "private": float("inf")}}
    with pytest.raises(ValueError, match="non-finite"):
        load_target_rules(_write(tmp_path, None, raw=json.dumps(bad)))


def test_path_appears_in_error(tmp_path):
    p = _write(tmp_path, [1])
    with pytest.raises(ValueError, match=str(p.name)):
        load_target_rules(p)


# --- delegated domain rejects (from_dict + __post_init__, re-raised w/ path) ---


def test_delegates_density_range_reject(tmp_path):
    with pytest.raises(ValueError, match="invalid"):
        load_target_rules(_write(tmp_path, {**_VALID, "density_factor": 1.5}))


def test_delegates_incomplete_area_map_reject(tmp_path):
    with pytest.raises(ValueError, match="invalid"):
        load_target_rules(_write(tmp_path, {**_VALID, "default_min_area_m2": {"public": 12.0}}))


def test_delegates_unknown_top_level_key_reject(tmp_path):
    with pytest.raises(ValueError, match="invalid"):
        load_target_rules(_write(tmp_path, {**_VALID, "bogus": 1}))


def test_delegates_missing_required_field_reject(tmp_path):
    incomplete = {k: v for k, v in _VALID.items() if k != "density_factor"}
    with pytest.raises(ValueError, match="invalid"):
        load_target_rules(_write(tmp_path, incomplete))
