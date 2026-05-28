"""Tests for ``room_layout.stages.atomize`` — work item 4.8a / Plan §4.8.

Unit tests on small shapes assert atomize's structural invariants:
area conservation (atoms tile the floor exactly), containment, part_id
assignment, theta inheritance, hole exclusion, and the Atom dataclass
properties. Exhaustive per-atom geometry across the 33 showcase cases
is covered by the goldens in 4.8b.
"""

import pytest
import shapely.affinity as sa
import shapely.geometry as sg
from shapely.ops import unary_union

from room_layout.schema import FloorShape, ShapePart
from room_layout.stages._helpers import from_shapely, part_theta, to_shapely
from room_layout.stages.atomize import Atom, atomize


def _rect(x0, y0, x1, y1) -> ShapePart:
    return ShapePart(exterior=((x0, y0), (x1, y0), (x1, y1), (x0, y1)))


def _floor(*parts) -> FloorShape:
    return FloorShape(level=1, parts=list(parts), floor_to_floor_height=3.0)


def _atoms_union(atoms):
    return unary_union([to_shapely(a.shape) for a in atoms])


# --- basic structure ---


def test_atomize_returns_tuple_of_atoms():
    atoms = atomize(_floor(_rect(0, 0, 1, 1)))
    assert isinstance(atoms, tuple)
    assert atoms
    assert all(isinstance(a, Atom) for a in atoms)


def test_atomize_simple_rect_tiles_exactly():
    atoms = atomize(_floor(_rect(0, 0, 1, 1)))
    assert sum(a.area for a in atoms) == pytest.approx(1.0)


def test_atomize_unique_atom_ids():
    atoms = atomize(_floor(_rect(0, 0, 2, 2)))
    ids = [a.atom_id for a in atoms]
    assert len(ids) == len(set(ids))


# --- area conservation + containment ---


def test_atomize_area_conserved_for_clean_rect():
    atoms = atomize(_floor(_rect(0, 0, 3, 2)))
    assert abs(sum(a.area for a in atoms) - 6.0) < 1e-9


def test_atomize_union_within_footprint():
    floor = _floor(_rect(0, 0, 2, 2))
    atoms = atomize(floor)
    footprint = to_shapely(floor.parts[0])
    union = _atoms_union(atoms)
    # union must not spill outside the footprint (allow tiny FP slack)
    assert union.difference(footprint).area < 1e-9


def test_atomize_hole_is_excluded():
    # rect 10x10 with a 4x4 CW hole → tiled area = 100 - 16 = 84
    part = ShapePart(
        exterior=((0, 0), (10, 0), (10, 10), (0, 10)),
        holes=(((3, 3), (3, 7), (7, 7), (7, 3)),),
    )
    atoms = atomize(_floor(part))
    assert abs(sum(a.area for a in atoms) - 84.0) < 1e-6


# --- part_id / theta ---


def test_atomize_distinct_part_ids_for_two_parts():
    atoms = atomize(_floor(_rect(0, 0, 1, 1), _rect(3, 3, 4, 4)))
    assert sorted(set(a.part_id for a in atoms)) == [0, 1]


def test_atomize_axis_aligned_theta_zero():
    atoms = atomize(_floor(_rect(0, 0, 2, 2)))
    assert all(a.theta == 0.0 for a in atoms)


def test_atomize_rotated_inherits_part_theta():
    # a rect rotated 30° about its center; atoms share the part's theta
    box = sg.box(0, 0, 4, 3)
    rotated = from_shapely(sa.rotate(box, 30, origin=(2, 1.5)))
    expected_theta = part_theta(rotated)
    atoms = atomize(_floor(rotated))
    assert atoms
    assert all(abs(a.theta - expected_theta) < 1e-9 for a in atoms)
    assert expected_theta > 0.0  # genuinely rotated


# --- Atom properties ---


def test_atom_area_property_matches_polygon():
    atoms = atomize(_floor(_rect(0, 0, 1, 1)))
    a = atoms[0]
    assert a.area == pytest.approx(to_shapely(a.shape).area)


def test_atom_centroid_property():
    atoms = atomize(_floor(_rect(0, 0, 1, 1)))
    cx, cy = atoms[0].centroid
    c = to_shapely(atoms[0].shape).centroid
    assert abs(cx - c.x) < 1e-12
    assert abs(cy - c.y) < 1e-12


# --- absorb_slivers flag ---


def test_atomize_absorb_slivers_flag_runs_both_ways():
    floor = _floor(_rect(0, 0, 2, 2))
    with_absorb = atomize(floor, absorb_slivers=True)
    without_absorb = atomize(floor, absorb_slivers=False)
    # both tile the same total area; absorbing never increases the count
    assert abs(sum(a.area for a in with_absorb) - 4.0) < 1e-9
    assert abs(sum(a.area for a in without_absorb) - 4.0) < 1e-9
    assert len(with_absorb) <= len(without_absorb)
