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

import bisect
from collections import defaultdict
from dataclasses import dataclass
from math import degrees

import shapely.affinity as sa
import shapely.geometry as sg
from shapely.geometry.polygon import orient as _orient
from shapely.ops import unary_union

from .atomize import Atom, atomize
from .dimensions import DimensionPolicy
from .schema import ShapeInput, ShapePart
from .territory import KIND_CURVED, resolve_territories


# Reference parameters --------------------------------------------------------
MIN_AREA = 3.0          # m² minimum final region area
MAX_ASPECT = 4.0        # final region local-bbox aspect cap
BAL_MIN = 0.15          # balance threshold (smaller piece ≥ 15% of larger)
TIE_DECIMALS = 6        # balance tie-break precision (float drift tolerance)


@dataclass(frozen=True)
class Region:
    region_id: int
    shape: ShapePart
    atom_ids: tuple[int, ...]
    part_id: int
    piece_id: int
    theta: float
    cut_history: tuple[tuple[str, float], ...]


@dataclass
class _PropagationState:
    """Per-theta-group seen-coord set for cross-cell cut alignment.

    When a candidate's coord is already in ``seen``, the lattice selector
    ranks it ahead of unseen candidates of equal balance — so the second
    cell to subdivide tends to reuse cut coords picked by the first.
    """

    seen_xs: set[float]
    seen_ys: set[float]

    def has(self, label: str, coord: float) -> bool:
        return coord in (self.seen_xs if label == "axis_x" else self.seen_ys)

    def add(self, label: str, coord: float) -> None:
        (self.seen_xs if label == "axis_x" else self.seen_ys).add(coord)


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


def _collect_structural_coords(
    territories,
) -> dict[float, tuple[tuple[float, ...], tuple[float, ...]]]:
    """Return ``{theta_key: (xs, ys)}`` of territory-piece vertex coords.

    Coords are in each non-curved theta group's local frame. Drives Pass A's
    structural pre-cut: cutting at these coords coincides with reflex
    vertices, hole reflexes, and cross-part edges that fall inside another
    piece. Curved territories (many circumference vertices, no meaningful
    structural axis) are skipped.
    """
    xs_by_theta: dict[float, set[float]] = defaultdict(set)
    ys_by_theta: dict[float, set[float]] = defaultdict(set)
    for terr in territories:
        if terr.kind == KIND_CURVED:
            continue
        eff_theta = terr.theta
        key = round(eff_theta, 9)
        for piece in terr.pieces:
            poly = _rotate_geom(_to_shapely(piece), -eff_theta)
            if poly.is_empty:
                continue
            for ring in [poly.exterior, *poly.interiors]:
                for x, y in list(ring.coords)[:-1]:
                    xs_by_theta[key].add(round(x, 9))
                    ys_by_theta[key].add(round(y, 9))
    return {
        key: (tuple(sorted(xs_by_theta[key])), tuple(sorted(ys_by_theta[key])))
        for key in xs_by_theta
    }


def _structural_partition(
    atoms_with_local,
    interior_xs: tuple[float, ...],
    interior_ys: tuple[float, ...],
):
    """Pass A pre-cut: bin atoms into structural cells.

    Atoms are binned by local centroid x then y against the (sorted) interior
    structural coords. Each non-empty ``(x_idx, y_idx)`` becomes a cell. The
    cell's ``cut_history`` records the structural coords bounding it on each
    side (0-4 entries; corner cells have 2, edge cells 3, interior cells 4).

    ``bisect_right`` so an atom whose centroid sits exactly on a coord goes
    to the higher bin — robust to the rare absorbed-sliver atom whose
    centroid lands on a grid line.
    """
    if not interior_xs and not interior_ys:
        return [(atoms_with_local, [])] if atoms_with_local else []

    n_x = len(interior_xs)
    n_y = len(interior_ys)

    x_bins: list[list] = [[] for _ in range(n_x + 1)]
    for aw in atoms_with_local:
        x_bins[bisect.bisect_right(interior_xs, aw[1][0])].append(aw)

    cells = []
    for x_idx, x_bin in enumerate(x_bins):
        if not x_bin:
            continue
        y_bins: list[list] = [[] for _ in range(n_y + 1)]
        for aw in x_bin:
            y_bins[bisect.bisect_right(interior_ys, aw[1][1])].append(aw)
        for y_idx, cell_atoms in enumerate(y_bins):
            if not cell_atoms:
                continue
            history: list[tuple[str, float]] = []
            if x_idx > 0:
                history.append(("axis_x", float(interior_xs[x_idx - 1])))
            if x_idx < n_x:
                history.append(("axis_x", float(interior_xs[x_idx])))
            if y_idx > 0:
                history.append(("axis_y", float(interior_ys[y_idx - 1])))
            if y_idx < n_y:
                history.append(("axis_y", float(interior_ys[y_idx])))
            cells.append((cell_atoms, history))
    return cells


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

    atom_grid = _collect_group_grid(atoms)
    structural_grid = _collect_structural_coords(territories)

    # Pass A: collect structural cells per theta group.
    theta_cells: dict[float, list] = defaultdict(list)
    for terr in territories:
        eff_theta = 0.0 if terr.kind == KIND_CURVED else terr.theta
        theta_key = round(eff_theta, 9)
        struct_xs, struct_ys = structural_grid.get(theta_key, ((), ()))
        for piece_idx, _piece in enumerate(terr.pieces):
            piece_atoms = atoms_by_pp.get((terr.part_id, piece_idx), [])
            if not piece_atoms:
                continue
            atoms_with_local = _build_atoms_with_local(piece_atoms, eff_theta)
            pb = _piece_local_bbox(atoms_with_local)
            interior_xs = _interior_coords(struct_xs, pb[0], pb[2])
            interior_ys = _interior_coords(struct_ys, pb[1], pb[3])
            cells = _structural_partition(atoms_with_local, interior_xs, interior_ys)
            for cell_atoms, cell_history in cells:
                cell_area = sum(aw[3] for aw in cell_atoms)
                theta_cells[theta_key].append(
                    (cell_area, cell_atoms, cell_history,
                     terr.part_id, piece_idx, eff_theta),
                )

    # Pass B: subdivide each cell, area-desc within theta group so the
    # largest cells anchor the seen-coord state that smaller cells reuse.
    regions: list[Region] = []
    next_id = 0
    for theta_key, cells in theta_cells.items():
        xs_pool, ys_pool = atom_grid.get(theta_key, ((), ()))
        state = _PropagationState(seen_xs=set(), seen_ys=set())
        cells.sort(key=lambda c: -c[0])
        for _area, cell_atoms, cell_history, part_id, piece_idx, eff_theta in cells:
            k = max(1, round(_area / target_area))
            groups = _recurse_partition(cell_atoms, k, xs_pool, ys_pool, state)

            for atom_list, sub_history in groups:
                actual_atoms = [aw[0] for aw in atom_list]
                if not actual_atoms:
                    continue
                shape_part = _union_atoms_to_shape_part(actual_atoms)
                if shape_part is None:
                    continue
                regions.append(
                    Region(
                        region_id=next_id,
                        shape=shape_part,
                        atom_ids=tuple(a.atom_id for a in actual_atoms),
                        part_id=part_id,
                        piece_id=piece_idx,
                        theta=eff_theta,
                        cut_history=tuple(cell_history) + tuple(sub_history),
                    )
                )
                next_id += 1

    return tuple(regions)


def _piece_local_bbox(atoms_with_local):
    return (
        min(aw[2][0] for aw in atoms_with_local),
        min(aw[2][1] for aw in atoms_with_local),
        max(aw[2][2] for aw in atoms_with_local),
        max(aw[2][3] for aw in atoms_with_local),
    )


def _interior_coords(coords, lo: float, hi: float, eps: float = 1e-6):
    return tuple(c for c in coords if lo + eps < c < hi - eps)


# Atom local-frame cache ------------------------------------------------------


def _build_atoms_with_local(piece_atoms, eff_theta):
    """Pre-compute per-atom local-frame ``(bbox_center, bbox, area)`` once.

    Cut selection runs many sums and bbox-aspect checks per candidate; doing
    this work per call would create thousands of throwaway shapely Polygons.
    Cached structure is ``(atom, (cx, cy), (minx, miny, maxx, maxy), area)``.
    """
    out = []
    for a in piece_atoms:
        poly = _to_shapely(a.shape)
        if abs(eff_theta) > 1e-12:
            poly = _rotate_geom(poly, -eff_theta)
        minx, miny, maxx, maxy = poly.bounds
        cx = 0.5 * (minx + maxx)
        cy = 0.5 * (miny + maxy)
        out.append((a, (cx, cy), (minx, miny, maxx, maxy), float(poly.area)))
    return out


# Recursive partition ---------------------------------------------------------


def _recurse_partition(atoms_with_local, k, xs_pool, ys_pool, state):
    if k <= 1 or not atoms_with_local:
        return [(atoms_with_local, [])]
    total_area = sum(aw[3] for aw in atoms_with_local)
    if total_area < MIN_AREA * 2:
        return [(atoms_with_local, [])]

    sel = _select_lattice_cut(atoms_with_local, k, xs_pool, ys_pool, state)
    if sel is None:
        return [(atoms_with_local, [])]

    label, coord, left, right = sel
    state.add(label, coord)
    la = sum(aw[3] for aw in left)
    ra = sum(aw[3] for aw in right)
    k_alloc = _allocate_k_areas([la, ra], k)

    result = []
    for sub_atoms, sub_k in zip((left, right), k_alloc):
        for group_atoms, group_history in _recurse_partition(
            sub_atoms, sub_k, xs_pool, ys_pool, state,
        ):
            result.append((group_atoms, [(label, coord)] + group_history))
    return result


# Cut selection (lattice / slab over shared atom grid) -----------------------


def _select_lattice_cut(atoms_with_local, k_total, xs_pool, ys_pool, state):
    """Pick the best slab cut from the shared-grid pool.

    Ranking: balance descending, then seen-coord-first (Pass B neighbor
    propagation), then local-bbox aspect ascending. Balance and aspect come
    from cached per-atom area and local bbox — no shapely calls in the hot
    path.
    """
    cuts = _lattice_cuts(atoms_with_local, xs_pool, ys_pool)
    valid = []
    for label, coord, left, right in cuts:
        la = sum(aw[3] for aw in left)
        ra = sum(aw[3] for aw in right)
        if la < MIN_AREA or ra < MIN_AREA:
            continue
        b = min(la, ra) / max(la, ra)
        if b < BAL_MIN:
            continue
        left_asp = _local_bbox_aspect(left)
        right_asp = _local_bbox_aspect(right)
        if not _aspect_ok_areas([la, ra], [left_asp, right_asp], k_total):
            continue
        valid.append((label, coord, left, right, b, max(left_asp, right_asp)))
    if not valid:
        return None
    valid.sort(key=lambda v: (
        -round(v[4], TIE_DECIMALS),
        0 if state.has(v[0], v[1]) else 1,
        v[5],
    ))
    label, coord, left, right, _b, _asp = valid[0]
    return label, coord, left, right


def _local_bbox_aspect(atoms_with_local):
    """Aspect of the union bbox in the theta-group local frame.

    Exact for rectangular slabs (which cuts at atom-grid lines produce in
    rectangular pieces). For non-rectangular slabs it overestimates aspect,
    which is conservative — a slab that passes this gate has true aspect at
    most this value.
    """
    minx = min(aw[2][0] for aw in atoms_with_local)
    miny = min(aw[2][1] for aw in atoms_with_local)
    maxx = max(aw[2][2] for aw in atoms_with_local)
    maxy = max(aw[2][3] for aw in atoms_with_local)
    w, h = maxx - minx, maxy - miny
    if w <= 1e-9 or h <= 1e-9:
        return 99.0
    return max(w, h) / min(w, h)


def _aspect_ok_areas(areas, aspects, k_total):
    """Aspect gate, only enforced on pieces that won't be subdivided further."""
    k_alloc = _allocate_k_areas(areas, k_total)
    for ar, asp, kp in zip(areas, aspects, k_alloc):
        if (kp <= 1 or ar < MIN_AREA * 2) and asp > MAX_ASPECT:
            return False
    return True


def _allocate_k_areas(areas, k_total):
    total = sum(areas)
    out, acc = [], 0
    for i, ar in enumerate(areas):
        if i == len(areas) - 1:
            kk = max(1, k_total - acc)
        else:
            kk = max(1, round(k_total * ar / total))
            acc += kk
        out.append(kk)
    return out


# Geometry helpers ------------------------------------------------------------


def _to_shapely(part: ShapePart) -> sg.Polygon:
    return sg.Polygon(part.exterior, [list(h) for h in part.holes])


def _rotate_geom(geom, theta_rad):
    if abs(theta_rad) < 1e-12:
        return geom
    return sa.rotate(geom, degrees(theta_rad), origin=(0, 0))


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
