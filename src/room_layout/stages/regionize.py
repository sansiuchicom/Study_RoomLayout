"""Atom-based regionizer — Phase 5.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.9 + S03-D13.

Ported from Cell ``regionize.py`` and adapted to the new schema: the
stage takes a ``FloorShape`` (S03-D13). Algorithm unchanged.

Cut selection follows the reference algorithm at
``algorithm/celllayout/zoning.py``: hierarchical priority
T1a → T1b → T2 → T3, deterministic with balance/aspect gates and no
scoring function.

Two adaptations for atom alignment (region geometry is the union of
constituent atom polygons, not the polygon-cut sub-piece):

1. Cut candidate vertices are taken from the raw piece polygon (no
   simplification). Atom anchors already include every raw polygon
   vertex, so T1a/T1b cut lines coincide with atom column/row
   boundaries.

2. T3 ``axis_mid`` candidates are sampled from the local-frame atom
   edge positions inside the [0.3, 0.7] bbox fraction range — not from
   evenly spaced fractions — so T3 cuts also align with atom edges.

Atoms are assigned to sub-pieces by local-frame centroid containment.
The resulting region polygon is the union of the assigned atom polygons
in the global frame, so the region boundary follows atom edges
everywhere except where a T2 (oblique reflex_pair) cut runs through atom
interiors.

Internal per S03-D6 — ``Region`` is not re-exported from the public
surface. ``region_graph`` / ``shape_gate`` consume ``Region`` / ``regionize``.
"""

import bisect
from collections import defaultdict
from dataclasses import dataclass
from math import ceil

import shapely.geometry as sg
from shapely.ops import unary_union

from room_layout.schema import FloorShape, ShapePart
from room_layout.stages._helpers import from_shapely, rotate_radians, to_shapely
from room_layout.stages.atomize import Atom, atomize
from room_layout.stages.dimensions import DimensionPolicy
from room_layout.stages.territory import (
    KIND_CURVED,
    collect_cross_theta_contact_coords,
    resolve_territories,
)

# Reference parameters --------------------------------------------------------
MIN_AREA = 0.7  # m² minimum final region area
MAX_ASPECT = 3.0  # final region local-bbox aspect cap (~ 1m × 3m fits target)
BAL_MIN = 0.15  # balance threshold (smaller piece ≥ 15% of larger)
TIE_DECIMALS = 6  # balance tie-break precision (float drift tolerance)
_MERGE_NECK_EPS = 0.03  # sliver 흡수 시 병합 결과 최소 목 두께 — 이보다 얇게
# 연결되면(점-핀치 / hole 너머) 병합 거부 → 비현실 tab / area 손실 방지


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
    vertex coord, so it captures both piece-vertex anchors (structural)
    and the ``split_interval``-generated subdivisions baked into atom
    edges. Slab cut candidates are drawn from this pool.
    """
    xs_by_theta: dict[float, set[float]] = defaultdict(set)
    ys_by_theta: dict[float, set[float]] = defaultdict(set)
    for a in atoms:
        key = round(a.theta, 9)
        poly = rotate_radians(to_shapely(a.shape), -a.theta)
        for x, y in list(poly.exterior.coords)[:-1]:
            xs_by_theta[key].add(round(x, 9))
            ys_by_theta[key].add(round(y, 9))
    return {
        key: (tuple(sorted(xs_by_theta[key])), tuple(sorted(ys_by_theta[key])))
        for key in xs_by_theta
    }


def _collect_structural_coords(
    floor,
    territories,
) -> dict[float, tuple[tuple[float, ...], tuple[float, ...]]]:
    """Return ``{theta_key: (xs, ys)}`` of structural coords per theta group.

    Two sources contribute, in each non-curved piece's local frame:

      Intra-group vertex coords
        Every vertex of every non-curved territory piece (exterior +
        interior rings). Captures reflex vertices, hole reflexes, and
        cross-part edges of pieces sharing a theta group.

      Cross-group contact endpoints (via ``territory``)
        Endpoints of every shared boundary between pieces in DIFFERENT
        theta groups, projected into each piece's local frame.
        ``atomize`` uses the same source to seed atom anchors, so Pass
        A's cuts land exactly on these coords with no atom-snap drift.
    """
    xs_by_theta: dict[float, set[float]] = defaultdict(set)
    ys_by_theta: dict[float, set[float]] = defaultdict(set)

    for terr in territories:
        if terr.kind == KIND_CURVED:
            continue
        eff_theta = terr.theta
        key = round(eff_theta, 9)
        for piece in terr.pieces:
            poly = rotate_radians(to_shapely(piece), -eff_theta)
            if poly.is_empty:
                continue
            for ring in [poly.exterior, *poly.interiors]:
                for x, y in list(ring.coords)[:-1]:
                    xs_by_theta[key].add(round(x, 9))
                    ys_by_theta[key].add(round(y, 9))

    contact_xs, contact_ys = collect_cross_theta_contact_coords(floor, territories)
    for key, vals in contact_xs.items():
        xs_by_theta[key].update(vals)
    for key, vals in contact_ys.items():
        ys_by_theta[key].update(vals)

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

    Atoms are binned by local centroid x then y against the (sorted)
    interior structural coords. Each non-empty ``(x_idx, y_idx)`` becomes
    a cell tuple ``(atoms, history, x_idx, y_idx)``. ``history`` records
    the structural coords bounding the cell (0-4 entries: corner cells 2,
    edge cells 3, interior cells 4). ``x_idx``/``y_idx`` are retained so a
    follow-up absorption pass can find lattice-adjacent neighbors.

    ``bisect_right`` so an atom whose centroid sits exactly on a coord
    goes to the higher bin — robust to the rare absorbed-sliver atom whose
    centroid lands on a grid line.
    """
    if not interior_xs and not interior_ys:
        return [(atoms_with_local, [], 0, 0)] if atoms_with_local else []

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
            cells.append((cell_atoms, history, x_idx, y_idx))
    return cells


def _absorb_sliver_cells(cells, threshold: float = MIN_AREA):
    """Merge cells with area < threshold into their largest adjacent cell.

    Adjacency follows the ``(x_idx, y_idx)`` lattice (differs by 1 on one
    axis). When a neighbor has already been absorbed, the adjacency
    follows the merge chain to its current host — so a sliver sandwiched
    between another sliver and the main cell can still reach the main cell
    after the in-between sliver is merged first.

    Slivers without any live neighbor are returned as-is. Output is
    ``(atoms, history)`` pairs ready for Pass B; absorbed slivers'
    histories are dropped (the host's history still describes the merged
    region's actual exterior cuts).
    """
    if not cells:
        return []

    cells = list(cells)
    areas = [sum(aw[3] for aw in c[0]) for c in cells]
    idx_to_pos = {(c[2], c[3]): i for i, c in enumerate(cells)}
    successor: dict[int, int] = {}
    exhausted: set[int] = set()

    def root(i: int) -> int:
        while i in successor:
            i = successor[i]
        return i

    while True:
        live = [
            (i, areas[i])
            for i in range(len(cells))
            if i not in successor and i not in exhausted and areas[i] < threshold
        ]
        if not live:
            break
        sliver_i, _ = min(live, key=lambda p: p[1])
        _atoms, _hist, x_idx, y_idx = cells[sliver_i]
        adj_roots: set[int] = set()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            j = idx_to_pos.get((x_idx + dx, y_idx + dy))
            if j is None:
                continue
            r = root(j)
            if r != sliver_i:
                adj_roots.add(r)
        if not adj_roots:
            exhausted.add(sliver_i)
            continue
        # 격자 번호상 인접이어도 hole(계단/courtyard) 너머라 병합 결과가 robust 하게
        # 연결되지 않으면(disconnected = area 손실 B6, 또는 점-핀치 = 비현실 tab) 제외.
        # 병합 결과를 살짝 erode 해도 단일 Polygon 으로 남는 host 만 허용.
        sliver_poly = unary_union([to_shapely(aw[0].shape) for aw in cells[sliver_i][0]])
        robust = []
        for r in adj_roots:
            host_poly = unary_union([to_shapely(aw[0].shape) for aw in cells[r][0]])
            eroded = sliver_poly.union(host_poly).buffer(-_MERGE_NECK_EPS)
            if eroded.geom_type == "Polygon" and not eroded.is_empty:
                robust.append(r)
        if not robust:
            exhausted.add(sliver_i)
            continue
        host_i = max(robust, key=lambda r: areas[r])
        ha, hh, hx, hy = cells[host_i]
        cells[host_i] = (ha + cells[sliver_i][0], hh, hx, hy)
        areas[host_i] += areas[sliver_i]
        successor[sliver_i] = host_i

    return [(c[0], c[1]) for i, c in enumerate(cells) if i not in successor]


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
    to grid edges, so a pool coord cannot fall through any atom's
    centroid.
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
    floor: FloorShape,
    atoms: tuple[Atom, ...] | None = None,
    policy: DimensionPolicy | None = None,
    *,
    target_area: float = 3.0,
) -> tuple[Region, ...]:
    if atoms is None:
        atoms = atomize(floor, policy)
    if not atoms:
        return ()

    territories = resolve_territories(floor)
    atoms_by_pp: dict[tuple[int, int], list[Atom]] = defaultdict(list)
    for a in atoms:
        atoms_by_pp[(a.part_id, a.piece_id)].append(a)

    atom_grid = _collect_group_grid(atoms)
    structural_grid = _collect_structural_coords(floor, territories)

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
            cells = _absorb_sliver_cells(cells)
            for cell_atoms, cell_history in cells:
                cell_area = sum(aw[3] for aw in cell_atoms)
                theta_cells[theta_key].append(
                    (cell_area, cell_atoms, cell_history, terr.part_id, piece_idx, eff_theta),
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
            # k is the max of area-based count and aspect-based count.
            # A narrow slab (aspect > MAX_ASPECT) needs more cuts so each
            # terminal piece can satisfy the aspect cap. Without this bump,
            # k=2 on a 0.9×8 slab leaves the seen-coord cuts of wider
            # neighbors aspect-rejected — and the slab picks differently-
            # placed cuts, breaking row alignment with its sibling cells.
            cb = _piece_local_bbox(cell_atoms)
            w, h = cb[2] - cb[0], cb[3] - cb[1]
            cell_aspect = max(w, h) / max(min(w, h), 1e-9)
            k_area = max(1, round(_area / target_area))
            k_aspect = max(1, ceil(cell_aspect / MAX_ASPECT))
            k = max(k_area, k_aspect)
            groups = _recurse_partition(
                cell_atoms,
                k,
                xs_pool,
                ys_pool,
                state,
                cell_aspect,
            )

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

    Cut selection runs many sums and bbox-aspect checks per candidate;
    doing this work per call would create thousands of throwaway shapely
    Polygons. Cached structure is
    ``(atom, (cx, cy), (minx, miny, maxx, maxy), area)``.
    """
    out = []
    for a in piece_atoms:
        poly = to_shapely(a.shape)
        if abs(eff_theta) > 1e-12:
            poly = rotate_radians(poly, -eff_theta)
        minx, miny, maxx, maxy = poly.bounds
        cx = 0.5 * (minx + maxx)
        cy = 0.5 * (miny + maxy)
        out.append((a, (cx, cy), (minx, miny, maxx, maxy), float(poly.area)))
    return out


# Recursive partition ---------------------------------------------------------


def _recurse_partition(
    atoms_with_local,
    k,
    xs_pool,
    ys_pool,
    state,
    cell_aspect=1.0,
):
    """Recurse on a cell with given target k.

    ``cell_aspect`` is the original cell's bbox aspect ratio. Used to
    relax the terminal aspect gate inside thin cells — a 0.4×7 slab can
    only ever produce sub-pieces with aspect well above MAX_ASPECT, so
    enforcing the gate would block all subdivisions. The relaxation lets
    the cell subdivide internally and align with seen-coord cuts from its
    wider neighbors.
    """
    if k <= 1 or not atoms_with_local:
        return [(atoms_with_local, [])]
    total_area = sum(aw[3] for aw in atoms_with_local)
    if total_area < MIN_AREA * 2:
        return [(atoms_with_local, [])]

    sel = _select_lattice_cut(
        atoms_with_local,
        k,
        xs_pool,
        ys_pool,
        state,
        cell_aspect,
    )
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
            sub_atoms,
            sub_k,
            xs_pool,
            ys_pool,
            state,
            cell_aspect,
        ):
            result.append((group_atoms, [(label, coord)] + group_history))
    return result


# Cut selection (lattice / slab over shared atom grid) -----------------------


def _select_lattice_cut(
    atoms_with_local,
    k_total,
    xs_pool,
    ys_pool,
    state,
    cell_aspect=1.0,
):
    """Pick the best slab cut from the shared-grid pool.

    Two-pool selection:
      1. If any valid candidate's coord is in ``state.seen_*`` (= already
         used by an earlier cell in this theta group), pick the best among
         those by ``(balance DESC, aspect ASC)``. Aggressive propagation —
         even an asymmetric seen cut wins over a perfectly balanced unseen
         one, so sibling cells line up.
      2. Otherwise pick the overall best by the same key.

    ``cell_aspect`` is the enclosing cell's bbox aspect, used to relax the
    terminal aspect gate for sub-pieces inside an already-thin cell.
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
        if not _aspect_ok_areas(
            [la, ra],
            [left_asp, right_asp],
            k_total,
            cell_aspect,
        ):
            continue
        valid.append((label, coord, left, right, b, max(left_asp, right_asp)))
    if not valid:
        return None

    def sort_key(v):
        return (-round(v[4], TIE_DECIMALS), v[5])

    seen = [v for v in valid if state.has(v[0], v[1])]
    pool = seen if seen else valid
    pool.sort(key=sort_key)
    label, coord, left, right, _b, _asp = pool[0]
    return label, coord, left, right


def _local_bbox_aspect(atoms_with_local):
    """Aspect of the union bbox in the theta-group local frame.

    Exact for rectangular slabs (which cuts at atom-grid lines produce in
    rectangular pieces). For non-rectangular slabs it overestimates
    aspect, which is conservative — a slab that passes this gate has true
    aspect at most this value.
    """
    minx = min(aw[2][0] for aw in atoms_with_local)
    miny = min(aw[2][1] for aw in atoms_with_local)
    maxx = max(aw[2][2] for aw in atoms_with_local)
    maxy = max(aw[2][3] for aw in atoms_with_local)
    w, h = maxx - minx, maxy - miny
    if w <= 1e-9 or h <= 1e-9:
        return 99.0
    return max(w, h) / min(w, h)


def _aspect_ok_areas(areas, aspects, k_total, cell_aspect=1.0):
    """Aspect gate, only enforced on pieces that won't be subdivided further.

    The effective cap is ``max(MAX_ASPECT, cell_aspect)`` — inside a cell
    that is already thinner than MAX_ASPECT, no sub-piece can be more
    square than the cell itself, so enforcing the strict cap would block
    every cut. Relaxing to ``cell_aspect`` lets the cell subdivide along
    seen-coord cuts from its wider neighbors.
    """
    effective_max = max(MAX_ASPECT, cell_aspect)
    k_alloc = _allocate_k_areas(areas, k_total)
    for ar, asp, kp in zip(areas, aspects, k_alloc):
        if (kp <= 1 or ar < MIN_AREA * 2) and asp > effective_max:
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


def _union_atoms_to_shape_part(atoms) -> ShapePart | None:
    polys = [to_shapely(a.shape) for a in atoms]
    if not polys:
        return None
    merged = unary_union(polys)
    if merged.is_empty:
        return None
    if isinstance(merged, sg.MultiPolygon):
        merged = max(merged.geoms, key=lambda p: p.area)
    if not isinstance(merged, sg.Polygon):
        return None
    return from_shapely(merged)
