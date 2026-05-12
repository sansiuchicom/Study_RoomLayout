import math
from collections import defaultdict

import shapely.affinity as sa
import shapely.geometry as sg
from shapely.ops import unary_union

from celllayout_tf.atomize import atomize
from celllayout_tf.cases import selected_cases
from celllayout_tf.regionize import Region, regionize


def _shape_to_polygon(shape):
    return sg.Polygon(shape.exterior, [list(h) for h in shape.holes])


def _total_atom_area(atoms):
    return sum(_shape_to_polygon(a.shape).area for a in atoms)


def test_regionize_rect_returns_multiple_regions():
    case = selected_cases([1])[0][2]  # 30평 판상형 14×10 = 140 m²
    regions = regionize(case)
    assert len(regions) >= 5  # 140 / 6 ≈ 23


def test_every_atom_assigned_to_exactly_one_region():
    case = selected_cases([1])[0][2]
    atoms = atomize(case)
    regions = regionize(case, atoms=atoms)

    all_atom_ids = {a.atom_id for a in atoms}
    assigned: set[int] = set()
    for r in regions:
        for aid in r.atom_ids:
            assert aid not in assigned, f"atom {aid} assigned twice"
            assigned.add(aid)
    assert assigned == all_atom_ids


def test_region_areas_within_min_max_band_mostly():
    case = selected_cases([1])[0][2]
    atoms = atomize(case)
    regions = regionize(case, atoms=atoms)
    for r in regions:
        poly = _shape_to_polygon(r.shape)
        # at minimum, every region should not be a sliver
        assert poly.area > 0.5, (r.region_id, poly.area)


def test_regions_dont_span_part_or_piece():
    case = selected_cases([22])[0][2]  # main(part 0) + wing(part 1)
    atoms = atomize(case)
    regions = regionize(case, atoms=atoms)

    atom_by_id = {a.atom_id: a for a in atoms}
    for r in regions:
        parts = {atom_by_id[aid].part_id for aid in r.atom_ids}
        pieces = {atom_by_id[aid].piece_id for aid in r.atom_ids}
        assert len(parts) == 1, (r.region_id, parts)
        assert len(pieces) == 1, (r.region_id, pieces)


def test_case_13_disjoint_pieces_get_separate_regions():
    case = selected_cases([13])[0][2]  # 十자: P0 + P1 (split into 2 pieces)
    atoms = atomize(case)
    regions = regionize(case, atoms=atoms)

    pieces_seen = {(r.part_id, r.piece_id) for r in regions}
    assert (1, 0) in pieces_seen
    assert (1, 1) in pieces_seen


def test_region_area_sum_matches_atom_total():
    for idx, _name, case in selected_cases([1, 5, 9, 13, 16, 22, 24, 28]):
        atoms = atomize(case)
        regions = regionize(case, atoms=atoms)
        region_area = sum(_shape_to_polygon(r.shape).area for r in regions)
        assert math.isclose(region_area, _total_atom_area(atoms), rel_tol=1e-3), idx


def test_regionize_runs_on_all_33_cases():
    for idx, _name, case in selected_cases():
        regions = regionize(case)
        assert regions, idx


def test_region_atom_ids_match_actual_atom_union_area():
    case = selected_cases([16])[0][2]
    atoms = atomize(case)
    atom_by_id = {a.atom_id: a for a in atoms}
    regions = regionize(case, atoms=atoms)
    for r in regions:
        atom_polys = [_shape_to_polygon(atom_by_id[aid].shape) for aid in r.atom_ids]
        merged_area = unary_union(atom_polys).area
        region_area = _shape_to_polygon(r.shape).area
        assert math.isclose(merged_area, region_area, rel_tol=1e-3), r.region_id


def test_cut_history_is_recorded():
    """Each entry is (axis_label, local-frame coord); labels are axis-only."""
    case = selected_cases([1])[0][2]
    regions = regionize(case)
    assert any(len(r.cut_history) > 0 for r in regions)
    valid_labels = {"axis_x", "axis_y"}
    for r in regions:
        for entry in r.cut_history:
            assert isinstance(entry, tuple) and len(entry) == 2, (r.region_id, entry)
            label, coord = entry
            assert label in valid_labels, (r.region_id, label)
            assert isinstance(coord, float), (r.region_id, entry)


def _local_atom_coords_by_theta(atoms):
    """Map round(theta, 9) -> (set of local-frame xs, set of local-frame ys)."""
    xs: dict[float, set[float]] = defaultdict(set)
    ys: dict[float, set[float]] = defaultdict(set)
    for a in atoms:
        key = round(a.theta, 9)
        poly = _shape_to_polygon(a.shape)
        if abs(a.theta) > 1e-12:
            poly = sa.rotate(poly, -math.degrees(a.theta), origin=(0, 0))
        for x, y in list(poly.exterior.coords)[:-1]:
            xs[key].add(round(x, 4))
            ys[key].add(round(y, 4))
    return xs, ys


def test_cut_coords_come_from_shared_grid():
    """Every cut coord must be a vertex on the theta-group's atom grid.

    Case 13 has two axis-aligned parts (same theta group). If part 0 and the
    two pieces of part 1 don't share the cut-coord pool, parts cut at
    coordinates that don't appear anywhere else in the group.
    """
    case = selected_cases([13])[0][2]
    atoms = atomize(case)
    regions = regionize(case, atoms=atoms)

    xs_by_theta, ys_by_theta = _local_atom_coords_by_theta(atoms)
    for r in regions:
        key = round(r.theta, 9)
        for label, coord in r.cut_history:
            c = round(coord, 4)
            if label == "axis_x":
                assert c in xs_by_theta[key], (r.region_id, label, coord)
            elif label == "axis_y":
                assert c in ys_by_theta[key], (r.region_id, label, coord)


def test_target_area_smaller_produces_more_regions():
    case = selected_cases([1])[0][2]
    atoms = atomize(case)
    coarse = regionize(case, atoms=atoms, target_area=12.0)
    fine = regionize(case, atoms=atoms, target_area=4.0)
    assert len(fine) > len(coarse)
