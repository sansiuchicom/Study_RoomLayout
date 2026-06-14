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
    _MERGE_NECK_EPS,
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


def test_regionize_conserves_area_and_connectivity_with_interior_hole():
    """Hole-adjacent sliver absorption must not merge across an interior hole.

    Pre-fix, ``_absorb_sliver_cells`` picked merge hosts by lattice index
    only, so a hole-side sliver could merge into the cell on the FAR side
    of the hole — producing (a) a disconnected group whose small piece is
    silently dropped by ``_union_atoms_to_shape_part`` (area loss, B6
    path) or (b) a point-pinched region (near-point neck → unrealistic
    tab). The fix requires the merged result to survive a small erosion
    (``_MERGE_NECK_EPS``).

    Geometry reproduces the first real-world trigger: a rectangular floor
    with a floating interior stair hole (ResearchBIM_synthetic-bim
    integration, seed-7 1F — PlanBIM 142 §10).
    """
    # Full-precision coords — the trigger is precision-sensitive (atom
    # centroids decide the absorption path; rounded coords miss it).
    ext = (
        (0.0, 0.0),
        (9.750572799628003, 0.0),
        (9.750572799628003, 11.383282805817453),
        (0.0, 11.383282805817453),
    )
    hole = (  # CW interior ring — floating stair core, 2.5 × 4.0 m
        (3.6252863998140015, 3.6916414029087266),
        (3.6252863998140015, 7.6916414029087266),
        (6.1252863998140015, 7.6916414029087266),
        (6.1252863998140015, 3.6916414029087266),
    )
    floor = FloorShape(
        level=1,
        parts=[ShapePart(exterior=ext, holes=(hole,))],
        floor_to_floor_height=3.0,
    )
    atoms = atomize(floor)
    regions = regionize(floor, atoms=atoms)

    # (a) area conservation — no silently dropped disconnected pieces.
    atom_area = sum(a.area for a in atoms)
    region_area = sum(_area(r) for r in regions)
    assert region_area == pytest.approx(atom_area, abs=1e-6)

    # (b) no point-pinched region — every region survives the merge-neck
    # erosion the absorption fix guarantees (_MERGE_NECK_EPS).
    for r in regions:
        eroded = to_shapely(r.shape).buffer(-_MERGE_NECK_EPS)
        assert eroded.geom_type == "Polygon" and not eroded.is_empty, (
            f"region {r.region_id} is point-pinched or degenerate"
        )


def test_absorb_rejects_gap_merge_even_for_thin_sliver():
    """erosion 게이트의 구멍 (리뷰 2026-06-12): 전체 폭 < 2×_MERGE_NECK_EPS 인
    sliver 는 buffer(-EPS) 가 끊긴 조각을 *통째로 지워* 단일 Polygon 으로 오판
    → 떨어진 host 와 병합 → `_union_atoms_to_shape_part` 가 작은 조각을 버림
    (무음 area 손실, B6 재발). 연결성 선체크(union 이 Polygon 인가)가 막아야 한다.
    """
    from room_layout.stages.regionize import _absorb_sliver_cells  # noqa: PLC0415

    def _atom(aid, sp):
        return Atom(
            atom_id=aid,
            shape=sp,
            part_id=0,
            piece_id=0,
            theta=0.0,
            is_feature_sliver=False,
        )

    # 폭 5cm(< 0.06) sliver — 격자번호상 host 와 인접하지만 실제론 0.45m 떨어짐
    thin = _atom(0, ShapePart(exterior=((0, 0), (0.05, 0), (0.05, 2), (0, 2))))
    fat = _atom(1, _rect(0.5, 0, 2.5, 2))
    cells = [
        ([(thin, (0.025, 1.0), (0, 0, 0.05, 2), 0.1)], [], 0, 0),
        ([(fat, (1.5, 1.0), (0.5, 0, 2.5, 2), 4.0)], [], 1, 0),
    ]
    out = _absorb_sliver_cells(cells)
    assert len(out) == 2, (
        "떨어진 host 와 병합됨 — 얇은 sliver 가 erosion 게이트를 우회 (area 손실 경로)"
    )
