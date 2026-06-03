"""Polygonization tests (Step 07 §4.2) — region-id sets → room / corridor polygons.

Synthetic unit tests pin the core contract (edge-adjacent regions → one CCW
Polygon; loud ``GeometryFailure`` on disconnected / empty rooms; corridor
multi-component → list). The 33-case sweep proves area conservation +
single-Polygon rooms on real growth/carve output (S07-D5: 0/137 disconnected),
and re-confirms the 4 known multi-component corridor cases from the probe.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from shapely.geometry import Polygon
from tests._fixtures import load_growth_fixture

from room_layout.schema import ShapeInput, from_dict
from room_layout.schema.failure import GeometryFailure
from room_layout.stages.atomize import atomize
from room_layout.stages.corridor import carve_corridors
from room_layout.stages.growth_partition import region_partition_growth
from room_layout.stages.polygonize import (
    build_region_polygons,
    polygonize_corridors,
    polygonize_room,
)
from room_layout.stages.region_graph import build_region_graph
from room_layout.stages.regionize import regionize

GOLDEN = Path(__file__).parent / "golden"

# Corridor sets that the S07-D5 probe found to be multi-component (the carved
# base ∪ shortcut set splits into ≥2 pieces). Goldens are byte-identical to
# Cell, so this is a stable regression lock.
MULTI_COMPONENT_CORRIDOR_CASES = {
    "case_04_50py_c_shape",
    "case_10_l_shape_thick",
    "case_32_60py_big_l_shape",
    "case_33_donut_wing",
}


# ---- synthetic unit tests -------------------------------------------------


def _sq(x0: float, y0: float, s: float = 1.0) -> Polygon:
    return Polygon([(x0, y0), (x0 + s, y0), (x0 + s, y0 + s), (x0, y0 + s)])


def test_room_edge_adjacent_regions_merge_to_one_ccw_polygon():
    region_poly = {0: _sq(0, 0), 1: _sq(1, 0)}  # share the x=1 edge
    poly = polygonize_room((0, 1), region_poly, room_name="r")
    assert poly.geom_type == "Polygon"
    assert poly.area == pytest.approx(2.0)
    assert poly.exterior.is_ccw  # contract §2.4: CCW


def test_room_disjoint_regions_raise_disconnected():
    region_poly = {0: _sq(0, 0), 1: _sq(5, 5)}  # no contact
    with pytest.raises(GeometryFailure) as exc:
        polygonize_room((0, 1), region_poly, room_name="bedroom_1")
    assert exc.value.record.code == "ROOM_DISCONNECTED"
    assert exc.value.record.stage == "polygonize"
    assert exc.value.record.data["room"] == "bedroom_1"


def test_room_corner_only_touch_raises_disconnected():
    region_poly = {0: _sq(0, 0), 1: _sq(1, 1)}  # touch at the (1,1) corner only
    with pytest.raises(GeometryFailure) as exc:
        polygonize_room((0, 1), region_poly, room_name="r")
    assert exc.value.record.code == "ROOM_DISCONNECTED"


def test_room_empty_region_ids_raise_empty():
    with pytest.raises(GeometryFailure) as exc:
        polygonize_room((), {}, room_name="r")
    assert exc.value.record.code == "ROOM_EMPTY"


def test_corridor_multi_component_returns_list():
    region_poly = {0: _sq(0, 0), 1: _sq(5, 5)}  # two disjoint corridor pieces
    polys = polygonize_corridors((0, 1), region_poly)
    assert len(polys) == 2
    assert all(p.geom_type == "Polygon" and p.exterior.is_ccw for p in polys)


def test_corridor_connected_returns_single():
    polys = polygonize_corridors((0, 1), {0: _sq(0, 0), 1: _sq(1, 0)})
    assert len(polys) == 1
    assert polys[0].area == pytest.approx(2.0)


def test_corridor_empty_returns_empty_list():
    assert polygonize_corridors((), {}) == []


# ---- 33-case sweep on real growth/carve output ----------------------------


def _carve(case_dir: Path):
    with (case_dir / "input.json").open(encoding="utf-8") as f:
        floor = from_dict(ShapeInput, json.load(f)["shape"]).floors[0]
    fixture = load_growth_fixture(case_dir)
    atoms = atomize(floor)
    regions = regionize(floor, atoms=atoms)
    rg = build_region_graph(floor, atoms=atoms, regions=regions)
    growth = region_partition_growth(floor, fixture, regions=regions, region_graph=rg)
    return carve_corridors(floor, growth, regions=regions, region_graph=rg), regions


_CASES = sorted(p.name for p in GOLDEN.iterdir() if p.is_dir())


@pytest.mark.parametrize("case", _CASES)
def test_all_rooms_polygonize_to_single_polygon_area_conserved(case):
    cl, regions = _carve(GOLDEN / case)
    region_poly = build_region_polygons(regions)
    n = 0
    for gr in cl.rooms:
        if not gr.region_ids:
            continue
        n += 1
        poly = polygonize_room(gr.region_ids, region_poly, room_name=gr.name)
        assert poly.geom_type == "Polygon"
        assert poly.is_valid
        expected = sum(region_poly[rid].area for rid in gr.region_ids)
        assert poly.area == pytest.approx(expected, abs=1e-6)
    assert n > 0  # the case actually produced rooms


@pytest.mark.parametrize("case", _CASES)
def test_corridors_polygonize_to_valid_ccw_components(case):
    cl, regions = _carve(GOLDEN / case)
    region_poly = build_region_polygons(regions)
    polys = polygonize_corridors(cl.corridor_region_ids, region_poly)
    assert all(p.geom_type == "Polygon" and p.is_valid and p.exterior.is_ccw for p in polys)
    # area conservation across the components
    expected = sum(region_poly[rid].area for rid in cl.corridor_region_ids)
    assert sum(p.area for p in polys) == pytest.approx(expected, abs=1e-6)
    if case in MULTI_COMPONENT_CORRIDOR_CASES:
        assert len(polys) >= 2  # S07-D5 probe finding (stable golden)
