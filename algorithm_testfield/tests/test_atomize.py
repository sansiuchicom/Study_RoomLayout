import math

import shapely.geometry as sg

from celllayout_tf.atomize import Atom, atomize
from celllayout_tf.cases import selected_cases
from celllayout_tf.dimensions import DimensionPolicy
from celllayout_tf.schema import ShapeInput, ShapePart
from celllayout_tf.territory import resolve_territories


def _to_shapely(part: ShapePart) -> sg.Polygon:
    return sg.Polygon(part.exterior, [list(h) for h in part.holes])


def _atom_area(a: Atom) -> float:
    return _to_shapely(a.shape).area


def _territory_total_area(shape: ShapeInput) -> float:
    terr = resolve_territories(shape)
    return sum(_to_shapely(p).area for t in terr for p in t.pieces)


def test_atomize_simple_rect_tiles_full_area():
    shape = ShapeInput(
        "rect",
        (ShapePart(exterior=((0, 0), (12, 0), (12, 8), (0, 8))),),
    )
    atoms = atomize(shape)
    total = sum(_atom_area(a) for a in atoms)
    assert math.isclose(total, 96.0, rel_tol=1e-6)
    assert all(a.theta == 0.0 for a in atoms)
    assert all(a.part_id == 0 and a.piece_id == 0 for a in atoms)


def test_atoms_do_not_overlap_pairwise_on_small_case():
    case = selected_cases([9])[0][2]  # ㄱ자 standard
    atoms = atomize(case)
    polys = [_to_shapely(a.shape) for a in atoms]
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            inter = polys[i].intersection(polys[j])
            assert inter.area < 1e-6, (i, j, inter.area)


def test_atom_total_area_matches_resolved_territories_for_all_cases():
    for idx, _name, case in selected_cases():
        atoms = atomize(case)
        atom_area = sum(_atom_area(a) for a in atoms)
        terr_area = _territory_total_area(case)
        assert math.isclose(atom_area, terr_area, rel_tol=1e-3), idx


def test_case_22_main_atoms_theta_zero_wing_atoms_theta_25():
    case = selected_cases([22])[0][2]
    atoms = atomize(case)

    main_atoms = [a for a in atoms if a.part_id == 0]
    wing_atoms = [a for a in atoms if a.part_id == 1]

    assert main_atoms and wing_atoms
    for a in main_atoms:
        assert a.theta == 0.0
    for a in wing_atoms:
        assert abs(a.theta - math.radians(25)) < 1e-9


def test_case_24_vertical_atoms_axis_aligned_bar_atoms_rotated():
    case = selected_cases([24])[0][2]
    atoms = atomize(case)
    bar_atoms = [a for a in atoms if a.part_id == 0]
    vert_atoms = [a for a in atoms if a.part_id == 1]
    assert bar_atoms and vert_atoms
    for a in vert_atoms:
        assert a.theta == 0.0
    # bar rotated -25° around origin then translated; effective theta = -25° mod (π/2) = 65°
    for a in bar_atoms:
        assert abs(a.theta - math.radians(65)) < 1e-9


def test_case_13_vertical_bar_atoms_split_across_two_pieces():
    case = selected_cases([13])[0][2]
    atoms = atomize(case)
    pairs = {(a.part_id, a.piece_id) for a in atoms}
    assert (0, 0) in pairs  # horizontal bar single piece
    assert (1, 0) in pairs  # vertical bar bottom piece
    assert (1, 1) in pairs  # vertical bar top piece


def test_case_28_curved_disk_uses_axis_aligned_grid():
    case = selected_cases([28])[0][2]
    atoms = atomize(case)
    disk_atoms = [a for a in atoms if a.part_id == 2]
    assert disk_atoms
    # curved part is atomized at theta=0 (axis-aligned grid clipped to curve)
    for a in disk_atoms:
        assert a.theta == 0.0


def test_all_atom_polygons_are_valid_and_nonempty():
    case = selected_cases([5])[0][2]  # 타워형 has cascading clips
    atoms = atomize(case)
    for a in atoms:
        poly = _to_shapely(a.shape)
        assert poly.is_valid, a.atom_id
        assert poly.area > 0, a.atom_id


def test_each_atom_has_unique_id():
    case = selected_cases([22])[0][2]
    atoms = atomize(case)
    ids = [a.atom_id for a in atoms]
    assert len(ids) == len(set(ids))


def test_finer_policy_produces_more_atoms():
    case = selected_cases([1])[0][2]
    coarse = atomize(case, DimensionPolicy(target_atom_size=0.40))
    fine = atomize(case, DimensionPolicy(target_atom_size=0.25))
    assert len(fine) > len(coarse)
