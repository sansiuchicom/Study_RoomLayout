"""Tests for ``room_layout.stages.regionize`` — work item 4.9a / Plan §4.9.

Unit tests on small shapes assert regionize's structural invariants:
area conservation (regions tile the floor), every region ≥ MIN_AREA,
atom partition (each atom lands in exactly one region), unique ids,
multi-part coverage, and atoms-param consistency. Exact per-region
geometry across the 33 showcase cases is covered by the goldens in 4.9b.
"""

import pytest

from room_layout.schema import FloorShape, ShapePart
from room_layout.stages._helpers import to_shapely
from room_layout.stages.atomize import Atom, atomize
from room_layout.stages.regionize import (
    MIN_AREA,
    Region,
    _lattice_cuts,
    _union_atoms_to_shape_part,
    regionize,
)


def _rect(x0, y0, x1, y1) -> ShapePart:
    return ShapePart(exterior=((x0, y0), (x1, y0), (x1, y1), (x0, y1)))


def _floor(*parts) -> FloorShape:
    return FloorShape(level=1, parts=list(parts), floor_to_floor_height=3.0)


def _area(region: Region) -> float:
    return to_shapely(region.shape).area


# --- basic structure ---


def test_regionize_returns_tuple_of_regions():
    regions = regionize(_floor(_rect(0, 0, 2, 2)))
    assert isinstance(regions, tuple)
    assert regions
    assert all(isinstance(r, Region) for r in regions)


def test_regionize_small_square_is_one_region():
    # 2x2 = 4 m²; k_area = round(4/3) = 1 → a single region, full area
    regions = regionize(_floor(_rect(0, 0, 2, 2)))
    assert len(regions) == 1
    assert _area(regions[0]) == pytest.approx(4.0)


def test_regionize_subdivides_large_slab():
    # 6x2 = 12 m²; k_area = round(12/3) = 4 → subdivided
    regions = regionize(_floor(_rect(0, 0, 6, 2)))
    assert len(regions) >= 2


def test_regionize_unique_region_ids():
    regions = regionize(_floor(_rect(0, 0, 6, 2)))
    ids = [r.region_id for r in regions]
    assert ids == list(range(len(regions)))  # sequential, unique


# --- area conservation + min area ---


def test_regionize_area_conserved():
    regions = regionize(_floor(_rect(0, 0, 6, 2)))
    assert sum(_area(r) for r in regions) == pytest.approx(12.0)


def test_regionize_regions_meet_min_area():
    regions = regionize(_floor(_rect(0, 0, 6, 2)))
    assert all(_area(r) >= MIN_AREA - 1e-9 for r in regions)


# --- atom partition ---


def test_regionize_atoms_partitioned():
    """Each atom lands in exactly one region (no loss, no double-count)."""
    floor = _floor(_rect(0, 0, 6, 2))
    atoms = atomize(floor)
    regions = regionize(floor, atoms=atoms)
    assigned = [aid for r in regions for aid in r.atom_ids]
    all_atom_ids = {a.atom_id for a in atoms}
    assert len(assigned) == len(set(assigned))  # disjoint
    assert set(assigned) == all_atom_ids  # complete


def test_regionize_atom_ids_non_empty():
    regions = regionize(_floor(_rect(0, 0, 6, 2)))
    assert all(len(r.atom_ids) > 0 for r in regions)


# --- consistency + multi-part ---


def test_regionize_explicit_atoms_match_internal():
    floor = _floor(_rect(0, 0, 6, 2))
    assert regionize(floor) == regionize(floor, atoms=atomize(floor))


def test_regionize_two_parts_span_both_part_ids():
    regions = regionize(_floor(_rect(0, 0, 4, 2), _rect(6, 6, 10, 8)))
    assert sorted(set(r.part_id for r in regions)) == [0, 1]
    assert sum(_area(r) for r in regions) == pytest.approx(16.0)


def test_regionize_empty_atoms_returns_empty():
    # regionize short-circuits on no atoms
    assert regionize(_floor(_rect(0, 0, 2, 2)), atoms=()) == ()


# --- region metadata ---


def test_regionize_carries_theta_and_piece():
    regions = regionize(_floor(_rect(0, 0, 2, 2)))
    r = regions[0]
    assert r.theta == 0.0
    assert r.piece_id == 0
    assert isinstance(r.cut_history, tuple)


# --- latent-bug PoC (review B5) ---


@pytest.mark.xfail(
    reason="B5 latent: _lattice_cuts splits left/right with strict < / >, so an atom "
    "whose local centroid sits exactly on a cut coordinate is dropped from BOTH sides "
    "(silent atom loss). Pass A guards this case via bisect_right; Pass B does not. "
    "Not triggered by the 33 fixtures; this is the minimal direct trigger.",
    strict=True,
)
def test_lattice_cuts_conserves_atom_whose_centroid_is_on_the_cut():
    # aw is (atom, local_centroid, ...); _lattice_cuts only reads aw[1]. Three
    # atoms at x = 1, 2, 3; cutting at the pool coord x = 2 must keep all three.
    aws = [(None, (1.0, 0.5)), (None, (2.0, 0.5)), (None, (3.0, 0.5))]
    cuts = _lattice_cuts(aws, [2.0], [])
    assert cuts, "expected an x-cut at 2.0"
    _, _, left, right = cuts[0]
    # the atom centred exactly at x = 2.0 must land on one side, not vanish
    assert len(left) + len(right) == len(aws)


@pytest.mark.xfail(
    reason="B6 latent: _union_atoms_to_shape_part keeps only the largest piece when the "
    "atom union is a MultiPolygon (disconnected group), silently dropping the rest — while "
    "the caller still lists every atom in region.atom_ids, desyncing shape from atom_ids. "
    "Not triggered by the 33 fixtures (Pass A pre-splits at reflex vertices); minimal trigger.",
    strict=True,
)
def test_union_atoms_conserves_area_when_group_is_disconnected():
    # Two atoms with a gap → unary_union is a MultiPolygon; the region shape must
    # still account for all the atom area, not just the largest piece.
    def _atom(aid, sp):
        return Atom(
            atom_id=aid, shape=sp, part_id=0, piece_id=0, theta=0.0, is_feature_sliver=False
        )

    atoms = [_atom(0, _rect(0, 0, 1, 1)), _atom(1, _rect(3, 0, 4, 1))]
    shape = _union_atoms_to_shape_part(atoms)
    assert shape is not None
    assert to_shapely(shape).area == pytest.approx(2.0, abs=1e-9)
