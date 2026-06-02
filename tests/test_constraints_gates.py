"""Tests for `room_layout.constraints.gates` — Plan §4.5 / S05-D4.

Each gate is exercised with inline primitive inputs: the pass case, each
fail branch, and the required-only (D023) / None-skip behaviors. No
TargetRules object — gates take primitive domain values by injection.
"""

import pytest

from room_layout.constraints.gates import (
    check_access_schema,
    check_min_area,
    check_min_dim,
    check_multi_floor_feasibility,
)
from room_layout.schema.failure import (
    AreaGateFailure,
    DimGateFailure,
    DomainGateFailure,
)
from room_layout.schema.program import SpaceUnitSpec


def _sus(**kwargs) -> SpaceUnitSpec:
    base = dict(
        id="r",
        role="private",
        usage=None,
        area_min_m2=10.0,
        required=True,
    )
    base.update(kwargs)
    return SpaceUnitSpec(**base)


# --- check_min_area ---


def test_min_area_passes_when_under_capacity():
    specs = [_sus(id="a", area_min_m2=10.0), _sus(id="b", area_min_m2=10.0)]
    # 20 required ≤ 100 * 0.7 = 70
    check_min_area(specs, footprint_area_m2=100.0, density_factor=0.7)


def test_min_area_fails_when_over_capacity():
    specs = [_sus(id="a", area_min_m2=40.0), _sus(id="b", area_min_m2=40.0)]
    # 80 required > 100 * 0.7 = 70
    with pytest.raises(AreaGateFailure) as exc:
        check_min_area(specs, footprint_area_m2=100.0, density_factor=0.7)
    rec = exc.value.record
    assert rec.code == "DOMAIN_AREA_GATE_FAIL"
    assert rec.data["total_required_area_m2"] == 80.0
    assert rec.data["usable_capacity_m2"] == 70.0
    assert rec.data["required_space_count"] == 2


def test_min_area_counts_required_only():
    """D023: an optional space does not push the sum over capacity."""
    specs = [
        _sus(id="need", area_min_m2=60.0, required=True),
        _sus(id="opt", area_min_m2=60.0, required=False),
    ]
    # required-only = 60 ≤ 70; counting both (120) would fail
    check_min_area(specs, footprint_area_m2=100.0, density_factor=0.7)


def test_min_area_boundary_equal_passes():
    """Σ == capacity is OK (strict > only)."""
    specs = [_sus(area_min_m2=70.0)]
    check_min_area(specs, footprint_area_m2=100.0, density_factor=0.7)


# --- check_min_dim ---


def test_min_dim_passes_when_fits():
    specs = [_sus(min_dimension_m=2.0), _sus(min_dimension_m=2.5)]
    check_min_dim(specs, footprint_bbox_short_side_m=3.0)


def test_min_dim_fails_on_worst_space():
    specs = [_sus(id="ok", min_dimension_m=2.0), _sus(id="wide", min_dimension_m=4.0)]
    with pytest.raises(DimGateFailure) as exc:
        check_min_dim(specs, footprint_bbox_short_side_m=3.0)
    rec = exc.value.record
    assert rec.code == "DOMAIN_DIM_GATE_FAIL"
    assert rec.data["space_id"] == "wide"
    assert rec.data["min_dimension_m"] == 4.0


def test_min_dim_skips_none_spaces():
    """min_dimension_m is optional — None declares no short-side minimum."""
    specs = [_sus(min_dimension_m=None), _sus(min_dimension_m=None)]
    check_min_dim(specs, footprint_bbox_short_side_m=1.0)  # no candidates → OK


def test_min_dim_ignores_optional_spaces():
    """D023: an optional wide space does not trip the gate."""
    specs = [
        _sus(id="need", min_dimension_m=2.0, required=True),
        _sus(id="opt", min_dimension_m=9.0, required=False),
    ]
    check_min_dim(specs, footprint_bbox_short_side_m=3.0)


def test_min_dim_boundary_equal_passes():
    specs = [_sus(min_dimension_m=3.0)]
    check_min_dim(specs, footprint_bbox_short_side_m=3.0)


# --- check_multi_floor_feasibility ---


def test_multi_floor_single_floor_ok():
    check_multi_floor_feasibility(n_floors=1, requires_single_floor=True)


def test_multi_floor_fails_when_required_but_multi():
    with pytest.raises(DomainGateFailure) as exc:
        check_multi_floor_feasibility(n_floors=3, requires_single_floor=True)
    rec = exc.value.record
    assert rec.code == "DOMAIN_MULTI_FLOOR_NOT_SUPPORTED"
    assert rec.data["actual_floor_count"] == 3


def test_multi_floor_allowed_when_not_required():
    """requires_single_floor=False → multi-floor is fine at this gate."""
    check_multi_floor_feasibility(n_floors=3, requires_single_floor=False)


def test_multi_floor_zero_floors_fails_when_single_required():
    """n_floors != 1 includes 0, not just >1."""
    with pytest.raises(DomainGateFailure):
        check_multi_floor_feasibility(n_floors=0, requires_single_floor=True)


# --- check_access_schema (stub) ---


def test_access_schema_is_noop():
    """S05-D4: documented no-op stub — never raises in v1."""
    assert check_access_schema([_sus()]) is None
    assert check_access_schema([]) is None
