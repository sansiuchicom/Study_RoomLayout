"""RunConfig.__post_init__ value-range validation tests (Step 06 §4.7, S06-D14).

Previously dataclass defaults were trusted; users could construct
RunConfig(atom_size_mm=0) or atom_inclusion_threshold=2.0 without error,
producing confusing geometry failures many stages downstream. This file
locks the value ranges at construction time (D005 fail-loud).
"""
from __future__ import annotations

import pytest

from proto3.config import RunConfig


def test_runconfig_default_values_construct_ok():
    rc = RunConfig()
    assert rc.atom_size_mm == 300
    assert rc.atom_inclusion_threshold == 0.5
    assert rc.min_atom_side_mm == 300
    assert rc.door_min_boundary_mm == 800


# --- atom_size_mm ------------------------------------------------------------------

@pytest.mark.parametrize("bad", [0, -1, -300, 1.5, "300", True, None])
def test_runconfig_atom_size_mm_rejects_invalid(bad):
    with pytest.raises(ValueError, match="atom_size_mm"):
        RunConfig(atom_size_mm=bad)  # type: ignore[arg-type]


def test_runconfig_atom_size_mm_accepts_positive_int():
    RunConfig(atom_size_mm=600)
    RunConfig(atom_size_mm=1)


# --- atom_inclusion_threshold ------------------------------------------------------

@pytest.mark.parametrize("bad", [0, -0.1, 1.5, 2.0, True, False, "0.5", None,
                                  float("nan"), float("inf"), float("-inf")])
def test_runconfig_atom_inclusion_threshold_rejects_invalid(bad):
    with pytest.raises(ValueError, match="atom_inclusion_threshold"):
        RunConfig(atom_inclusion_threshold=bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("good", [0.1, 0.5, 0.99, 1.0, 1])
def test_runconfig_atom_inclusion_threshold_accepts_in_range(good):
    rc = RunConfig(atom_inclusion_threshold=good)
    assert rc.atom_inclusion_threshold == good


# --- min_atom_side_mm (deprecated but still bounded) -------------------------------

@pytest.mark.parametrize("bad", [0, -1, 1.5, "300", True])
def test_runconfig_min_atom_side_mm_rejects_invalid(bad):
    with pytest.raises(ValueError, match="min_atom_side_mm"):
        RunConfig(min_atom_side_mm=bad)  # type: ignore[arg-type]


# --- door_min_boundary_mm ----------------------------------------------------------

@pytest.mark.parametrize("bad", [-1, -800, 1.5, "800", True])
def test_runconfig_door_min_boundary_mm_rejects_invalid(bad):
    with pytest.raises(ValueError, match="door_min_boundary_mm"):
        RunConfig(door_min_boundary_mm=bad)  # type: ignore[arg-type]


def test_runconfig_door_min_boundary_zero_allowed():
    """0 is permitted (might mean 'door capability disabled' in future configs)."""
    RunConfig(door_min_boundary_mm=0)
