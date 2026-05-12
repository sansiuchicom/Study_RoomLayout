"""Assign atomic faces to provisional candidate zones."""

from __future__ import annotations

from dataclasses import dataclass, field

from shapely.ops import unary_union

from .geometry import polygon_parts
from .planner import CandidateZone
from .subdivision import AtomicFace


@dataclass
class Zone:
    zone_id: int
    polygon: object
    face_ids: list[int] = field(default_factory=list)
    cut_history: list[str] = field(default_factory=list)
    family_id: int | None = None
    family_theta: float = 0.0

    def as_dict(self) -> dict:
        return {
            "zone_id": self.zone_id,
            "polygon": self.polygon,
            "face_ids": list(self.face_ids),
            "cut_history": list(self.cut_history),
            "family_id": self.family_id,
            "family_theta": self.family_theta,
        }


def assign_faces_to_candidates(
    faces: list[AtomicFace],
    candidates: list[CandidateZone],
) -> list[Zone]:
    """Assign each atomic face to the candidate with largest area overlap."""
    if not candidates:
        return []

    buckets: dict[int, list[AtomicFace]] = {c.zone_id: [] for c in candidates}
    by_id = {c.zone_id: c for c in candidates}

    for face in faces:
        winner = max(
            candidates,
            key=lambda c: face.polygon.intersection(c.polygon).area,
        )
        buckets[winner.zone_id].append(face)

    zones: list[Zone] = []
    for zone_id, assigned in buckets.items():
        if not assigned:
            continue
        candidate = by_id[zone_id]
        parts = [face.polygon for face in assigned]
        geom = unary_union(parts)
        zone_parts = polygon_parts(geom)
        polygon = zone_parts[0] if len(zone_parts) == 1 else geom
        zones.append(
            Zone(
                zone_id=zone_id,
                polygon=polygon,
                face_ids=[face.face_id for face in assigned],
                cut_history=list(candidate.cut_history),
                family_id=candidate.family_id,
                family_theta=candidate.family_theta,
            )
        )
    zones.sort(key=lambda z: z.zone_id)
    return zones
