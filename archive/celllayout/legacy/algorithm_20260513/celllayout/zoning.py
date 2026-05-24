"""
Vertex-first deterministic zoning (pipeline20 essence).

Footprint → k zones (sub-room building blocks).

Hierarchy: T1a cross_cut > T1b vertex_aligned (+structural) > T2 oblique reflex > T3 axis_mid.
Stage-aware aspect: max_aspect enforced only on final pieces (k_p≤1 or area<min*2).
Float-tolerant balance tie-break (round to 6 decimals).
Multi-axis: per-family decomposition via cell layer (atom/per_family).
"""
from collections import defaultdict

import numpy as np
import shapely
import shapely.affinity as sa
import shapely.geometry as sg
from shapely.ops import split, unary_union

from celllayout.atom import per_family as p2M
from celllayout.atom.lir_progressive import lir_at_angle


# Parameters (external, not magic) ---------------------------------------------
MIN_AREA = 3.0          # m² — min final zone area (sub-room unit)
MARGIN = 0.5            # m — vertex too close to bbox edge → skip
MIN_CUT_LEN = 1.0       # m — oblique reflex pair min internal length
MAX_ASPECT = 4.0        # final zone MRR aspect cap (architectural)
BAL_MIN = 0.15          # T1/T2 balance ≥ this (1:7 imbalance OK)
SIMPLIFY_TOL = 0.15     # m — vertex/structural extraction simplification
TIE_DECIMALS = 6        # tie-break: balance rounded here (avoid float-drift bias)

# Tail cleanup (post-process): detach orientation-foreign protrusions and
# reassign to neighbour zone with longest shared boundary.
TAIL_MIN_AREA = 0.3     # m² — tail piece must reach this to be reassigned
TAIL_MIN_ASPECT = 6.0   # MRR aspect — only thin elongated pieces qualify
TAIL_MIN_CORE = 0.4     # family-theta LIR must be ≥ this fraction of zone area
TAIL_THETA_TOL = np.radians(10)  # tail orientation vs recipient family_theta
TAIL_BRIDGE_TOL = 0.02  # m — morphological-opening tolerance bridging slice↔target
TAIL_SLICE_MIN = 0.01   # m² — slice below this is dropped (numerical noise)


# 1. Reflex + structural coords -------------------------------------------------
def reflex_vertices(poly):
    """Reflex vertices on exterior + holes (CCW orientation)."""
    if not poly.exterior.is_ccw:
        poly = sg.Polygon(list(poly.exterior.coords)[::-1],
                          [list(h.coords)[::-1] for h in poly.interiors])
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


def structural_coords(poly):
    """Reflex coord set propagated to sub-recursion (alignment hint)."""
    simp = poly.simplify(SIMPLIFY_TOL, preserve_topology=True)
    src = simp if isinstance(simp, sg.Polygon) and not simp.is_empty else poly
    rfx = reflex_vertices(src)
    return {'xs': {round(x, 6) for x, _ in rfx},
            'ys': {round(y, 6) for _, y in rfx}}


# 2. Cut candidate generators ---------------------------------------------------
def _vertex_coords(poly):
    """Simplified polygon's exterior + hole vertices (for cut candidate seeding)."""
    simp = poly.simplify(SIMPLIFY_TOL, preserve_topology=True)
    src = simp if isinstance(simp, sg.Polygon) and not simp.is_empty else poly
    coords = list(src.exterior.coords)[:-1]
    for h in src.interiors:
        coords.extend(list(h.coords)[:-1])
    return coords


def vertex_aligned_lines(poly, structural=None):
    """T1b: axis-aligned line per vertex coord. structural injects parent reflex coords."""
    minx, miny, maxx, maxy = poly.bounds
    coords = _vertex_coords(poly)
    if structural:
        coords += [(x, miny) for x in structural['xs']]  # x → V line only (y at boundary)
        coords += [(minx, y) for y in structural['ys']]  # y → H line only (x at boundary)
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


def cross_cut_pairs(poly):
    """T1a: (V at x, H at y) pair per vertex with both inside margin → 3-4 piece split."""
    minx, miny, maxx, maxy = poly.bounds
    pairs, seen = [], set()
    for x, y in _vertex_coords(poly):
        k = (round(x, 2), round(y, 2))
        if (k in seen or
            not (minx + MARGIN < x < maxx - MARGIN) or
            not (miny + MARGIN < y < maxy - MARGIN)):
            continue
        seen.add(k)
        pairs.append([sg.LineString([(x, miny - 1), (x, maxy + 1)]),
                      sg.LineString([(minx - 1, y), (maxx + 1, y)])])
    return pairs


def reflex_pair_lines(poly):
    """T2: oblique line connecting two reflex vertices (axis-aligned excluded)."""
    rfx = reflex_vertices(poly)
    out = []
    for i in range(len(rfx)):
        for j in range(i + 1, len(rfx)):
            line = sg.LineString([rfx[i], rfx[j]])
            inter = line.intersection(poly)
            if not (hasattr(inter, 'length') and inter.length >= MIN_CUT_LEN):
                continue
            (x1, y1), (x2, y2) = list(line.coords)[0], list(line.coords)[-1]
            if abs(x1 - x2) < 1e-3 or abs(y1 - y2) < 1e-3:
                continue  # axis-aligned belongs to T1
            out.append([line])
    return out


def axis_mid_lines(poly):
    """T3 fallback: bbox fraction 0.3..0.7 lines (V and H)."""
    minx, miny, maxx, maxy = poly.bounds
    cuts = []
    for f in np.linspace(0.3, 0.7, 9):
        x = minx + f * (maxx - minx)
        y = miny + f * (maxy - miny)
        cuts.append([sg.LineString([(x, miny - 1), (x, maxy + 1)])])
        cuts.append([sg.LineString([(minx - 1, y), (maxx + 1, y)])])
    return cuts


# 3. Split & validity -----------------------------------------------------------
def split_pieces(poly, lines):
    """Split poly by 1+ lines sequentially. Returns area-desc pieces (≥2) or None."""
    pieces = [poly]
    for line in lines:
        nxt = []
        for p in pieces:
            try:
                r = split(p, line)
                parts = list(r.geoms) if hasattr(r, 'geoms') else [r]
                nxt.extend(q for q in parts
                           if isinstance(q, sg.Polygon) and q.area > 0.01)
            except Exception:
                nxt.append(p)
        pieces = nxt or pieces
    if len(pieces) < 2:
        return None
    return sorted(pieces, key=lambda p: -p.area)


def piece_aspect(p):
    """MRR-based aspect (max_edge / min_edge)."""
    if p.is_empty or p.area < 1e-6:
        return 99.0
    try:
        c = list(p.minimum_rotated_rectangle.exterior.coords)
        e1 = float(np.hypot(c[1][0] - c[0][0], c[1][1] - c[0][1]))
        e2 = float(np.hypot(c[2][0] - c[1][0], c[2][1] - c[1][1]))
        return max(e1, e2) / max(min(e1, e2), 1e-6)
    except Exception:
        return 99.0


def balance(pieces):
    a = [p.area for p in pieces]
    return min(a) / max(a)


def allocate_k(pieces, k_total):
    """Area-proportional k allocation; last piece absorbs remainder.
    Mirrors _partition's actual logic so cut validity matches recursion behavior."""
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
    """Stage-aware: enforce MAX_ASPECT only on final pieces (k_p≤1 or area<MIN*2).
    Intermediate pieces (will be sub-split) are exempt → vertex-aligned cuts that
    create temporarily elongated pieces (e.g., E자 H at y=8 → 14×3) survive."""
    if k_total is None:
        return all(piece_aspect(p) <= MAX_ASPECT for p in pieces)
    for p, kp in zip(pieces, allocate_k(pieces, k_total)):
        if (kp <= 1 or p.area < MIN_AREA * 2) and piece_aspect(p) > MAX_ASPECT:
            return False
    return True


def best_cut(candidates, poly, bal_min, k_total, prefer_short=False):
    """Pick valid cut with best (-balance_tied, tiebreak).

    candidates: iterable of (label, lines) pairs.
    Validity: min_area ≥ MIN_AREA, balance ≥ bal_min, _aspect_ok.
    Returns: (label, lines, pieces, balance) or None.
    """
    valid = []
    for label, lines in candidates:
        pieces = split_pieces(poly, lines)
        if pieces is None or min(p.area for p in pieces) < MIN_AREA:
            continue
        b = balance(pieces)
        if b < bal_min or not _aspect_ok(pieces, k_total):
            continue
        valid.append((label, lines, pieces, b))
    if not valid:
        return None
    if prefer_short:
        valid.sort(key=lambda v: (-round(v[3], TIE_DECIMALS),
                                   sum(l.length for l in v[1])))
    else:
        valid.sort(key=lambda v: (-round(v[3], TIE_DECIMALS),
                                   max(piece_aspect(p) for p in v[2])))
    return valid[0]


# 4. Hierarchical selection -----------------------------------------------------
def select_cut(poly, k_total, structural=None):
    """T1a (cross) → T1b (vertex_aligned + structural) → T2 (oblique) → T3 (axis_mid)."""
    for label, gen, prefer_short, bmin in (
        ('cross_cut',      lambda: cross_cut_pairs(poly),                False, BAL_MIN),
        ('vertex_aligned', lambda: ([line] for line in
                                     vertex_aligned_lines(poly, structural)), False, BAL_MIN),
        ('reflex_pair',    lambda: reflex_pair_lines(poly),              True,  BAL_MIN),
        ('axis_mid',       lambda: axis_mid_lines(poly),                 False, 0.0),
    ):
        cands = ((label, lines) for lines in gen())
        r = best_cut(cands, poly, bmin, k_total, prefer_short=prefer_short)
        if r is not None:
            return r
    return None


# 5. Recursive partition --------------------------------------------------------
def _partition(poly, k, structural):
    """Recurse in axis-aligned local frame. Caller handles theta rotation."""
    if k <= 1 or poly.area < MIN_AREA * 2:
        return [{'polygon': poly, 'cut_history': []}]
    sel = select_cut(poly, k, structural)
    if sel is None:
        return [{'polygon': poly, 'cut_history': []}]
    label, _lines, pieces, _b = sel
    zones = []
    for p, kp in zip(pieces, allocate_k(pieces, k)):
        for z in _partition(p, kp, structural):
            z['cut_history'].insert(0, label)
            zones.append(z)
    return zones


def partition_family(poly, k, theta):
    """Frame transform by -theta, partition, rotate back."""
    cx, cy = poly.centroid.x, poly.centroid.y
    P = (sa.rotate(poly, -np.degrees(theta), origin=(cx, cy))
         if abs(theta) > 1e-3 else poly)
    zones = _partition(P, k, structural_coords(P))
    if abs(theta) > 1e-3:
        for z in zones:
            z['polygon'] = sa.rotate(z['polygon'], np.degrees(theta),
                                     origin=(cx, cy))
    return zones


# 6. Family decomposition (cell layer) ------------------------------------------
def get_families(footprint, cell_size=0.3):
    """02M cell decomp → list of {id, polygon, theta, area} (area-desc)."""
    _cells, pieces, _, _ = p2M.recursive_progressive_per_family(
        footprint, target_cell_size=cell_size, seed=42)
    grp = defaultdict(lambda: {'polys': [], 'theta': 0.0})
    for piece in pieces:
        grp[piece['family_id']]['polys'].append(piece['polygon'])
        grp[piece['family_id']]['theta'] = piece['theta']
    out, nid = [], 0
    for d in grp.values():
        u = unary_union(d['polys'])
        for p in (list(u.geoms) if isinstance(u, sg.MultiPolygon) else [u]):
            if p.area >= 0.01:
                out.append({'id': nid, 'polygon': p,
                            'theta': d['theta'], 'area': p.area})
                nid += 1
    return sorted(out, key=lambda x: -x['area'])


# 7. Tail cleanup (post-process) ------------------------------------------------
def _detect_foreign_tails(zone_poly, family_theta,
                           min_area=TAIL_MIN_AREA,
                           min_aspect=TAIL_MIN_ASPECT,
                           min_core=TAIL_MIN_CORE,
                           lir_resolution=0.05):
    """Return foreign-tail Polygons in `zone_poly`.

    A 'foreign tail' is a connected piece outside the family-theta-aligned LIR
    that is thin+elongated (aspect ≥ min_aspect, area ≥ min_area). Chunky
    non-LIR pieces are NOT tails — they are normal local bulges.
    """
    if not isinstance(zone_poly, sg.Polygon) or zone_poly.is_empty:
        return []
    lir = lir_at_angle(zone_poly, family_theta, resolution=lir_resolution)
    if lir is None or lir.area < zone_poly.area * min_core:
        return []
    diff = zone_poly.difference(lir.buffer(1e-4))
    parts = list(diff.geoms) if hasattr(diff, 'geoms') else [diff]
    out = []
    for p in parts:
        if not (isinstance(p, sg.Polygon) and p.area >= min_area
                and piece_aspect(p) >= min_aspect):
            continue
        # Foreign means orientation distinct from family — same-orientation
        # residues are native LIR leftovers, not multi-axis transition wedges.
        if _theta_match(_tail_orientation(p), family_theta):
            continue
        out.append(p)
    return out


def _strip_tails(zone_poly, tails):
    """Remove `tails` from `zone_poly` and clean the zero-width slit that
    `difference` leaves along colinear cut paths."""
    raw = zone_poly.difference(unary_union(tails))
    core = (raw.buffer(-1e-3, cap_style=2, join_style=2)
               .buffer(1e-3, cap_style=2, join_style=2))
    if isinstance(core, sg.MultiPolygon):
        core = max(core.geoms, key=lambda p: p.area)
    return core


def _tail_orientation(tail_poly):
    """Principal angle of `tail_poly` (longest MRR edge, mod 90°).

    Returned in radians on [0, π/2). None if MRR is degenerate.
    """
    try:
        coords = list(tail_poly.minimum_rotated_rectangle.exterior.coords)
    except Exception:
        return None
    if len(coords) < 4:
        return None
    edges = [(coords[i + 1][0] - coords[i][0],
              coords[i + 1][1] - coords[i][1]) for i in range(4)]
    lengths = [np.hypot(dx, dy) for dx, dy in edges]
    if max(lengths) < 1e-9:
        return None
    dx, dy = edges[int(np.argmax(lengths))]
    return float(np.arctan2(dy, dx)) % (np.pi / 2)


def _theta_match(theta_a, theta_b, tol=TAIL_THETA_TOL):
    """True if two thetas are within `tol`, modulo 90°."""
    if theta_a is None or theta_b is None:
        return False
    d = abs((theta_a - theta_b) % (np.pi / 2))
    return min(d, np.pi / 2 - d) < tol


def _slice_tail_among_recipients(tail, family_theta, recipients):
    """Slice `tail` along the family rotated-frame long axis using each
    recipient's bbox range. Returns list of (slice_polygon, recipient_zone).
    Slices outside any recipient's range are dropped (caller restores them).
    """
    if not recipients:
        return []
    rad = np.radians
    deg = np.degrees
    cx, cy = 0.0, 0.0  # constant origin keeps slabs consistent across shapes
    tail_rot = sa.rotate(tail, -deg(family_theta), origin=(cx, cy))
    tx0, ty0, tx1, ty1 = tail_rot.bounds
    use_y = (ty1 - ty0) >= (tx1 - tx0)

    ranges = []
    for r in recipients:
        rr = sa.rotate(r['polygon'], -deg(family_theta), origin=(cx, cy))
        bx0, by0, bx1, by1 = rr.bounds
        lo, hi = (by0, by1) if use_y else (bx0, bx1)
        ranges.append((r, lo, hi))
    ranges.sort(key=lambda x: x[1])

    out = []
    for r, lo, hi in ranges:
        slab = (sg.box(tx0 - 1, lo, tx1 + 1, hi) if use_y
                else sg.box(lo, ty0 - 1, hi, ty1 + 1))
        s = tail_rot.intersection(slab)
        if s.is_empty:
            continue
        s_orig = sa.rotate(s, deg(family_theta), origin=(cx, cy))
        parts = ([s_orig] if isinstance(s_orig, sg.Polygon)
                 else list(s_orig.geoms) if hasattr(s_orig, 'geoms') else [])
        for p in parts:
            if isinstance(p, sg.Polygon) and p.area >= TAIL_SLICE_MIN:
                out.append((p, r))
    return out


def _bridge_merge(target, piece, tol=TAIL_BRIDGE_TOL):
    """Merge `piece` into `target`. If they are within `tol` but not actually
    touching along a 1D boundary, bridge the sub-tolerance gap with a
    morphological opening so the result is a single Polygon."""
    direct = unary_union([target, piece])
    if isinstance(direct, sg.Polygon):
        return direct
    bridged = (direct.buffer(tol, cap_style=2, join_style=2)
                     .buffer(-tol, cap_style=2, join_style=2))
    if isinstance(bridged, sg.Polygon):
        return bridged
    if isinstance(bridged, sg.MultiPolygon):
        return max(bridged.geoms, key=lambda p: p.area)
    return None  # bridging failed


def _cleanup_zone_tails(zones, footprint):
    """Extract foreign-orientation tails and distribute across all
    orientation-compatible recipient zones via family-long-axis slicing.
    Slices that fall outside every recipient's range are returned to source.
    Sub-tolerance gaps (parallel-offset edges) are bridged morphologically.
    Source zones are only modified if at least one slice successfully merges.
    """
    pending = []  # (source_zone, [(slice, target), ...], leftovers)
    for z in zones:
        tails = _detect_foreign_tails(z['polygon'], z['family_theta'])
        if not tails:
            continue
        all_slices = []
        leftovers = []
        for t in tails:
            tail_theta = _tail_orientation(t)
            compatibles = [o for o in zones
                           if o['zone_id'] != z['zone_id']
                           and _theta_match(tail_theta, o['family_theta'])]
            if not compatibles:
                continue
            family_theta = compatibles[0]['family_theta']
            slices = _slice_tail_among_recipients(t, family_theta, compatibles)
            covered = (unary_union([s for s, _ in slices])
                       if slices else sg.Polygon())
            leftover = t.difference(covered) if not covered.is_empty else t
            if not leftover.is_empty and leftover.area >= TAIL_SLICE_MIN:
                leftovers.append(leftover)
            all_slices.extend(slices)
        if not all_slices:
            continue
        pending.append((z, all_slices, leftovers))

    for src, slices_with_targets, leftovers in pending:
        all_pieces = [s for s, _ in slices_with_targets] + leftovers
        src['polygon'] = _strip_tails(src['polygon'], all_pieces)
        for piece, target in slices_with_targets:
            merged = _bridge_merge(target['polygon'], piece)
            if merged is not None:
                target['polygon'] = merged
            else:
                src['polygon'] = unary_union([src['polygon'], piece])
        for piece in leftovers:
            src['polygon'] = unary_union([src['polygon'], piece])

    for z in zones:
        g = z['polygon'].intersection(footprint)
        if isinstance(g, sg.Polygon):
            z['polygon'] = g
        elif hasattr(g, 'geoms'):
            polys = [x for x in g.geoms if isinstance(x, sg.Polygon)]
            if polys:
                z['polygon'] = max(polys, key=lambda p: p.area)

    # Normalise coordinates to a mm grid. Slicing + bridge_merge produce
    # vertices that differ at ULP level along shared boundaries, which makes
    # `boundary.intersection` collapse a real 3 m contact to ~1.8 cm and the
    # graph splits into disconnected components. `set_precision` snaps both
    # polygons to the same grid so their segments coincide exactly.
    for z in zones:
        z['polygon'] = shapely.set_precision(z['polygon'], 0.001)
    return zones


# 8. Main interface -------------------------------------------------------------
def zone_footprint(footprint, k=None, area_per_zone=10.0):
    """Footprint → k zones. Multi-axis aware via per-family decomposition.

    k=None → auto from footprint.area / area_per_zone (≥2).
    Returns (zones, families).
    """
    if k is None:
        k = max(2, round(footprint.area / area_per_zone))

    families = get_families(footprint)
    threshold = max(MIN_AREA * 0.6, footprint.area * 0.04)
    big = [f for f in families if f['area'] >= threshold]
    if not big and families:
        big = [families[0]]
    if not big:
        big = [{'id': 0, 'polygon': footprint, 'theta': 0.0,
                'area': footprint.area}]

    # k allocation by area
    total = sum(f['area'] for f in big)
    k_alloc, acc = [], 0
    for i, f in enumerate(big):
        kk = (max(1, k - acc) if i == len(big) - 1
              else max(1, round(k * f['area'] / total)))
        k_alloc.append(kk)
        if i < len(big) - 1:
            acc += kk

    # Partition each family
    all_zones, zid = [], 0
    for f, kk in zip(big, k_alloc):
        for s in partition_family(f['polygon'], kk, f['theta']):
            all_zones.append({'polygon': s['polygon'],
                              'zone_id': zid,
                              'family_id': f['id'],
                              'family_theta': f['theta'],
                              'cut_history': s.get('cut_history', [])})
            zid += 1

    # Coverage fix: gap → nearest zone (by boundary share)
    union_z = unary_union([z['polygon'] for z in all_zones])
    gap = footprint.difference(union_z)
    if gap.area > 0.01:
        for part in (list(gap.geoms) if isinstance(gap, sg.MultiPolygon)
                     else [gap]):
            if part.area < 0.01:
                continue
            best = max(all_zones,
                       key=lambda z: z['polygon'].buffer(0.3)
                                      .intersection(part.boundary).length
                                      if part.boundary.length > 0 else 0)
            best['polygon'] = unary_union([best['polygon'], part])

    # Clip to footprint, keep largest Polygon part (drop lines/points from
    # GeometryCollection that intersection() may produce on curved boundaries)
    for z in all_zones:
        g = z['polygon'].intersection(footprint)
        if isinstance(g, sg.Polygon):
            z['polygon'] = g
        elif hasattr(g, 'geoms'):
            polys = [x for x in g.geoms if isinstance(x, sg.Polygon)]
            z['polygon'] = (max(polys, key=lambda p: p.area)
                            if polys else z['polygon'])

    # Tail cleanup: detach orientation-foreign protrusions (e.g. diagonal
    # wedges absorbed by an axis-aligned family) and reassign to neighbour.
    all_zones = _cleanup_zone_tails(all_zones, footprint)

    return all_zones, big
