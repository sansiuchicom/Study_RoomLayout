"""Atomic subdivision from footprint boundary plus planned linework."""

from __future__ import annotations

from dataclasses import dataclass

from shapely.ops import polygonize, unary_union

from .geometry import iter_linework, polygon_boundary_lines, polygon_parts, snap


@dataclass(frozen=True)
class AtomicFace:
    face_id: int
    polygon: object
    source: str = "polygonize"

    @property
    def area(self) -> float:
        return float(self.polygon.area)

    @property
    def centroid(self) -> tuple[float, float]:
        c = self.polygon.centroid
        return (float(c.x), float(c.y))


@dataclass
class SubdivisionResult:
    faces: list[AtomicFace]
    precision: float
    line_count: int
    raw_face_count: int
    dropped_face_count: int


def _quantized_key(poly, precision: float):
    c = poly.representative_point()
    return (
        round(c.y / precision),
        round(c.x / precision),
        round(poly.area / (precision * precision)),
    )


def _clip_linework_to_footprint(linework, footprint):
    clipped = []
    for line in iter_linework(linework):
        clipped.extend(iter_linework([line.intersection(footprint)]))
    return clipped


def build_atomic_faces(
    footprint,
    linework=(),
    *,
    precision: float = 0.001,
    min_face_area: float | None = None,
) -> SubdivisionResult:
    """Build topological atomic faces inside ``footprint``.

    The result is generated from a shared line arrangement:

    * snapped footprint exterior and hole boundaries
    * snapped planner linework clipped to the footprint
    * unary-unioned linework, so intersections are noded before polygonize

    Returned faces are clipped back to the snapped footprint. Hole interiors and
    outside polygons produced by polygonize are dropped.
    """
    min_face_area = precision * precision if min_face_area is None else min_face_area

    footprint_q = snap(footprint, precision)
    footprint_parts = polygon_parts(footprint_q)
    if not footprint_parts:
        return SubdivisionResult(
            faces=[],
            precision=precision,
            line_count=0,
            raw_face_count=0,
            dropped_face_count=0,
        )

    boundary_lines = []
    for part in footprint_parts:
        boundary_lines.extend(polygon_boundary_lines(part))

    clipped_cut_lines = _clip_linework_to_footprint(linework, footprint_q)
    all_lines = [snap(line, precision) for line in boundary_lines + clipped_cut_lines]
    all_lines = [line for line in iter_linework(all_lines) if line.length > precision]

    if not all_lines:
        return SubdivisionResult(
            faces=[],
            precision=precision,
            line_count=0,
            raw_face_count=0,
            dropped_face_count=0,
        )

    noded = unary_union(all_lines)
    raw_faces = list(polygonize(noded))

    face_polys = []
    dropped = 0
    for raw in raw_faces:
        clipped = snap(raw.intersection(footprint_q), precision)
        parts = [p for p in polygon_parts(clipped) if p.area > min_face_area]
        if not parts:
            dropped += 1
            continue
        face_polys.extend(parts)

    face_polys.sort(key=lambda p: _quantized_key(p, precision))
    faces = [
        AtomicFace(face_id=i, polygon=poly)
        for i, poly in enumerate(face_polys)
    ]
    return SubdivisionResult(
        faces=faces,
        precision=precision,
        line_count=len(all_lines),
        raw_face_count=len(raw_faces),
        dropped_face_count=dropped,
    )
