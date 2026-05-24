"""Tests for ProgramRequest dataclass + Role Literal (Step 06 §4.2, S06-D8, D10).

Covers:
- ProgramRequest.__post_init__ shape validation (spaces is list, items are SpaceUnitSpec).
- SpaceUnitSpec.role: Role Literal — D017 strict validation via from_dict.
- BuildingInput.program_request deserialization round-trip with the typed shape.
"""
from __future__ import annotations

import pytest

from proto3.schema.input import BuildingInput
from proto3.schema.program import ProgramRequest, SpaceUnitSpec
from proto3.schema.serialize import from_dict, to_dict


# --- ProgramRequest.__post_init__ ---------------------------------------------------

def test_program_request_default_is_empty_spaces_list():
    pr = ProgramRequest()
    assert pr.spaces == []


def test_program_request_accepts_list_of_space_unit_spec():
    pr = ProgramRequest(spaces=[
        SpaceUnitSpec(name="living", role="public"),
        SpaceUnitSpec(name="bedroom_1", role="private"),
    ])
    assert len(pr.spaces) == 2
    assert pr.spaces[0].name == "living"


def test_program_request_raises_when_spaces_not_list():
    with pytest.raises(ValueError, match="must be list"):
        ProgramRequest(spaces="not_a_list")  # type: ignore[arg-type]


def test_program_request_raises_when_spaces_is_dict():
    with pytest.raises(ValueError, match="must be list"):
        ProgramRequest(spaces={"living": "public"})  # type: ignore[arg-type]


def test_program_request_raises_when_item_is_not_space_unit_spec():
    with pytest.raises(ValueError, match=r"spaces\[0\] must be SpaceUnitSpec"):
        ProgramRequest(spaces=[{"name": "living", "role": "public"}])  # type: ignore[list-item]


def test_program_request_raises_when_item_is_string():
    with pytest.raises(ValueError, match=r"spaces\[1\] must be SpaceUnitSpec"):
        ProgramRequest(spaces=[
            SpaceUnitSpec(name="living", role="public"),
            "just_a_string",  # type: ignore[list-item]
        ])


# --- Role Literal (D017 via from_dict) ----------------------------------------------

def test_space_unit_spec_default_role_is_none():
    s = SpaceUnitSpec()
    assert s.role is None


def test_space_unit_spec_accepts_canonical_roles():
    for r in ("public", "private", "service", "wet", "hub", "corridor"):
        s = SpaceUnitSpec(name="x", role=r)
        assert s.role == r


def test_space_unit_spec_role_unknown_value_raises_via_from_dict():
    """D017 strict Literal validation kicks in at deserialize time."""
    with pytest.raises(ValueError, match="not in allowed Literal"):
        from_dict(SpaceUnitSpec, {"name": "x", "role": "rolee"})


def test_space_unit_spec_role_none_is_allowed_via_from_dict():
    """Role | None — None is a valid placeholder; Stage 01 enforces non-None at instantiation (S06-D10)."""
    s = from_dict(SpaceUnitSpec, {"name": "x", "role": None})
    assert s.role is None


# --- BuildingInput integration ------------------------------------------------------

def test_building_input_default_program_request_is_empty():
    b = BuildingInput()
    assert isinstance(b.program_request, ProgramRequest)
    assert b.program_request.spaces == []


def test_building_input_from_dict_typed_program_request():
    """fixture-shaped raw dict deserializes into the typed ProgramRequest."""
    raw = {
        "target_type": "apartment",
        "floors": [],
        "program_request": {
            "spaces": [
                {"name": "living", "role": "public"},
                {"name": "bathroom_1", "role": "wet"},
            ]
        },
        "persistent_anchors": [],
    }
    b = from_dict(BuildingInput, raw)
    assert isinstance(b.program_request, ProgramRequest)
    assert len(b.program_request.spaces) == 2
    assert b.program_request.spaces[0].name == "living"
    assert b.program_request.spaces[1].role == "wet"


def test_building_input_round_trip_typed_program_request():
    raw = {
        "target_type": "apartment",
        "floors": [],
        "program_request": {"spaces": [{"name": "living", "role": "public"}]},
        "persistent_anchors": [],
    }
    b = from_dict(BuildingInput, raw)
    rebuilt = to_dict(b)
    # SpaceUnitSpec has more fields than the raw dict; raw subset must match
    assert rebuilt["program_request"]["spaces"][0]["name"] == "living"
    assert rebuilt["program_request"]["spaces"][0]["role"] == "public"


# --- SpaceUnitSpec.__post_init__ value validation (merge-prep #1) ------------------

def test_space_unit_spec_default_constructible():
    """Default placeholder still valid (test_smoke compatibility)."""
    SpaceUnitSpec()


def test_space_unit_spec_name_must_be_str():
    with pytest.raises(ValueError, match="name must be str"):
        SpaceUnitSpec(name=123)  # type: ignore[arg-type]


def test_space_unit_spec_required_must_be_bool():
    """`required=1` or `required="true"` are silent-fail traps; type-strict bool."""
    with pytest.raises(ValueError, match="required must be bool"):
        SpaceUnitSpec(name="x", role="public", required="true")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="required must be bool"):
        SpaceUnitSpec(name="x", role="public", required=1)  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["min_area_m2", "max_area_m2", "preferred_area_m2"])
@pytest.mark.parametrize("bad", [-1.0, -0.01, "large", float("nan"), float("inf"), True, False])
def test_space_unit_spec_area_fields_reject_invalid(field, bad):
    kwargs = {"name": "x", "role": "public", field: bad}
    with pytest.raises(ValueError, match=field):
        SpaceUnitSpec(**kwargs)


@pytest.mark.parametrize("good", [0, 0.0, 7.5, 100])
def test_space_unit_spec_area_fields_accept_non_negative_finite(good):
    SpaceUnitSpec(name="x", role="public", min_area_m2=good)


@pytest.mark.parametrize("bad", [0, -1, 1.5, "2400", True])
def test_space_unit_spec_min_dimension_rejects_invalid(bad):
    with pytest.raises(ValueError, match="min_dimension_mm"):
        SpaceUnitSpec(name="x", role="public", min_dimension_mm=bad)  # type: ignore[arg-type]


def test_space_unit_spec_max_area_must_not_be_less_than_min():
    with pytest.raises(ValueError, match="max_area_m2.*must be"):
        SpaceUnitSpec(name="x", role="public", min_area_m2=10.0, max_area_m2=5.0)


def test_space_unit_spec_max_area_equal_min_allowed():
    """Equal bounds are valid (single fixed area)."""
    SpaceUnitSpec(name="x", role="public", min_area_m2=10.0, max_area_m2=10.0)
