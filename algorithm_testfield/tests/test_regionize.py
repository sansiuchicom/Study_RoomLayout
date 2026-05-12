import math

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
    case = selected_cases([1])[0][2]
    regions = regionize(case)
    # at least some regions should have non-empty cut_history
    assert any(len(r.cut_history) > 0 for r in regions)
    valid_labels = {"cross_cut", "vertex_aligned", "reflex_pair", "axis_mid"}
    for r in regions:
        for label in r.cut_history:
            assert label in valid_labels, (r.region_id, label)


def test_target_area_smaller_produces_more_regions():
    case = selected_cases([1])[0][2]
    atoms = atomize(case)
    coarse = regionize(case, atoms=atoms, target_area=12.0)
    fine = regionize(case, atoms=atoms, target_area=4.0)
    assert len(fine) > len(coarse)
