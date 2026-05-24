"""Partition validation utilities.

The testfield treats exact coverage as a first-class contract:

* zone union should cover the footprint
* zones should not overlap each other
* zones should not extend outside the footprint
* zone polygons should be valid
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import shapely.geometry as sg
from shapely.validation import explain_validity
from shapely.ops import unary_union

from .geometry import polygon_parts, snap


@dataclass(frozen=True)
class OverlapDetail:
    """Pairwise overlap diagnostic between two zone parts."""

    zone_a: Any
    zone_b: Any
    area: float


@dataclass(frozen=True)
class InvalidDetail:
    """Validity diagnostic for one zone part."""

    zone_id: Any
    reason: str


@dataclass(frozen=True)
class PartitionReport:
    """Numerical validation summary for a footprint partition."""

    zone_count: int
    part_count: int
    empty_count: int
    multipart_count: int
    footprint_area: float
    union_area: float
    sum_zone_area: float
    gap_area: float
    gap_part_count: int
    largest_gap_area: float
    overlap_area: float
    overlap_details: tuple[OverlapDetail, ...]
    outside_area: float
    outside_part_count: int
    largest_outside_area: float
    invalid_count: int
    invalid_details: tuple[InvalidDetail, ...]
    precision: float
    tolerance: float

    @property
    def ok(self) -> bool:
        return (
            self.gap_area <= self.tolerance
            and self.overlap_area <= self.tolerance
            and self.outside_area <= self.tolerance
            and self.invalid_count == 0
            and self.empty_count == 0
            and self.multipart_count == 0
        )

    @property
    def gap_ratio(self) -> float:
        return _ratio(self.gap_area, self.footprint_area)

    @property
    def overlap_ratio(self) -> float:
        return _ratio(self.overlap_area, self.footprint_area)

    @property
    def outside_ratio(self) -> float:
        return _ratio(self.outside_area, self.footprint_area)

    @property
    def failed_checks(self) -> tuple[str, ...]:
        out = []
        if self.gap_area > self.tolerance:
            out.append("gap")
        if self.overlap_area > self.tolerance:
            out.append("overlap")
        if self.outside_area > self.tolerance:
            out.append("outside")
        if self.invalid_count:
            out.append("invalid")
        if self.empty_count:
            out.append("empty")
        if self.multipart_count:
            out.append("multipart")
        return tuple(out)

    def short_status(self) -> str:
        return "ok" if self.ok else ",".join(self.failed_checks)


def _zone_polygon(zone):
    if isinstance(zone, dict):
        return zone["polygon"]
    return getattr(zone, "polygon", zone)


def _zone_id(zone, fallback: int):
    if isinstance(zone, dict):
        return zone.get("zone_id", fallback)
    return getattr(zone, "zone_id", fallback)


def _ratio(value: float, total: float) -> float:
    return 0.0 if total <= 0.0 else value / total


def _largest_area(parts) -> float:
    return float(max((p.area for p in parts), default=0.0))


def _safe_snap(geom, precision: float):
    try:
        return snap(geom, precision)
    except Exception:
        return geom


def validate_partition(
    footprint,
    zones,
    *,
    precision: float = 0.001,
    tolerance: float = 1e-6,
) -> PartitionReport:
    """Validate that ``zones`` form a disjoint cover of ``footprint``."""
    zones = list(zones)
    footprint_q = _safe_snap(footprint, precision)
    zone_entries = []
    empty_count = 0
    multipart_count = 0
    invalid_details = []

    for idx, zone in enumerate(zones):
        zid = _zone_id(zone, idx)
        poly = _safe_snap(_zone_polygon(zone), precision)
        if poly.is_empty:
            empty_count += 1
            continue

        parts = polygon_parts(poly)
        if not parts:
            empty_count += 1
            continue
        if len(parts) > 1:
            multipart_count += 1

        for part in parts:
            if not part.is_valid:
                invalid_details.append(
                    InvalidDetail(zone_id=zid, reason=explain_validity(part))
                )
            zone_entries.append((zid, part))

    zone_parts = [part for _, part in zone_entries]

    if zone_parts:
        union = unary_union(zone_parts)
        union_q = _safe_snap(union, precision)
    else:
        union_q = sg.GeometryCollection()

    sum_area = float(sum(p.area for p in zone_parts))
    union_area = float(union_q.area)
    gap = footprint_q.difference(union_q)
    outside = union_q.difference(footprint_q)
    gap_parts = polygon_parts(gap)
    outside_parts = polygon_parts(outside)
    gap_area = float(gap.area)
    outside_area = float(outside.area)
    overlap_area = max(0.0, sum_area - union_area)
    overlap_details = []
    for i, (za, pa) in enumerate(zone_entries):
        for zb, pb in zone_entries[i + 1:]:
            area = float(pa.intersection(pb).area)
            if area > tolerance:
                overlap_details.append(OverlapDetail(za, zb, area))

    return PartitionReport(
        zone_count=len(zones),
        part_count=len(zone_parts),
        empty_count=empty_count,
        multipart_count=multipart_count,
        footprint_area=float(footprint_q.area),
        union_area=union_area,
        sum_zone_area=sum_area,
        gap_area=gap_area,
        gap_part_count=len(gap_parts),
        largest_gap_area=_largest_area(gap_parts),
        overlap_area=overlap_area,
        overlap_details=tuple(overlap_details),
        outside_area=outside_area,
        outside_part_count=len(outside_parts),
        largest_outside_area=_largest_area(outside_parts),
        invalid_count=len(invalid_details),
        invalid_details=tuple(invalid_details),
        precision=precision,
        tolerance=tolerance,
    )
