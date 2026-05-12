import math

import pytest

from celllayout_tf.dimensions import (
    DimensionPolicy,
    interval_positions,
    is_quantum_aligned,
    split_interval,
)


def assert_sums_to(widths, length):
    assert math.isclose(sum(widths), length, abs_tol=1e-9)


def test_default_policy_values_are_consistent():
    policy = DimensionPolicy()

    assert policy.geometry_snap == 0.01
    assert policy.module_quantum == 0.05
    assert policy.target_atom_size == 0.30
    assert policy.min_atom_size == 0.20
    assert policy.max_atom_size == 0.40


def test_split_one_meter_interval_without_thirds():
    widths = split_interval(1.00)

    assert widths == [0.35, 0.30, 0.35]
    assert_sums_to(widths, 1.00)
    assert all(is_quantum_aligned(w) for w in widths)


def test_split_four_point_one_meters_uses_quantized_adjustments():
    widths = split_interval(4.10)

    assert_sums_to(widths, 4.10)
    assert len(widths) == 14
    assert widths.count(0.25) == 2
    assert widths.count(0.30) == 12
    assert all(is_quantum_aligned(w) for w in widths)


def test_small_feature_interval_is_preserved_not_dropped():
    widths = split_interval(0.18)

    assert widths == [0.18]
    assert_sums_to(widths, 0.18)


def test_non_quantum_interval_keeps_exact_length_with_minimal_adjustment():
    widths = split_interval(1.03)

    assert_sums_to(widths, 1.03)
    assert len(widths) == 3
    assert sum(1 for w in widths if is_quantum_aligned(w)) == 2
    assert all(0.20 <= w <= 0.40 for w in widths)


def test_positions_end_at_snapped_interval_length():
    widths = split_interval(2.05)
    positions = interval_positions(0.0, widths)

    assert positions[0] == 0.0
    assert positions[-1] == 2.05
    assert_sums_to(widths, 2.05)
    assert all(round(p, 2) == p for p in positions)


def test_invalid_policy_rejects_unaligned_values():
    with pytest.raises(ValueError):
        DimensionPolicy(module_quantum=0.033)
