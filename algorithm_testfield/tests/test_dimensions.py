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


def test_split_one_meter_interval_keeps_quantum_alignment():
    widths = split_interval(1.00)
    assert widths == [0.35, 0.30, 0.35]
    assert_sums_to(widths, 1.00)
    assert all(is_quantum_aligned(w) for w in widths)


def test_split_4_10_meter_interval_uses_quantized_adjustments():
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


def test_invalid_policy_rejects_unaligned_module_quantum():
    with pytest.raises(ValueError):
        DimensionPolicy(module_quantum=0.033)


def test_invalid_policy_rejects_min_greater_than_target():
    with pytest.raises(ValueError):
        DimensionPolicy(min_atom_size=0.35, target_atom_size=0.30)


def test_invalid_policy_rejects_target_greater_than_max():
    with pytest.raises(ValueError):
        DimensionPolicy(target_atom_size=0.45, max_atom_size=0.40)


def test_deviation_widths_settle_at_edges_not_interior():
    widths = split_interval(4.10)
    # 14 widths total, deviations (0.25) should be at the very ends
    assert widths[0] == 0.25
    assert widths[-1] == 0.25
    assert all(w == 0.30 for w in widths[1:-1])


def test_widths_stay_in_min_max_band():
    policy = DimensionPolicy()
    for length in [0.5, 1.0, 1.5, 2.0, 3.7, 5.5, 8.4, 12.3]:
        widths = split_interval(length, policy)
        if len(widths) == 1 and widths[0] <= policy.min_atom_size:
            continue  # tiny feature exception
        for w in widths:
            assert policy.min_atom_size <= w <= policy.max_atom_size, (length, w)


def test_average_width_near_target_for_typical_lengths():
    policy = DimensionPolicy()
    for length in [3.0, 6.0, 9.0, 12.0]:
        widths = split_interval(length, policy)
        avg = sum(widths) / len(widths)
        assert abs(avg - policy.target_atom_size) < 0.05, (length, avg)
