"""Tests for `room_layout.schema.program` — work item 4.8 / Plan §4.8.

Covers: `Role` Literal validation (incl. S02-D9 `corridor` rejection),
`TargetType` Literal validation, `SpaceUnitSpec.anchor_id` rule for
`vertical_circulation` role, the S05-D1 area-field realignment (required
`area_min_m2`, optional `area_target_m2`) + minimal value guards,
Optional `min_dimension_m` (Pipeline §2.2), `ProgramRequest` non-empty
`floor_programs`, frozen input contract (S02-D3).
"""

from dataclasses import FrozenInstanceError

import pytest

from room_layout.schema.program import ProgramRequest, SpaceUnitSpec


def _sus(**kwargs):
    base = dict(
        id="x",
        role="public",
        usage=None,
        area_target_m2=10.0,
        area_min_m2=8.0,
        min_dimension_m=2.0,
        required=True,
    )
    base.update(kwargs)
    return SpaceUnitSpec(**base)


# --- SpaceUnitSpec ---


@pytest.mark.parametrize("role", ["public", "private", "service", "wet", "hub"])
def test_space_unit_spec_accepts_non_vc_roles(role):
    s = _sus(role=role)
    assert s.role == role
    assert s.anchor_id is None


def test_space_unit_spec_rejects_corridor_role():
    """S02-D9: corridor is the output of carving, not user-requestable."""
    with pytest.raises(ValueError, match="corridor"):
        _sus(role="corridor")


@pytest.mark.parametrize("bad_role", ["bedroom", "BATHROOM", "", "foo"])
def test_space_unit_spec_rejects_unknown_role(bad_role):
    """Direct-construction Role Literal validation (close-time cleanup)."""
    with pytest.raises(ValueError, match="Role Literal"):
        _sus(role=bad_role)


def test_space_unit_spec_vertical_circulation_requires_anchor_id():
    with pytest.raises(ValueError, match="anchor_id"):
        _sus(role="vertical_circulation")


def test_space_unit_spec_vertical_circulation_with_anchor_id_accepts():
    s = _sus(role="vertical_circulation", anchor_id="stair_1")
    assert s.anchor_id == "stair_1"


def test_space_unit_spec_non_vc_with_anchor_id_rejected():
    # converse invariant (S07 review): anchor binding is vc-only (D004)
    with pytest.raises(ValueError, match="anchor_id is only valid"):
        _sus(role="public", anchor_id="stair_1")


def test_space_unit_spec_accepts_none_area_target():
    """S05-D1: `area_target_m2: float | None` — the optional diffusion hook."""
    s = _sus(area_target_m2=None)
    assert s.area_target_m2 is None


def test_space_unit_spec_accepts_none_min_dimension():
    """Pipeline §2.2: `min_dimension_m: float | None`."""
    s = _sus(min_dimension_m=None)
    assert s.min_dimension_m is None


# --- S05-D1 minimal value guards ---


def test_space_unit_spec_rejects_empty_id():
    with pytest.raises(ValueError, match="non-empty"):
        _sus(id="")


def test_space_unit_spec_rejects_negative_area_min():
    with pytest.raises(ValueError, match="area_min_m2"):
        _sus(area_min_m2=-1.0)


def test_space_unit_spec_accepts_zero_area_min():
    """area_min_m2 >= 0 — zero is a valid (no-minimum) floor."""
    s = _sus(area_min_m2=0.0)
    assert s.area_min_m2 == 0.0


def test_space_unit_spec_rejects_target_below_min():
    """S05-D1 (option 가): area_target_m2 >= area_min_m2 when both set."""
    with pytest.raises(ValueError, match="area_target_m2"):
        _sus(area_min_m2=8.0, area_target_m2=5.0)


def test_space_unit_spec_accepts_target_equal_min():
    s = _sus(area_min_m2=8.0, area_target_m2=8.0)
    assert s.area_target_m2 == 8.0


def test_space_unit_spec_rejects_nonpositive_min_dimension():
    with pytest.raises(ValueError, match="min_dimension_m"):
        _sus(min_dimension_m=0.0)


def test_space_unit_spec_is_frozen():
    s = _sus()
    with pytest.raises(FrozenInstanceError):
        s.role = "private"


# --- ProgramRequest ---


@pytest.mark.parametrize("target_type", ["apartment", "house", "hotel", "office", "warehouse"])
def test_program_request_accepts_valid_target_types(target_type):
    pr = ProgramRequest(target_type=target_type, floor_programs={1: [_sus()]})
    assert pr.target_type == target_type


@pytest.mark.parametrize("bad", ["", "   ", "studio", "office_building", "APARTMENT"])
def test_program_request_rejects_invalid_target_type(bad):
    """Direct-construction TargetType Literal validation (close-time cleanup).

    Subsumes the prior "non-empty / non-whitespace" checks since empty
    and whitespace strings are not in the TargetType Literal.
    """
    with pytest.raises(ValueError, match="TargetType Literal"):
        ProgramRequest(target_type=bad, floor_programs={1: [_sus()]})


def test_program_request_rejects_empty_floor_programs():
    with pytest.raises(ValueError, match="floor_programs"):
        ProgramRequest(target_type="apartment", floor_programs={})


def test_program_request_is_frozen():
    pr = ProgramRequest(target_type="apartment", floor_programs={1: [_sus()]})
    with pytest.raises(FrozenInstanceError):
        pr.target_type = "office"
