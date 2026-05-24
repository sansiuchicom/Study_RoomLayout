"""Tests for TargetRules dataclass + rules_loader (Step 06 §4.3, S06-D4, D9).

Covers:
- TargetRules dataclass shape (no defaults — fail-loud against silent fallback).
- load_target_rules happy path (default apartment.json).
- load_target_rules validation: missing/extra fields, type mismatch,
  unknown roles, out-of-range values, malformed JSON, unreadable file.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from proto3.target import DEFAULT_APARTMENT_RULES_PATH, TargetRules
from proto3.target.rules_loader import load_target_rules


# --- TargetRules dataclass --------------------------------------------------------

def test_target_rules_requires_all_fields():
    """No dataclass-level defaults (S06-D9). Missing args raise TypeError."""
    with pytest.raises(TypeError):
        TargetRules()  # type: ignore[call-arg]


def test_target_rules_construct_with_explicit_fields():
    r = TargetRules(
        target_type="apartment",
        min_cardinality={"public": 1},
        default_min_area_m2={"public": 12.0},
        density_factor=0.85,
        requires_single_floor=True,
    )
    assert r.target_type == "apartment"
    assert r.density_factor == 0.85


# --- load_target_rules: happy path ------------------------------------------------

def test_load_default_apartment_rules():
    r = load_target_rules(DEFAULT_APARTMENT_RULES_PATH)
    assert isinstance(r, TargetRules)
    assert r.target_type == "apartment"
    assert r.density_factor == 0.85
    assert r.requires_single_floor is True
    assert r.min_cardinality == {"public": 1, "private": 1, "wet": 1}
    assert r.default_min_area_m2 == {
        "public": 12.0, "service": 5.0, "private": 7.0,
        "wet": 3.0, "hub": 2.0, "corridor": 0.0,
    }


# --- load_target_rules: validation (negative paths) -------------------------------

def _write(tmp: Path, payload: dict) -> Path:
    p = tmp / "rules.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def _valid_payload() -> dict:
    return {
        "target_type": "apartment",
        "density_factor": 0.85,
        "requires_single_floor": True,
        "min_cardinality": {"public": 1, "private": 1, "wet": 1},
        "default_min_area_m2": {
            "public": 12.0, "service": 5.0, "private": 7.0,
            "wet": 3.0, "hub": 2.0, "corridor": 0.0,
        },
    }


def test_load_unreadable_file(tmp_path: Path):
    with pytest.raises(ValueError, match="unreadable"):
        load_target_rules(tmp_path / "missing.json")


def test_load_malformed_json(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{ not json", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed"):
        load_target_rules(p)


def test_load_top_level_not_object(tmp_path: Path):
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match="must be an object"):
        load_target_rules(p)


def test_load_missing_field(tmp_path: Path):
    payload = _valid_payload()
    del payload["density_factor"]
    with pytest.raises(ValueError, match="missing required fields"):
        load_target_rules(_write(tmp_path, payload))


def test_load_unknown_target_type(tmp_path: Path):
    payload = _valid_payload()
    payload["target_type"] = "bunker"
    with pytest.raises(ValueError, match="target_rules.target_type"):
        load_target_rules(_write(tmp_path, payload))


def test_load_target_type_wrong_type(tmp_path: Path):
    payload = _valid_payload()
    payload["target_type"] = 42
    with pytest.raises(ValueError, match="target_rules.target_type"):
        load_target_rules(_write(tmp_path, payload))


def test_load_extra_field(tmp_path: Path):
    payload = _valid_payload()
    payload["extra_thing"] = 42
    with pytest.raises(ValueError, match="unknown fields"):
        load_target_rules(_write(tmp_path, payload))


@pytest.mark.parametrize("bad", [-0.1, 0, 1.5, "0.85", True, False])
def test_load_density_factor_out_of_range_or_wrong_type(tmp_path: Path, bad):
    payload = _valid_payload()
    payload["density_factor"] = bad
    with pytest.raises(ValueError, match="density_factor"):
        load_target_rules(_write(tmp_path, payload))


def test_load_requires_single_floor_must_be_bool(tmp_path: Path):
    payload = _valid_payload()
    payload["requires_single_floor"] = "yes"
    with pytest.raises(ValueError, match="requires_single_floor"):
        load_target_rules(_write(tmp_path, payload))


def test_load_min_cardinality_unknown_role(tmp_path: Path):
    payload = _valid_payload()
    payload["min_cardinality"]["bogus"] = 1
    with pytest.raises(ValueError, match="min_cardinality role 'bogus'"):
        load_target_rules(_write(tmp_path, payload))


def test_load_min_cardinality_negative(tmp_path: Path):
    payload = _valid_payload()
    payload["min_cardinality"]["public"] = -1
    with pytest.raises(ValueError, match=r"min_cardinality\['public'\]"):
        load_target_rules(_write(tmp_path, payload))


def test_load_min_cardinality_non_int(tmp_path: Path):
    payload = _valid_payload()
    payload["min_cardinality"]["public"] = 1.5
    with pytest.raises(ValueError, match=r"min_cardinality\['public'\]"):
        load_target_rules(_write(tmp_path, payload))


def test_load_default_min_area_unknown_role(tmp_path: Path):
    payload = _valid_payload()
    payload["default_min_area_m2"]["bogus"] = 5.0
    with pytest.raises(ValueError, match="unknown roles"):
        load_target_rules(_write(tmp_path, payload))


def test_load_default_min_area_missing_role(tmp_path: Path):
    """default_min_area_m2 must specify every Role (D023 fill semantics)."""
    payload = _valid_payload()
    del payload["default_min_area_m2"]["hub"]
    with pytest.raises(ValueError, match="must specify every Role.*missing"):
        load_target_rules(_write(tmp_path, payload))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_load_default_min_area_rejects_nan_inf(tmp_path: Path, bad):
    payload = _valid_payload()
    payload["default_min_area_m2"]["public"] = bad
    with pytest.raises(ValueError, match=r"default_min_area_m2\['public'\].*finite"):
        load_target_rules(_write(tmp_path, payload))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_load_density_factor_rejects_nan_inf(tmp_path: Path, bad):
    payload = _valid_payload()
    payload["density_factor"] = bad
    with pytest.raises(ValueError, match="density_factor.*finite"):
        load_target_rules(_write(tmp_path, payload))


def test_load_min_cardinality_sparse_ok(tmp_path: Path):
    """min_cardinality is intentionally sparse — unspecified roles imply 0."""
    payload = _valid_payload()
    payload["min_cardinality"] = {"public": 1}  # sparse: only public
    r = load_target_rules(_write(tmp_path, payload))
    assert r.min_cardinality == {"public": 1}


def test_load_default_min_area_negative(tmp_path: Path):
    payload = _valid_payload()
    payload["default_min_area_m2"]["public"] = -1.0
    with pytest.raises(ValueError, match=r"default_min_area_m2\['public'\]"):
        load_target_rules(_write(tmp_path, payload))


def test_load_default_min_area_wrong_type(tmp_path: Path):
    payload = _valid_payload()
    payload["default_min_area_m2"]["public"] = "twelve"
    with pytest.raises(ValueError, match=r"default_min_area_m2\['public'\]"):
        load_target_rules(_write(tmp_path, payload))


def test_load_int_area_coerced_to_float(tmp_path: Path):
    """JSON `12` is allowed; loader coerces to float."""
    payload = _valid_payload()
    payload["default_min_area_m2"]["public"] = 12  # int
    r = load_target_rules(_write(tmp_path, payload))
    assert r.default_min_area_m2["public"] == 12.0
    assert isinstance(r.default_min_area_m2["public"], float)
