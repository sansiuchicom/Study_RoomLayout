"""Overlap resolution: turn a floor's ``ShapePart`` list into disjoint territories.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.7 + S03-D13.

Ported from Cell ``territory.py`` and adapted to the new schema: the stage
takes a ``FloorShape`` (S03-D13) and operates on ``floor.parts`` — Cell's
single-floor ``ShapeInput.parts`` maps 1:1 to one ``FloorShape``'s parts.

Rule: when two parts overlap, count each part's exterior vertices that are
strictly inside the other. The part with FEWER intruding vertices is the
host and keeps its full polygon; the other loses the overlap zone.

Tiebreakers (in order):
    1. axis-aligned > rotated > curved
    2. larger area
    3. earlier in the parts list

Internal per S03-D6 — not re-exported from the public surface. `atomize`
consumes `resolve_territories`, `collect_cross_theta_contact_coords`, and
`KIND_CURVED`.
"""

from collections import defaultdict
from dataclasses import dataclass
from math import atan2, degrees, hypot, pi

import shapely.affinity as sa
import shapely.geometry as sg

from room_layout.schema import FloorShape, ShapePart
from room_layout.stages._helpers import (
    from_shapely,
    part_theta,
    polygon_parts,
    to_shapely,
)

KIND_AXIS_ALIGNED = "axis_aligned"
KIND_ROTATED = "rotated"
KIND_CURVED = "curved"
_KIND_ORDER = {KIND_AXIS_ALIGNED: 0, KIND_ROTATED: 1, KIND_CURVED: 2}


@dataclass(frozen=True)
class Territory:
    part_id: int
    theta: float
    kind: str
    pieces: tuple[ShapePart, ...]

    @property
    def is_empty(self) -> bool:
        return len(self.pieces) == 0


def part_kind(part: ShapePart) -> str:
    """Classify a part by edge-angle consistency."""
    theta = part_theta(part)
    verts = part.exterior
    n = len(verts)
    aligned = 0
    total = 0
    eps_angle = 1e-3
    for i in range(n):
        x0, y0 = verts[i]
        x1, y1 = verts[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        if hypot(dx, dy) < 1e-9:
            continue
        edge_theta = atan2(dy, dx) % (pi / 2)
        if _angle_diff_mod_half_pi(edge_theta, theta) < eps_angle:
            aligned += 1
        total += 1
    if total == 0 or aligned / total < 0.95:
        return KIND_CURVED
    if abs(theta) < eps_angle or abs(theta - pi / 2) < eps_angle:
        return KIND_AXIS_ALIGNED
    return KIND_ROTATED


def resolve_territories(floor: FloorShape) -> tuple[Territory, ...]:
    """Return one ``Territory`` per floor part, with overlap zones removed."""
    parts = floor.parts
    polys = [to_shapely(p) for p in parts]
    kinds = [part_kind(p) for p in parts]
    thetas = [part_theta(p) for p in parts]

    territories = list(polys)

    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            if not polys[i].intersects(polys[j]):
                continue
            inter = polys[i].intersection(polys[j])
            if inter.is_empty or inter.area < 1e-9:
                continue
            winner = _pair_winner(i, j, parts, polys, kinds)
            loser = j if winner == i else i
            territories[loser] = territories[loser].difference(polys[winner])

    out = []
    for idx, geom in enumerate(territories):
        pieces = tuple(from_shapely(p) for p in polygon_parts(geom))
        out.append(
            Territory(
                part_id=idx,
                theta=thetas[idx],
                kind=kinds[idx],
                pieces=pieces,
            )
        )
    return tuple(out)


def collect_cross_theta_contact_coords(
    floor: FloorShape,
    territories: tuple[Territory, ...],
) -> tuple[dict[float, set[float]], dict[float, set[float]]]:
    """Boundary-crossing points between every pair of parts, per theta group.

    For every pair of parts (regardless of theta), find where their ORIGINAL
    polygon boundaries cross or touch, and project each crossing point into
    both parts' local frames. These points are treated as "structural
    vertices" alongside each piece's own polygon vertices.

    Why original (not post-clip territory pieces): shapely's
    ``polygon.difference`` introduces ~1e-6 FP drift, which can drop
    collinear shared edges from boundary intersection. Originals stay clean.

    Same-theta pairs are NOT skipped — they catch crossings that aren't
    polygon vertices of either piece. Example: case 28 disk crosses
    vert_rect's right edge at (4, 8), which is on vert_rect's edge but not
    a vert_rect corner. Without this, vert_rect would never get y=8 as a
    structural cut.

    Curved territories receive no projection coords (their many circumference
    samples carry no axial meaning) but still contribute endpoints to
    non-curved partners.

    Returns ``(xs_by_theta, ys_by_theta)`` as sets keyed by
    ``round(eff_theta, 9)``.
    """
    parts_meta = []
    for terr in territories:
        eff_theta = 0.0 if terr.kind == KIND_CURVED else terr.theta
        key = round(eff_theta, 9)
        is_curved = terr.kind == KIND_CURVED
        part = floor.parts[terr.part_id]
        gp = sg.Polygon(part.exterior, [list(h) for h in part.holes])
        if not gp.is_empty:
            parts_meta.append((key, eff_theta, is_curved, gp))

    xs: dict[float, set[float]] = defaultdict(set)
    ys: dict[float, set[float]] = defaultdict(set)
    for i in range(len(parts_meta)):
        ka, eta_a, curved_a, pa = parts_meta[i]
        for j in range(i + 1, len(parts_meta)):
            kb, eta_b, curved_b, pb = parts_meta[j]
            shared = pa.boundary.intersection(pb.boundary)
            if shared.is_empty:
                continue
            for px, py in _shared_boundary_endpoints(shared):
                if not curved_a:
                    ax, ay = _global_to_local(px, py, eta_a)
                    xs[ka].add(round(ax, 9))
                    ys[ka].add(round(ay, 9))
                if not curved_b:
                    bx, by_ = _global_to_local(px, py, eta_b)
                    xs[kb].add(round(bx, 9))
                    ys[kb].add(round(by_, 9))
    return xs, ys


def _shared_boundary_endpoints(geom) -> list[tuple[float, float]]:
    if geom.is_empty:
        return []
    t = geom.geom_type
    if t == "Point":
        return [(float(geom.x), float(geom.y))]
    if t == "MultiPoint":
        return [(float(p.x), float(p.y)) for p in geom.geoms]
    if t == "LineString":
        cs = list(geom.coords)
        return [tuple(map(float, cs[0])), tuple(map(float, cs[-1]))]
    if t == "MultiLineString":
        out: list[tuple[float, float]] = []
        for ls in geom.geoms:
            cs = list(ls.coords)
            out.append(tuple(map(float, cs[0])))
            out.append(tuple(map(float, cs[-1])))
        return out
    if t == "GeometryCollection":
        out = []
        for g in geom.geoms:
            out.extend(_shared_boundary_endpoints(g))
        return out
    return []


def _global_to_local(x: float, y: float, eff_theta: float) -> tuple[float, float]:
    """Rotate ``(x, y)`` clockwise by ``eff_theta`` around the origin."""
    if abs(eff_theta) < 1e-12:
        return (float(x), float(y))
    p = sa.rotate(sg.Point(x, y), -degrees(eff_theta), origin=(0, 0))
    return (float(p.x), float(p.y))


def _pair_winner(
    i: int,
    j: int,
    parts: tuple[ShapePart, ...],
    polys: list,
    kinds: list[str],
) -> int:
    count_i_in_j = _count_exterior_vertices_inside(parts[i], polys[j])
    count_j_in_i = _count_exterior_vertices_inside(parts[j], polys[i])

    if count_i_in_j < count_j_in_i:
        return i
    if count_i_in_j > count_j_in_i:
        return j

    rank_i = _KIND_ORDER[kinds[i]]
    rank_j = _KIND_ORDER[kinds[j]]
    if rank_i < rank_j:
        return i
    if rank_i > rank_j:
        return j

    if polys[i].area > polys[j].area:
        return i
    if polys[i].area < polys[j].area:
        return j

    return i


def _count_exterior_vertices_inside(part: ShapePart, host_polygon) -> int:
    count = 0
    for x, y in part.exterior:
        if host_polygon.contains(sg.Point(x, y)):
            count += 1
    return count


def _angle_diff_mod_half_pi(a: float, b: float) -> float:
    d = abs((a - b) % (pi / 2))
    return min(d, pi / 2 - d)
