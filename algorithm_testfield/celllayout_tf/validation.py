"""Partition validation utilities.

The testfield treats exact coverage as a first-class contract:

* zone union should cover the footprint
* zones should not overlap each other
* zones should not extend outside the footprint
* zone polygons should be valid
"""

from __future__ import annotations

from dataclasses import dataclass

from shapely.ops import unary_union

from .geometry import polygon_parts, snap


@dataclass(frozen=True)
class PartitionReport:
    """Numerical validation summary for a footprint partition."""

    zone_count: int
    footprint_area: float
    union_area: float
    sum_zone_area: float
    gap_area: float
    overlap_area: float
    outside_area: float
    invalid_count: int
    tolerance: float

    @property
    def ok(self) -> bool:
        return (
            self.gap_area <= self.tolerance
            and self.overlap_area <= self.tolerance
            and self.outside_area <= self.tolerance
            and self.invalid_count == 0
        )


def _zone_polygon(zone):
    if isinstance(zone, dict):
        return zone["polygon"]
    return getattr(zone, "polygon", zone)


def validate_partition(
    footprint,
    zones,
    *,
    precision: float = 0.001,
    tolerance: float = 1e-6,
) -> PartitionReport:
    """Validate that ``zones`` form a disjoint cover of ``footprint``."""
    footprint_q = snap(footprint, precision)
    polys = [snap(_zone_polygon(z), precision) for z in zones]
    polys = [p for p in polys if not p.is_empty]
    zone_parts = [part for poly in polys for part in polygon_parts(poly)]

    if zone_parts:
        union = unary_union(zone_parts)
        union_q = snap(union, precision)
    else:
        union_q = footprint_q.intersection(footprint_q.buffer(0).boundary)

    sum_area = float(sum(p.area for p in zone_parts))
    union_area = float(union_q.area)
    gap_area = float(footprint_q.difference(union_q).area)
    outside_area = float(union_q.difference(footprint_q).area)
    overlap_area = max(0.0, sum_area - union_area)
    invalid_count = sum(0 if p.is_valid else 1 for p in zone_parts)

    return PartitionReport(
        zone_count=len(zone_parts),
        footprint_area=float(footprint_q.area),
        union_area=union_area,
        sum_zone_area=sum_area,
        gap_area=gap_area,
        overlap_area=overlap_area,
        outside_area=outside_area,
        invalid_count=invalid_count,
        tolerance=tolerance,
    )
