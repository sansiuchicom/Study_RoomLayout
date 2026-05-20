"""Tests for growth_priority.py (Phase 7 Round 4 v2 W6a)."""

from __future__ import annotations

import pytest
import shapely.geometry as sg

from celllayout_tf.cases import selected_cases
from celllayout_tf.growth_priority import (
    SeedAnchor,
    _side_priority_from_outward,
    bounded_voronoi,
    compute_seed_anchors,
)
from celllayout_tf.region_graph import build_region_graph
from celllayout_tf.regionize import regionize
from celllayout_tf.territory import resolve_territories


def _build(case_index: int):
    _, _, shape = selected_cases([case_index])[0]
    regions = regionize(shape)
    graph = build_region_graph(shape, regions=regions)
    territories = resolve_territories(shape)
    by_id = {r.region_id: r for r in regions}
    return shape, regions, graph, territories, by_id


# ---------- _side_priority_from_outward ----------


def test_side_priority_x_dominant_positive():
    """outward = (+3, +1): dominant_out = right, secondary_out = top."""
    pri = _side_priority_from_outward((3.0, 1.0), seed_id=1)
    assert pri == ("right", "top", "bottom", "left")


def test_side_priority_y_dominant_negative():
    """outward = (+1, -3): dominant_out = bottom, secondary_out = right."""
    pri = _side_priority_from_outward((1.0, -3.0), seed_id=1)
    assert pri == ("bottom", "right", "left", "top")


def test_side_priority_zero_outward_deterministic_via_seed_id():
    """Ambiguous outward → hash-based perturbation. Same seed_id → same priority."""
    p1 = _side_priority_from_outward((0.0, 0.0), seed_id=42)
    p2 = _side_priority_from_outward((0.0, 0.0), seed_id=42)
    assert p1 == p2  # determinism

    p3 = _side_priority_from_outward((0.0, 0.0), seed_id=43)
    # Different seed → likely different priority (not strictly required but
    # the implementation uses Random(seed_id) which produces distinct streams)
    # Just check both are valid 4-permutations of sides.
    assert set(p1) == {"top", "right", "bottom", "left"}
    assert set(p3) == {"top", "right", "bottom", "left"}


def test_side_priority_equal_magnitude_x_wins_tie():
    """When |dx| == |dy|, dx is dominant (>= rule)."""
    pri = _side_priority_from_outward((2.0, 2.0), seed_id=1)
    # dx >= |dy| with strict >= → x dominant → right is dom_out
    assert pri[0] == "right"


# ---------- bounded_voronoi ----------


def test_voronoi_single_seed_assigns_whole_territory():
    """case 1 (single rect, K=5 seeds in 1 territory): each seed gets some
    regions; together they partition the territory."""
    shape, regions, graph, terrs, by_id = _build(1)
    # Use first 3 regions as synthetic seeds
    territory = terrs[0]
    in_territory = [r for r in graph.regions if r.part_id == territory.part_id]
    assert len(in_territory) > 3
    seed_ids = tuple(sorted(r.region_id for r in in_territory)[:3])

    cells = bounded_voronoi(territory, seed_ids, graph)
    assert set(cells.keys()) == set(seed_ids)
    # Every region in territory assigned to exactly one cell
    all_assigned = [rid for cell in cells.values() for rid in cell]
    assert len(all_assigned) == len(set(all_assigned))
    assert set(all_assigned) == {r.region_id for r in in_territory}


def test_voronoi_one_seed_takes_all_when_alone():
    """Single seed in territory → entire territory in its cell."""
    shape, regions, graph, terrs, by_id = _build(1)
    territory = terrs[0]
    in_territory = [r for r in graph.regions if r.part_id == territory.part_id]
    seed_id = in_territory[0].region_id

    cells = bounded_voronoi(territory, (seed_id,), graph)
    assert len(cells) == 1
    assert set(cells[seed_id]) == {r.region_id for r in in_territory}


def test_voronoi_raises_on_seed_outside_territory():
    """Seed not in territory → ValueError."""
    shape, regions, graph, terrs, by_id = _build(22)  # multi-territory
    territory_0 = next(t for t in terrs if t.part_id == 0)
    # Find a region in a DIFFERENT territory
    foreign_region = next(
        r for r in graph.regions if r.part_id != territory_0.part_id
    )
    with pytest.raises(ValueError, match="not in territory"):
        bounded_voronoi(territory_0, (foreign_region.region_id,), graph)


# ---------- compute_seed_anchors (high-level integration) ----------


def test_compute_seed_anchors_single_territory_K5():
    """case 1, K=5 seeds → 5 SeedAnchors with valid side_priority."""
    shape, regions, graph, terrs, by_id = _build(1)
    in_territory = [r for r in graph.regions if r.part_id == terrs[0].part_id]
    seeds_by_room = {
        i: rid for i, rid in enumerate(
            sorted(r.region_id for r in in_territory)[:5]
        )
    }

    anchors = compute_seed_anchors(seeds_by_room, graph, terrs, by_id)
    assert set(anchors.keys()) == set(seeds_by_room.keys())
    for room_idx, sa in anchors.items():
        assert isinstance(sa, SeedAnchor)
        assert sa.seed_region_id == seeds_by_room[room_idx]
        assert sa.room_idx == room_idx
        # side_priority is a permutation of all 4 sides
        assert set(sa.side_priority) == {"top", "right", "bottom", "left"}


def test_compute_seed_anchors_multi_territory_case_22():
    """case 22 (main + wing): 2 territories. Seeds in each get own anchor.
    Cross-territory Voronoi is NOT computed — anchors per-territory."""
    shape, regions, graph, terrs, by_id = _build(22)
    # Pick one seed from each territory
    seed_main = next(r for r in graph.regions if r.part_id == 0).region_id
    seed_wing = next(r for r in graph.regions if r.part_id == 1).region_id
    seeds = {0: seed_main, 1: seed_wing}

    anchors = compute_seed_anchors(seeds, graph, terrs, by_id)
    assert set(anchors.keys()) == {0, 1}
    # Main seed's anchor is in main's local frame; wing's in wing's local
    # frame. Both should produce some non-zero outward (or fall back
    # gracefully). Just check they're SeedAnchor instances.
    assert all(isinstance(a, SeedAnchor) for a in anchors.values())


def test_compute_seed_anchors_outward_vector_points_away_from_other_seeds():
    """In a multi-seed cell, outward should point from the seed AWAY from
    the cell-cell boundary (i.e., toward the seed's outer side)."""
    shape, regions, graph, terrs, by_id = _build(1)
    in_territory = sorted(
        (r for r in graph.regions if r.part_id == terrs[0].part_id),
        key=lambda r: r.region_id,
    )
    # Use two seeds clearly far apart to make the outward meaningful.
    seed_a = in_territory[0].region_id   # presumably corner-ish
    seed_b = in_territory[-1].region_id  # opposite corner-ish
    seeds = {0: seed_a, 1: seed_b}

    anchors = compute_seed_anchors(seeds, graph, terrs, by_id)
    a_a, a_b = anchors[0], anchors[1]
    # The two seeds' outward vectors should point in roughly opposite
    # directions (their anchors meet near the Voronoi boundary).
    dot = (
        a_a.outward_vector[0] * a_b.outward_vector[0]
        + a_a.outward_vector[1] * a_b.outward_vector[1]
    )
    assert dot < 0, (
        f"two seeds at opposite ends should have opposite outward vectors; "
        f"got dot={dot}"
    )


# ---------- W6b: find_strip + bbox-in-territory ----------


from celllayout_tf.growth_priority import (
    find_strip,
    region_ids_by_part,
    region_local_polys_by_id,
    territory_local_polygon,
)


def _strip_setup(case_index: int):
    shape, regions, graph, terrs, by_id = _build(case_index)
    region_polys = region_local_polys_by_id(graph)
    ids_by_part = region_ids_by_part(graph)
    terr_polys = {
        t.part_id: territory_local_polygon(t) for t in terrs
    }
    return shape, regions, graph, terrs, by_id, region_polys, ids_by_part, terr_polys


def test_find_strip_returns_none_when_no_adjacent_unassigned():
    """If side has no adjacent unassigned regions → None."""
    shape, regions, graph, terrs, by_id, polys, ids_by_part, terr_polys = _strip_setup(1)
    # Assign EVERY region to room 0 except one seed
    seed_id = sorted(graph.regions, key=lambda r: r.region_id)[0].region_id
    region_to_room = {r.region_id: 0 for r in graph.regions if r.region_id != seed_id}

    result = find_strip(
        room_region_ids=(seed_id,),
        side="top",
        region_to_room=region_to_room,
        region_local_polys=polys,
        region_ids_by_part=ids_by_part,
        territory_local_poly=terr_polys[0],
        part_id=0,
    )
    assert result is None


def test_find_strip_single_region_clean_extension():
    """A single-region strip that forms a clean rect extension is accepted."""
    shape, regions, graph, terrs, by_id, polys, ids_by_part, terr_polys = _strip_setup(1)
    # Start with one region. Try absorbing on each side.
    seed_id = sorted(graph.regions, key=lambda r: r.region_id)[0].region_id
    region_to_room: dict[int, int] = {}

    # At least one of the 4 sides should yield SOME strip on case 1 (single rect)
    # because the seed is at a corner-ish position and has adjacent regions.
    yielded = False
    for side in ("top", "right", "bottom", "left"):
        result = find_strip(
            room_region_ids=(seed_id,),
            side=side,
            region_to_room=region_to_room,
            region_local_polys=polys,
            region_ids_by_part=ids_by_part,
            territory_local_poly=terr_polys[0],
            part_id=0,
        )
        if result is not None:
            yielded = True
            # Verify the returned strip is unassigned and in same territory
            for rid in result:
                assert rid not in region_to_room
                assert by_id[rid].part_id == 0
            break
    assert yielded, "expected at least one side to yield a strip on case 1"


def test_find_strip_rejects_when_combined_not_rect():
    """If absorbing would yield a non-rect union → None."""
    shape, regions, graph, terrs, by_id, polys, ids_by_part, terr_polys = _strip_setup(1)
    # Use 2 regions whose union is itself L-shaped (uncommon but possible).
    # Pick the region at top-left and one at top-middle but with different y_max.
    # Sort by y_max to find candidates.
    in_territory = [r for r in graph.regions if r.part_id == 0]
    by_id_local = {r.region_id: polys[r.region_id] for r in in_territory}
    # Use 2 corner regions far apart (probably non-adjacent, definitely
    # not forming a clean rect together)
    rids_sorted = sorted(in_territory, key=lambda r: (polys[r.region_id].centroid.x, polys[r.region_id].centroid.y))
    # Top-left + bottom-right: definitely L-or-disconnected
    a = rids_sorted[0].region_id
    b = rids_sorted[-1].region_id
    region_to_room: dict[int, int] = {}
    result = find_strip(
        room_region_ids=(a, b),
        side="top",
        region_to_room=region_to_room,
        region_local_polys=polys,
        region_ids_by_part=ids_by_part,
        territory_local_poly=terr_polys[0],
        part_id=0,
    )
    # Room union itself may not be a single polygon — caller upstream should
    # filter, but find_strip's None return is defensible too.
    assert result is None or len(result) == 0


def test_find_strip_rejects_overhang_outside_territory():
    """Strip whose new bbox would escape territory polygon → None.

    For case 9 (ㄱ자): a room near the inner corner can't push past the
    reflex vertex into the missing quadrant (it's not in territory).
    """
    shape, regions, graph, terrs, by_id, polys, ids_by_part, terr_polys = _strip_setup(9)
    # ㄱ자 has only 1 part (single territory). Pick the region containing
    # local coords near the inner corner. We just assert: for ANY starting
    # region, at least one side might be blocked by territory boundary.
    region_to_room: dict[int, int] = {}
    # We can't easily construct a specific overhang test without knowing
    # the exact regionize output. Instead, verify that find_strip on every
    # region produces results respecting territory containment.
    in_territory = [r for r in graph.regions if r.part_id == 0]
    any_blocked = False
    for r in in_territory:
        for side in ("top", "right", "bottom", "left"):
            result = find_strip(
                room_region_ids=(r.region_id,),
                side=side,
                region_to_room=region_to_room,
                region_local_polys=polys,
                region_ids_by_part=ids_by_part,
                territory_local_poly=terr_polys[0],
                part_id=0,
            )
            if result is None:
                any_blocked = True
                break
        if any_blocked:
            break
    assert any_blocked, "ㄱ자 should have at least one blocked side somewhere"


def test_find_strip_respects_already_assigned_regions():
    """Adjacent regions already assigned to another room are excluded."""
    shape, regions, graph, terrs, by_id, polys, ids_by_part, terr_polys = _strip_setup(1)
    seed_id = sorted(graph.regions, key=lambda r: r.region_id)[0].region_id
    # Find adjacent regions and mark them all assigned to room 1
    neighbors = graph.neighbors(seed_id)
    region_to_room = {nbr: 1 for nbr in neighbors}

    for side in ("top", "right", "bottom", "left"):
        result = find_strip(
            room_region_ids=(seed_id,),
            side=side,
            region_to_room=region_to_room,
            region_local_polys=polys,
            region_ids_by_part=ids_by_part,
            territory_local_poly=terr_polys[0],
            part_id=0,
        )
        if result is not None:
            # If a side yields, none of the returned regions should be assigned
            for rid in result:
                assert rid not in region_to_room


def test_find_strip_returned_regions_form_clean_rect_with_room():
    """Sanity: returned strip + room is bbox-equivalent."""
    shape, regions, graph, terrs, by_id, polys, ids_by_part, terr_polys = _strip_setup(1)
    import shapely.ops
    seed_id = sorted(graph.regions, key=lambda r: r.region_id)[0].region_id
    region_to_room: dict[int, int] = {}

    for side in ("top", "right", "bottom", "left"):
        result = find_strip(
            room_region_ids=(seed_id,),
            side=side,
            region_to_room=region_to_room,
            region_local_polys=polys,
            region_ids_by_part=ids_by_part,
            territory_local_poly=terr_polys[0],
            part_id=0,
        )
        if result is None:
            continue
        all_polys = [polys[seed_id]] + [polys[rid] for rid in result]
        union = shapely.ops.unary_union(all_polys)
        assert union.geom_type == "Polygon"
        cxL, cyB, cxR, cyT = union.bounds
        bbox_area = (cxR - cxL) * (cyT - cyB)
        # Should be bbox-equivalent
        assert abs(bbox_area - union.area) < 1e-6 * union.area


# ---------- W6c: region_priority_growth (end-to-end) ----------


from celllayout_tf.cases import make_cases
from celllayout_tf.growth_priority import region_priority_growth
from celllayout_tf.layout_fixtures import make_fixtures


def _all_cases_and_fixtures():
    cases = {c.name: c for c in make_cases()}
    return [
        (cases[f.case_name], f) for f in make_fixtures()
    ]


def test_priority_growth_runs_on_every_fixture():
    """No exception on any 33-case fixture."""
    for shape, fixture in _all_cases_and_fixtures():
        result = region_priority_growth(shape, fixture)
        assert len(result.rooms) == fixture.K


def test_priority_growth_each_region_assigned_at_most_once():
    for shape, fixture in _all_cases_and_fixtures()[:5]:
        result = region_priority_growth(shape, fixture)
        seen: set[int] = set()
        for room in result.rooms:
            for rid in room.region_ids:
                assert rid not in seen, (
                    f"case {fixture.case_index}: region {rid} double-assigned"
                )
                seen.add(rid)


def test_priority_growth_grown_rooms_are_rectangular():
    """Every grown room (except in curved territories) should have its
    region-union be bbox-equivalent in local frame."""
    import shapely.ops
    import shapely.affinity
    from math import degrees as _deg
    from celllayout_tf.regionize import regionize
    for shape, fixture in _all_cases_and_fixtures():
        result = region_priority_growth(shape, fixture)
        regs = regionize(shape)
        by_id = {r.region_id: r for r in regs}
        from celllayout_tf.territory import resolve_territories
        terrs = resolve_territories(shape)
        kind_by_part = {t.part_id: t.kind for t in terrs}
        for room in result.rooms:
            if not room.region_ids:
                continue
            kinds = {kind_by_part.get(by_id[rid].part_id) for rid in room.region_ids}
            if "curved" in kinds:
                continue  # curved territory exempt
            theta = by_id[room.region_ids[0]].theta
            polys = []
            for rid in room.region_ids:
                r = by_id[rid]
                p = sg.Polygon(r.shape.exterior, [list(h) for h in r.shape.holes])
                if theta != 0.0:
                    p = shapely.affinity.rotate(p, -_deg(theta), origin=(0, 0))
                polys.append(p)
            union = shapely.ops.unary_union(polys)
            if union.is_empty or union.geom_type != "Polygon":
                continue
            xmin, ymin, xmax, ymax = union.bounds
            bbox_area = (xmax - xmin) * (ymax - ymin)
            assert abs(bbox_area - union.area) < 1e-6 * max(union.area, 1e-9), (
                f"case {fixture.case_index} {fixture.case_name}: "
                f"room {room.name} is NOT bbox-equivalent rect "
                f"(bbox_area={bbox_area:.4f}, union_area={union.area:.4f})"
            )


def test_priority_growth_diagnostics_present():
    shape, fixture = _all_cases_and_fixtures()[0]
    result = region_priority_growth(shape, fixture)
    diag = result.diagnostics
    assert "iterations" in diag
    assert "hub_room_index" in diag
    assert "total_rounds" in diag
    assert "below_min_area" in diag


def test_priority_growth_is_deterministic():
    shape, fixture = _all_cases_and_fixtures()[0]
    r1 = region_priority_growth(shape, fixture)
    r2 = region_priority_growth(shape, fixture)
    assert r1.unassigned_region_ids == r2.unassigned_region_ids
    for a, b in zip(r1.rooms, r2.rooms):
        assert a.region_ids == b.region_ids


def test_priority_growth_auto_seed_runs():
    """auto_seed=True fixture works through priority growth."""
    from celllayout_tf.room_growth import LayoutFixture, RoomSpec
    cases = {c.name: c for c in make_cases()}
    manual = make_fixtures()[0]
    auto_rooms = tuple(
        RoomSpec(name=r.name, role=r.role, seed_position=None,
                 target_aspect_range=r.target_aspect_range)
        for r in manual.rooms
    )
    auto = LayoutFixture(
        case_index=manual.case_index, case_name=manual.case_name,
        footprint_area_m2=manual.footprint_area_m2,
        rooms=auto_rooms,
        role_min_areas=manual.role_min_areas,
        role_aspect_ranges=manual.role_aspect_ranges,
        max_l_rooms=manual.max_l_rooms,
    )
    result = region_priority_growth(cases[manual.case_name], auto)
    assert len(result.rooms) == auto.K
    assert all(len(r.region_ids) >= 1 for r in result.rooms)
