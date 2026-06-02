"""Tests for the shipped `data/target_rules/apartment.json` — Plan §4.5.

Guards that the real apartment rules file is valid + loads via the adapter's
default path, and pins the documented values (provenance is in
`data/target_rules/README.md` §2). A value change must update both.
"""

from room_layout.schema import TargetRules
from room_layout.target import DEFAULT_APARTMENT_RULES_PATH, TargetAdapter, load_target_rules


def test_default_path_exists():
    assert DEFAULT_APARTMENT_RULES_PATH.is_file()


def test_apartment_rules_load_via_loader():
    r = load_target_rules(DEFAULT_APARTMENT_RULES_PATH)
    assert isinstance(r, TargetRules)


def test_adapter_loads_default_apartment():
    a = TargetAdapter(DEFAULT_APARTMENT_RULES_PATH)
    assert isinstance(a.target_rules(), TargetRules)


def test_apartment_documented_values():
    """Pins the README §2 provenance values — change both together."""
    r = load_target_rules(DEFAULT_APARTMENT_RULES_PATH)
    assert r.density_factor == 0.85
    assert r.requires_single_floor is True
    assert r.min_cardinality == {"public": 1, "private": 1, "wet": 1}
    assert r.default_min_area_m2 == {
        "public": 9.0,
        "private": 7.0,
        "service": 4.0,
        "wet": 2.5,
        "hub": 2.0,
        "corridor": 0.0,
        "vertical_circulation": 2.0,
    }
