"""Atomic subdivision API skeleton.

The full Phase 2 implementation will polygonize footprint boundary plus planned
linework into shared atomic faces. Phase 0 exposes the result shape and a safe
single-face fallback so downstream modules can be wired now.
"""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import polygon_parts, snap


@dataclass(frozen=True)
class AtomicFace:
    face_id: int
    polygon: object


@dataclass
class SubdivisionResult:
    faces: list[AtomicFace]
    precision: float


def build_atomic_faces(
    footprint,
    linework=(),
    *,
    precision: float = 0.001,
) -> SubdivisionResult:
    """Build atomic faces for ``footprint``.

    Phase 0 returns the snapped footprint as a single face when no linework is
    provided. Phase 2 will implement true linework polygonization here.
    """
    if list(linework):
        raise NotImplementedError("Linework polygonization starts in Phase 2.")

    footprint_q = snap(footprint, precision)
    faces = [
        AtomicFace(face_id=i, polygon=part)
        for i, part in enumerate(polygon_parts(footprint_q))
    ]
    return SubdivisionResult(faces=faces, precision=precision)
