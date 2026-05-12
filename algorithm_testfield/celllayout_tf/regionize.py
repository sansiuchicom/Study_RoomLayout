"""Atom-based regionizer.

Cut selection follows the reference algorithm at
``algorithm/celllayout/zoning.py``: hierarchical priority T1a → T1b → T2 → T3,
deterministic with balance/aspect gates and no scoring function.

Two adaptations for atom alignment (because our region geometry is the union
of constituent atom polygons, not the polygon-cut sub-piece):

1. Cut candidate vertices are taken from the raw piece polygon (no
   simplification). Atom anchors already include every raw polygon vertex,
   so T1a/T1b cut lines coincide with atom column/row boundaries.

2. T3 ``axis_mid`` candidates are sampled from the local-frame atom edge
   positions inside the [0.3, 0.7] bbox fraction range — not from evenly
   spaced fractions — so T3 cuts also align with atom edges.

Atoms are assigned to sub-pieces by local-frame centroid containment. The
resulting region polygon is the union of the assigned atom polygons in the
global frame, so the region boundary follows atom edges everywhere except
where a T2 (oblique reflex_pair) cut runs through atom interiors.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import cos, degrees, sin

import numpy as np
import shapely.affinity as sa
import shapely.geometry as sg
from shapely.geometry.polygon import orient as _orient
from shapely.ops import split, unary_union

from .atomize import Atom, atomize
from .dimensions import DimensionPolicy
from .schema import ShapeInput, ShapePart
from .territory import KIND_CURVED, resolve_territories


# Reference parameters --------------------------------------------------------
MIN_AREA = 3.0          # m² minimum final region area
MARGIN = 0.5            # m vertex too close to bbox edge is skipped
MIN_CUT_LEN = 1.0       # m oblique reflex-pair line minimum internal length
MAX_ASPECT = 4.0        # final region MRR aspect cap
BAL_MIN = 0.15          # T1/T2 balance threshold (small piece ≥ 14% of large)
TIE_DECIMALS = 6        # balance tie-break precision (float drift tolerance)


@dataclass(frozen=True)
class Region:
    region_id: int
    shape: ShapePart
    atom_ids: tuple[int, ...]
    part_id: int
    piece_id: int
    theta: float
    cut_history: tuple[str, ...]


@dataclass(frozen=True)
class _PartitionContext:
    structural: dict
    atom_xs: tuple[float, ...]
    atom_ys: tuple[float, ...]


def _collect_group_grid(
    atoms,
) -> dict[float, tuple[tuple[float, ...], tuple[float, ...]]]:
    """Return ``{theta_key: (xs, ys)}`` of atom-edge coords per theta group.

    Coords are in each group's local frame (atom polygons rotated by
    ``-theta``). The pool is the union of every atom polygon's exterior
    vertex coord, so it captures both piece-vertex anchors (structural) and
    the ``split_interval``-generated subdivisions baked into atom edges.
    Slab cut candidates are drawn from this pool.
    """
    xs_by_theta: dict[float, set[float]] = defaultdict(set)
    ys_by_theta: dict[float, set[float]] = defaultdict(set)
    for a in atoms:
        key = round(a.theta, 9)
        poly = _rotate_geom(_to_shapely(a.shape), -a.theta)
        for x, y in list(poly.exterior.coords)[:-1]:
            xs_by_theta[key].add(round(x, 9))
            ys_by_theta[key].add(round(y, 9))
    return {
        key: (tuple(sorted(xs_by_theta[key])), tuple(sorted(ys_by_theta[key])))
        for key in xs_by_theta
    }


def _lattice_cuts(
    atoms_with_local,
    xs_pool: tuple[float, ...],
    ys_pool: tuple[float, ...],
):
    """Yield slab cut candidates over the theta-group grid pool.

    Each ``aw`` is ``(atom, local_centroid)``. For every coord in the pool
    that splits the centroids into two non-empty groups, a candidate
    ``("axis_x"|"axis_y", coord, left_atoms, right_atoms)`` is emitted.
    Centroid-based assignment is unambiguous because atom polygons align
    to grid edges, so a pool coord cannot fall through any atom's centroid.
    """
    cuts = []
    for x in xs_pool:
        left = [aw for aw in atoms_with_local if aw[1][0] < x]
        right = [aw for aw in atoms_with_local if aw[1][0] > x]
        if left and right:
            cuts.append(("axis_x", float(x), left, right))
    for y in ys_pool:
        below = [aw for aw in atoms_with_local if aw[1][1] < y]
        above = [aw for aw in atoms_with_local if aw[1][1] > y]
        if below and above:
            cuts.append(("axis_y", float(y), below, above))
    return cuts


def regionize(
    shape: ShapeInput,
    atoms: tuple[Atom, ...] | None = None,
    policy: DimensionPolicy | None = None,
    *,
    target_area: float = 6.0,
) -> tuple[Region, ...]:
    if atoms is None:
        atoms = atomize(shape, policy)
    if not atoms:
        return ()

    territories = resolve_territories(shape)
    atoms_by_pp: dict[tuple[int, int], list[Atom]] = defaultdict(list)
    for a in atoms:
        atoms_by_pp[(a.part_id, a.piece_id)].append(a)

    regions: list[Region] = []
    next_id = [0]

    for terr in territories:
        eff_theta = 0.0 if terr.kind == KIND_CURVED else terr.theta
        for piece_idx, piece in enumerate(terr.pieces):
            piece_poly = _to_shapely(piece)
            piece_atoms = atoms_by_pp.get((terr.part_id, piece_idx), [])
            if piece_poly.area < 1e-9 or not piece_atoms:
                continue

            local_poly = _rotate_geom(piece_poly, -eff_theta)
            atoms_with_local = [
                (a, _rotate_point(a.centroid, -eff_theta)) for a in piece_atoms
            ]
            local_atom_polys = [
                _rotate_geom(_to_shapely(a.shape), -eff_theta) for a in piece_atoms
            ]
            ctx = _PartitionContext(
                structural=_structural_coords(local_poly),
                atom_xs=_collect_atom_edge_positions(local_atom_polys, axis="x"),
                atom_ys=_collect_atom_edge_positions(local_atom_polys, axis="y"),
            )

            k = max(1, round(piece_poly.area / target_area))
            groups = _recurse_partition(local_poly, atoms_with_local, k, ctx)

            for atom_list, cut_history in groups:
                actual_atoms = [aw[0] for aw in atom_list]
                if not actual_atoms:
                    continue
                shape_part = _union_atoms_to_shape_part(actual_atoms)
                if shape_part is None:
                    continue
                regions.append(
                    Region(
                        region_id=next_id[0],
                        shape=shape_part,
                        atom_ids=tuple(a.atom_id for a in actual_atoms),
                        part_id=terr.part_id,
                        piece_id=piece_idx,
                        theta=eff_theta,
                        cut_history=tuple(cut_history),
                    )
                )
                next_id[0] += 1

    return tuple(regions)


# Recursive partition ---------------------------------------------------------


def _recurse_partition(local_poly, atoms_with_local, k, ctx):
    if k <= 1 or local_poly.area < MIN_AREA * 2:
        return [(atoms_with_local, [])]

    sel = _select_cut(local_poly, k, ctx)
    if sel is None:
        return [(atoms_with_local, [])]

    label, _lines, pieces, _b = sel
    sub_atoms_lists: list[list] = [[] for _ in pieces]
    for aw in atoms_with_local:
        pt = sg.Point(aw[1])
        assigned = False
        for i, sub_poly in enumerate(pieces):
            if sub_poly.contains(pt):
                sub_atoms_lists[i].append(aw)
                assigned = True
                break
        if not assigned:
            best_i = min(
                range(len(pieces)),
                key=lambda i: pieces[i].distance(pt),
            )
            sub_atoms_lists[best_i].append(aw)

    result = []
    for sub_poly, sub_atoms, sub_k in zip(
        pieces, sub_atoms_lists, _allocate_k(pieces, k),
    ):
        for group_atoms, group_history in _recurse_partition(
            sub_poly, sub_atoms, sub_k, ctx,
        ):
            result.append((group_atoms, [label] + group_history))
    return result


# Cut selection (mirrors reference) ------------------------------------------


def _select_cut(local_poly, k_total, ctx):
    for label, gen, prefer_short, bmin in (
        ("cross_cut", lambda: _cross_cut_pairs(local_poly), False, BAL_MIN),
        ("vertex_aligned", lambda: ([ln] for ln in
                                     _vertex_aligned_lines(local_poly, ctx.structural)),
                                                                 False, BAL_MIN),
        ("reflex_pair", lambda: _reflex_pair_lines(local_poly), True, BAL_MIN),
        ("axis_mid", lambda: _axis_mid_lines_atom_aligned(local_poly, ctx),
                                                                 False, 0.0),
    ):
        cands = ((label, lines) for lines in gen())
        r = _best_cut(cands, local_poly, bmin, k_total, prefer_short)
        if r is not None:
            return r
    return None


def _vertex_coords_raw(poly):
    coords = list(poly.exterior.coords)[:-1]
    for h in poly.interiors:
        coords.extend(list(h.coords)[:-1])
    return coords


def _reflex_vertices(poly):
    if not poly.exterior.is_ccw:
        poly = sg.Polygon(
            list(poly.exterior.coords)[::-1],
            [list(h.coords)[::-1] for h in poly.interiors],
        )
    out = []

    def scan(coords):
        n = len(coords)
        for i in range(n):
            a, b, c = (np.asarray(coords[(i + j - 1) % n]) for j in range(3))
            v1, v2 = b - a, c - b
            if v1[0] * v2[1] - v1[1] * v2[0] < -1e-6:
                out.append(tuple(b))

    scan(list(poly.exterior.coords)[:-1])
    for h in poly.interiors:
        c = list(h.coords)[:-1]
        scan(c[::-1] if h.is_ccw else c)
    return out


def _structural_coords(poly):
    rfx = _reflex_vertices(poly)
    return {
        "xs": {round(x, 6) for x, _ in rfx},
        "ys": {round(y, 6) for _, y in rfx},
    }


def _vertex_aligned_lines(poly, structural=None):
    minx, miny, maxx, maxy = poly.bounds
    coords = _vertex_coords_raw(poly)
    if structural:
        coords += [(x, miny) for x in structural["xs"]]
        coords += [(minx, y) for y in structural["ys"]]
    cuts, sx, sy = [], set(), set()
    for x, y in coords:
        kx, ky = round(x, 2), round(y, 2)
        if minx + MARGIN < x < maxx - MARGIN and kx not in sx:
            sx.add(kx)
            cuts.append(sg.LineString([(x, miny - 1), (x, maxy + 1)]))
        if miny + MARGIN < y < maxy - MARGIN and ky not in sy:
            sy.add(ky)
            cuts.append(sg.LineString([(minx - 1, y), (maxx + 1, y)]))
    return cuts


def _cross_cut_pairs(poly):
    minx, miny, maxx, maxy = poly.bounds
    pairs, seen = [], set()
    for x, y in _vertex_coords_raw(poly):
        k = (round(x, 2), round(y, 2))
        if (
            k in seen
            or not (minx + MARGIN < x < maxx - MARGIN)
            or not (miny + MARGIN < y < maxy - MARGIN)
        ):
            continue
        seen.add(k)
        pairs.append(
            [
                sg.LineString([(x, miny - 1), (x, maxy + 1)]),
                sg.LineString([(minx - 1, y), (maxx + 1, y)]),
            ]
        )
    return pairs


def _reflex_pair_lines(poly):
    rfx = _reflex_vertices(poly)
    out = []
    for i in range(len(rfx)):
        for j in range(i + 1, len(rfx)):
            line = sg.LineString([rfx[i], rfx[j]])
            inter = line.intersection(poly)
            if not (hasattr(inter, "length") and inter.length >= MIN_CUT_LEN):
                continue
            (x1, y1), (x2, y2) = list(line.coords)[0], list(line.coords)[-1]
            if abs(x1 - x2) < 1e-3 or abs(y1 - y2) < 1e-3:
                continue
            out.append([line])
    return out


def _axis_mid_lines_atom_aligned(poly, ctx):
    """T3 fallback at atom-aligned positions inside [0.3, 0.7] bbox fraction."""
    minx, miny, maxx, maxy = poly.bounds
    W = maxx - minx
    H = maxy - miny
    if W <= 0 or H <= 0:
        return []
    x_lo, x_hi = minx + 0.3 * W, minx + 0.7 * W
    y_lo, y_hi = miny + 0.3 * H, miny + 0.7 * H

    cuts = []
    for x in ctx.atom_xs:
        if x_lo <= x <= x_hi:
            cuts.append([sg.LineString([(x, miny - 1), (x, maxy + 1)])])
    for y in ctx.atom_ys:
        if y_lo <= y <= y_hi:
            cuts.append([sg.LineString([(minx - 1, y), (maxx + 1, y)])])
    return cuts


# Split / validity ------------------------------------------------------------


def _split_pieces(poly, lines):
    pieces = [poly]
    for line in lines:
        nxt = []
        for p in pieces:
            try:
                r = split(p, line)
                parts = list(r.geoms) if hasattr(r, "geoms") else [r]
                nxt.extend(
                    q for q in parts if isinstance(q, sg.Polygon) and q.area > 0.01
                )
            except Exception:
                nxt.append(p)
        pieces = nxt or pieces
    if len(pieces) < 2:
        return None
    return sorted(pieces, key=lambda p: -p.area)


def _piece_aspect(p):
    if p.is_empty or p.area < 1e-6:
        return 99.0
    try:
        c = list(p.minimum_rotated_rectangle.exterior.coords)
        e1 = float(np.hypot(c[1][0] - c[0][0], c[1][1] - c[0][1]))
        e2 = float(np.hypot(c[2][0] - c[1][0], c[2][1] - c[1][1]))
        return max(e1, e2) / max(min(e1, e2), 1e-6)
    except Exception:
        return 99.0


def _balance(pieces):
    a = [p.area for p in pieces]
    return min(a) / max(a)


def _allocate_k(pieces, k_total):
    total = sum(p.area for p in pieces)
    out, acc = [], 0
    for i, p in enumerate(pieces):
        if i == len(pieces) - 1:
            kk = max(1, k_total - acc)
        else:
            kk = max(1, round(k_total * p.area / total))
            acc += kk
        out.append(kk)
    return out


def _aspect_ok(pieces, k_total):
    if k_total is None:
        return all(_piece_aspect(p) <= MAX_ASPECT for p in pieces)
    for p, kp in zip(pieces, _allocate_k(pieces, k_total)):
        if (kp <= 1 or p.area < MIN_AREA * 2) and _piece_aspect(p) > MAX_ASPECT:
            return False
    return True


def _best_cut(candidates, poly, bal_min, k_total, prefer_short=False):
    valid = []
    for label, lines in candidates:
        pieces = _split_pieces(poly, lines)
        if pieces is None or min(p.area for p in pieces) < MIN_AREA:
            continue
        b = _balance(pieces)
        if b < bal_min or not _aspect_ok(pieces, k_total):
            continue
        valid.append((label, lines, pieces, b))
    if not valid:
        return None
    if prefer_short:
        valid.sort(
            key=lambda v: (
                -round(v[3], TIE_DECIMALS),
                sum(line.length for line in v[1]),
            )
        )
    else:
        valid.sort(
            key=lambda v: (
                -round(v[3], TIE_DECIMALS),
                max(_piece_aspect(p) for p in v[2]),
            )
        )
    return valid[0]


# Geometry helpers ------------------------------------------------------------


def _to_shapely(part: ShapePart) -> sg.Polygon:
    return sg.Polygon(part.exterior, [list(h) for h in part.holes])


def _rotate_geom(geom, theta_rad):
    if abs(theta_rad) < 1e-12:
        return geom
    return sa.rotate(geom, degrees(theta_rad), origin=(0, 0))


def _rotate_point(pt, theta_rad):
    if abs(theta_rad) < 1e-12:
        return pt
    c, s = cos(theta_rad), sin(theta_rad)
    x, y = pt
    return (x * c - y * s, x * s + y * c)


def _collect_atom_edge_positions(local_polys, axis="x"):
    positions: set[float] = set()
    for poly in local_polys:
        if poly.is_empty:
            continue
        for x, y in list(poly.exterior.coords)[:-1]:
            positions.add(round(x if axis == "x" else y, 6))
    return tuple(sorted(positions))


def _union_atoms_to_shape_part(atoms) -> ShapePart | None:
    polys = [_to_shapely(a.shape) for a in atoms]
    if not polys:
        return None
    merged = unary_union(polys)
    if merged.is_empty:
        return None
    if isinstance(merged, sg.MultiPolygon):
        merged = max(merged.geoms, key=lambda p: p.area)
    if not isinstance(merged, sg.Polygon):
        return None
    merged = _orient(merged, sign=1.0)
    ext = tuple(tuple(map(float, p)) for p in list(merged.exterior.coords)[:-1])
    holes = tuple(
        tuple(tuple(map(float, p)) for p in list(r.coords)[:-1])
        for r in merged.interiors
    )
    return ShapePart(exterior=ext, holes=holes)
