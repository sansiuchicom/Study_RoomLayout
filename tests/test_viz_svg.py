"""Structural SVG renderer tests (Step 08 §4.7 / S08-D5).

Asserts *structure*, not bytes — layer count / order / class names, per-layer
element presence + counts, valid XML, footprint = single union path, role-fill
colors from the palette, coords inside the viewBox. SVG byte-goldens are
float/attr-order brittle (same reasoning as the matplotlib smoke tests).

``viz/svg.py`` is matplotlib-free (pure stdlib + shapely), so these run without
the viz extra.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from shapely.geometry import Polygon
from tests._fixtures import load_growth_fixture

from room_layout import run
from room_layout.schema import (
    FloorShape,
    LabeledFloorLayout,
    ProgramRequest,
    ShapeInput,
    SpaceUnitSpec,
    from_dict,
)
from room_layout.schema.geometry import ShapePart, VerticalAnchor
from room_layout.schema.output import LabeledRoom
from room_layout.viz import palette
from room_layout.viz.svg import render

GOLDEN = Path(__file__).parent / "golden"


def _shape_and_program(case: str):
    with (GOLDEN / case / "input.json").open(encoding="utf-8") as f:
        shape = from_dict(ShapeInput, json.load(f)["shape"])
    level = shape.floors[0].level
    fx = load_growth_fixture(GOLDEN / case)
    specs = [
        SpaceUnitSpec(id=r.name, role=r.role, usage=None, area_min_m2=0.5, required=True)
        for r in fx.rooms
    ]
    return shape, ProgramRequest(target_type="apartment", floor_programs={level: specs})


def _local(elem) -> str:
    return elem.tag.rsplit("}", 1)[-1]


def _render_case(case: str, tmp_path: Path):
    shape, program = _shape_and_program(case)
    result = run(shape, program, seed=42)
    out = render(
        shape.floors[0],
        result.floors[0],
        tmp_path / f"{case}.svg",
        anchors=shape.vertical_anchors,
    )
    return shape, result, ET.parse(out).getroot()


def _layer(root, cls: str):
    return next(g for g in root if g.attrib.get("class") == cls)


def _paths(g):
    return [c for c in g if _local(c) == "path"]


# --- layer structure -------------------------------------------------------


def test_layer_order_count_and_classes(tmp_path):
    _, _, root = _render_case("case_01_30py_flat", tmp_path)
    assert _local(root) == "svg"
    groups = [g for g in root if _local(g) == "g"]
    assert len(groups) == 12
    classes = [g.attrib["class"] for g in groups]
    assert classes == [f"layer-{i:02d}-{n}" for i, n in enumerate(palette.LAYER_ORDER)]


def test_unlit_debug_layers_are_empty_groups(tmp_path):
    # the empty-group contract (S08-D2): the final render leaves the geometry-
    # debug + failure layers empty, but the <g> placeholders still exist.
    _, _, root = _render_case("case_01_30py_flat", tmp_path)
    for name in ("atoms", "regions", "region-graph", "seeds", "grown", "failure"):
        idx = palette.LAYER_ORDER.index(name)
        g = _layer(root, f"layer-{idx:02d}-{name}")
        assert list(g) == [], f"{name} should be empty in the final render"


# --- footprint (S08-D8 union) ----------------------------------------------


def test_footprint_is_single_union_path_for_multipart(tmp_path):
    # case_04 footprint is 3 overlapping design primitives; the renderer must
    # outline their union (one perimeter), not each part (phantom seam boxes).
    shape, _, root = _render_case("case_04_50py_c_shape", tmp_path)
    assert len(shape.floors[0].parts) > 1
    fp = _layer(root, "layer-01-footprint")
    assert len(_paths(fp)) == 1


def test_footprint_single_part_is_single_path(tmp_path):
    shape, _, root = _render_case("case_01_30py_flat", tmp_path)
    assert len(shape.floors[0].parts) == 1
    assert len(_paths(_layer(root, "layer-01-footprint"))) == 1


# --- rooms / corridor ------------------------------------------------------


def test_rooms_filled_by_palette_role_color(tmp_path):
    _, result, root = _render_case("case_01_30py_flat", tmp_path)
    rooms = _paths(_layer(root, "layer-09-rooms"))
    assert len(rooms) == len(result.floors[0].rooms)
    allowed = set(palette.ROLE_COLORS.values()) | {palette.ROLE_FALLBACK_COLOR}
    for p in rooms:
        assert p.attrib["fill"] in allowed


def test_corridor_paths_match_polygon_count(tmp_path):
    _, result, root = _render_case("case_04_50py_c_shape", tmp_path)
    n = len(result.floors[0].corridor_polygons)
    assert n >= 1  # case_04 carves a corridor
    assert len(_paths(_layer(root, "layer-08-corridor"))) == n


def test_grid_layer_has_lines(tmp_path):
    _, _, root = _render_case("case_01_30py_flat", tmp_path)
    grid = _layer(root, "layer-00-grid")
    assert any(_local(c) == "line" for c in grid)


# --- viewBox / coordinate transform ----------------------------------------


def test_footprint_coords_inside_viewbox(tmp_path):
    _, _, root = _render_case("case_04_50py_c_shape", tmp_path)
    _, _, vb_w, vb_h = (float(v) for v in root.attrib["viewBox"].split())
    d = _paths(_layer(root, "layer-01-footprint"))[0].attrib["d"]
    nums = [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", d)]
    xs, ys = nums[0::2], nums[1::2]
    eps = 1e-6
    assert all(-eps <= x <= vb_w + eps for x in xs)
    assert all(-eps <= y <= vb_h + eps for y in ys)


# --- anchors (synthetic — golden cases carry none) -------------------------


def _anchored_floor():
    floor = FloorShape(
        level=1,
        parts=[ShapePart(exterior=((0, 0), (10, 0), (10, 8), (0, 8)))],
        floor_to_floor_height=3.0,
    )
    rooms = [
        LabeledRoom(
            id="stair",
            polygon=Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
            role="vertical_circulation",
            usage=None,
            area_m2=4.0,
            anchor_id="s1",
        )
    ]
    layout = LabeledFloorLayout(level=1, rooms=rooms, corridor_polygons=[])
    anchors = [
        VerticalAnchor(
            id="s1",
            kind="stair_core",
            footprint_polygon=Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
            floor_range=(1, 3),
            host_role="vertical_circulation",
        ),
        VerticalAnchor(
            id="ps",
            kind="ps_shaft",
            footprint_polygon=Polygon([(8, 6), (9, 6), (9, 7), (8, 7)]),
            floor_range=(1, 3),
            host_role=None,
        ),
    ]
    return floor, layout, anchors


def test_anchors_layer_drawn_when_passed(tmp_path):
    floor, layout, anchors = _anchored_floor()
    root = ET.parse(render(floor, layout, tmp_path / "a.svg", anchors=anchors)).getroot()
    assert len(_paths(_layer(root, "layer-05-anchors"))) == 2  # vc outline + forbidden shaft
    # vc also appears as a role-filled room
    assert len(_paths(_layer(root, "layer-09-rooms"))) == 1


def test_anchors_layer_empty_when_absent(tmp_path):
    floor, layout, _ = _anchored_floor()
    root = ET.parse(render(floor, layout, tmp_path / "a.svg")).getroot()
    assert list(_layer(root, "layer-05-anchors")) == []


def test_anchor_filtered_by_floor_level(tmp_path):
    floor, layout, anchors = _anchored_floor()
    # both anchors span floors 1–3; on level 1 both draw
    root = ET.parse(render(floor, layout, tmp_path / "a.svg", anchors=anchors)).getroot()
    assert len(_paths(_layer(root, "layer-05-anchors"))) == 2
    # an anchor that does not reach this floor is skipped
    off = VerticalAnchor(
        id="x",
        kind="ps_shaft",
        footprint_polygon=Polygon([(5, 5), (6, 5), (6, 6), (5, 6)]),
        floor_range=(8, 9),
        host_role=None,
    )
    root2 = ET.parse(render(floor, layout, tmp_path / "b.svg", anchors=[off])).getroot()
    assert list(_layer(root2, "layer-05-anchors")) == []
