"""Atomic subdivision testfield for RoomLayoutCell.

This package is intentionally separate from the legacy ``celllayout`` package
copied into ``algorithm_testfield``. New topology-safe experiments should live
here first, then be ported back only after the invariants are proven.
"""

from .validation import PartitionReport, validate_partition
from .zoning import zone_footprint

__all__ = [
    "PartitionReport",
    "validate_partition",
    "zone_footprint",
]
