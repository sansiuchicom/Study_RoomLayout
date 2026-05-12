import shapely.affinity as sa
from shapely.geometry import box
from shapely.ops import unary_union

from celllayout_tf.cases import make_cases
from celllayout_tf.zoning import zone_footprint


def test_planner_splits_rectangle_to_requested_k():
    result = zone_footprint(box(0, 0, 10, 10), k=4)

    assert result.planning.requested_k == 4
    assert len(result.planning.cuts) == 3
    assert len(result.zones) == 4
    assert len(result.subdivision.faces) == 4
    assert result.validation.ok
    assert sorted(round(zone.polygon.area, 6) for zone in result.zones) == [25, 25, 25, 25]


def test_planner_splits_l_shape_without_gap_or_overlap():
    footprint = unary_union([box(0, 0, 10, 4), box(0, 4, 4, 10)])

    result = zone_footprint(footprint, k=3)

    assert len(result.zones) == 3
    assert result.validation.ok


def test_planner_respects_hole_footprint():
    hole = box(4, 4, 6, 6)
    footprint = box(0, 0, 10, 10).difference(hole)

    result = zone_footprint(footprint, k=4)

    assert len(result.zones) == 4
    assert result.validation.ok
    assert all(zone.polygon.intersection(hole).area == 0 for zone in result.zones)


def test_planner_handles_rotated_footprint_without_topology_errors():
    footprint = sa.rotate(box(0, 0, 12, 8), 30, origin=(6, 4))

    result = zone_footprint(footprint, k=4)

    assert len(result.zones) == 4
    assert result.validation.ok


def test_planner_keeps_all_showcase_cases_topologically_valid():
    for name, footprint in make_cases():
        result = zone_footprint(footprint)

        assert result.validation.ok, name
