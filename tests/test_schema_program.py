"""Tests for `room_layout.schema.program` — work item 4.8 / Plan §4.8.

Covers: `Role` Literal acceptance (incl. S02-D9 `corridor` rejection),
`SpaceUnitSpec.anchor_id` rule for `vertical_circulation` role,
`ProgramRequest` non-empty `target_type` + `floor_programs`, frozen
input contract (S02-D3).
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


def test_space_unit_spec_vertical_circulation_requires_anchor_id():
    with pytest.raises(ValueError, match="anchor_id"):
        _sus(role="vertical_circulation")


def test_space_unit_spec_vertical_circulation_with_anchor_id_accepts():
    s = _sus(role="vertical_circulation", anchor_id="stair_1")
    assert s.anchor_id == "stair_1"


def test_space_unit_spec_is_frozen():
    s = _sus()
    with pytest.raises(FrozenInstanceError):
        s.role = "private"


# --- ProgramRequest ---


def test_program_request_valid():
    pr = ProgramRequest(target_type="apartment", floor_programs={1: [_sus()]})
    assert pr.target_type == "apartment"
    assert 1 in pr.floor_programs


def test_program_request_rejects_empty_target_type():
    with pytest.raises(ValueError, match="target_type"):
        ProgramRequest(target_type="", floor_programs={1: [_sus()]})


def test_program_request_rejects_whitespace_target_type():
    with pytest.raises(ValueError, match="target_type"):
        ProgramRequest(target_type="   ", floor_programs={1: [_sus()]})


def test_program_request_rejects_empty_floor_programs():
    with pytest.raises(ValueError, match="floor_programs"):
        ProgramRequest(target_type="apartment", floor_programs={})


def test_program_request_is_frozen():
    pr = ProgramRequest(target_type="apartment", floor_programs={1: [_sus()]})
    with pytest.raises(FrozenInstanceError):
        pr.target_type = "office"
