"""Tests for `room_layout.schema.geometry` — work item 4.8 / Plan §4.8.

Covers all geometry input types and their `__post_init__` structural
checks (S02-D6 / S02-D10 / S02-D12):

- `ShapePart` orientation (CCW exterior + CW holes) + degenerate / self-
  intersection rejection.
- `VerticalAnchor` kind↔host_role 5×1 matrix + `floor_range` ordering.
- `FloorShape` non-empty `parts` + positive `floor_to_floor_height`.
- `ShapeInput` non-empty `name` + `floors`.
- Frozen-input contract (S02-D3) for every type.
"""

from dataclasses import FrozenInstanceError

import pytest
from shapely.geometry import Polygon

from room_layout.schema.geometry import (
    FloorShape,
    ShapeInput,
    ShapePart,
    VerticalAnchor,
)

_CCW_SQUARE = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))
_CW_HOLE = ((2.0, 2.0), (2.0, 5.0), (5.0, 5.0), (5.0, 2.0))


# --- ShapePart ---


def test_shape_part_valid_ccw_exterior():
    sp = ShapePart(exterior=_CCW_SQUARE)
    assert sp.holes == ()


def test_shape_part_with_cw_hole():
    sp = ShapePart(exterior=_CCW_SQUARE, holes=(_CW_HOLE,))
    assert len(sp.holes) == 1


def test_shape_part_rejects_cw_exterior():
    cw = tuple(reversed(_CCW_SQUARE))
    with pytest.raises(ValueError, match="CCW"):
        ShapePart(exterior=cw)


def test_shape_part_rejects_ccw_hole():
    ccw_hole = tuple(reversed(_CW_HOLE))
    with pytest.raises(ValueError, match="CW"):
        ShapePart(exterior=_CCW_SQUARE, holes=(ccw_hole,))


def test_shape_part_rejects_hole_outside_exterior():
    # a CW hole placed outside the exterior — passes the per-ring checks but
    # forms an invalid polygon (S07 review: hole-inside / non-overlap unchecked).
    outside_hole = ((20.0, 20.0), (20.0, 22.0), (22.0, 22.0), (22.0, 20.0))
    with pytest.raises(ValueError, match="invalid polygon"):
        ShapePart(exterior=_CCW_SQUARE, holes=(outside_hole,))


def test_shape_part_rejects_under_three_points():
    with pytest.raises(ValueError, match="≥ 3 points"):
        ShapePart(exterior=((0.0, 0.0), (1.0, 1.0)))


def test_shape_part_rejects_collinear():
    with pytest.raises(ValueError, match="zero signed area"):
        ShapePart(exterior=((0.0, 0.0), (1.0, 0.0), (2.0, 0.0)))


def test_shape_part_rejects_bowtie():
    """Bowtie self-intersects; its shoelace sums to 0 so it hits the
    "zero signed area" branch rather than the later `is_simple` branch
    (documented in Tracker §3 — diagnostic precision known minor).
    Functional rejection still verified here.
    """
    with pytest.raises(ValueError):
        ShapePart(exterior=((0.0, 0.0), (10.0, 10.0), (10.0, 0.0), (0.0, 10.0)))


def test_shape_part_is_frozen():
    sp = ShapePart(exterior=_CCW_SQUARE)
    with pytest.raises(FrozenInstanceError):
        sp.exterior = ((1.0, 1.0), (2.0, 2.0), (3.0, 3.0))


# --- VerticalAnchor ---


def _va_polygon() -> Polygon:
    return Polygon([(0, 0), (3, 0), (3, 3), (0, 3)])


@pytest.mark.parametrize(
    "kind,host_role",
    [
        ("stair_core", "vertical_circulation"),
        ("elevator_shaft", "vertical_circulation"),
        ("ps_shaft", None),
        ("eps_shaft", None),
        ("duct_shaft", None),
    ],
)
def test_vertical_anchor_kind_host_role_matrix_valid(kind, host_role):
    """S02-D10: 5×1 kind→host_role matrix; matching pair accepted."""
    va = VerticalAnchor(
        id="a",
        kind=kind,
        footprint_polygon=_va_polygon(),
        floor_range=(1, 3),
        host_role=host_role,
    )
    assert va.host_role == host_role


@pytest.mark.parametrize(
    "kind,wrong_host",
    [
        ("stair_core", None),
        ("elevator_shaft", None),
        ("ps_shaft", "vertical_circulation"),
        ("eps_shaft", "vertical_circulation"),
        ("duct_shaft", "vertical_circulation"),
    ],
)
def test_vertical_anchor_rejects_wrong_host_role(kind, wrong_host):
    with pytest.raises(ValueError, match="host_role"):
        VerticalAnchor(
            id="a",
            kind=kind,
            footprint_polygon=_va_polygon(),
            floor_range=(1, 3),
            host_role=wrong_host,
        )


def test_vertical_anchor_rejects_inverted_floor_range():
    with pytest.raises(ValueError, match="floor_range"):
        VerticalAnchor(
            id="a",
            kind="ps_shaft",
            footprint_polygon=_va_polygon(),
            floor_range=(5, 3),
            host_role=None,
        )


@pytest.mark.parametrize("bad_kind", ["staircore", "elevator", "lift_shaft", ""])
def test_vertical_anchor_rejects_unknown_kind(bad_kind):
    """Direct-construction VerticalAnchorKind Literal validation
    (close-time cleanup — replaces the prior raw KeyError path)."""
    with pytest.raises(ValueError, match="VerticalAnchorKind Literal"):
        VerticalAnchor(
            id="a",
            kind=bad_kind,
            footprint_polygon=_va_polygon(),
            floor_range=(1, 3),
            host_role=None,
        )


def test_vertical_anchor_is_frozen():
    va = VerticalAnchor(
        id="a",
        kind="ps_shaft",
        footprint_polygon=_va_polygon(),
        floor_range=(1, 3),
        host_role=None,
    )
    with pytest.raises(FrozenInstanceError):
        va.id = "b"


# --- FloorShape ---


def _valid_part() -> ShapePart:
    return ShapePart(exterior=_CCW_SQUARE)


def test_floor_shape_valid():
    fs = FloorShape(level=1, parts=[_valid_part()], floor_to_floor_height=3.0)
    assert fs.level == 1
    assert len(fs.parts) == 1


def test_floor_shape_rejects_empty_parts():
    with pytest.raises(ValueError, match="parts"):
        FloorShape(level=1, parts=[], floor_to_floor_height=3.0)


@pytest.mark.parametrize("h", [0.0, -1.0])
def test_floor_shape_rejects_non_positive_height(h):
    with pytest.raises(ValueError, match="floor_to_floor_height"):
        FloorShape(level=1, parts=[_valid_part()], floor_to_floor_height=h)


def test_floor_shape_accepts_none_height():
    """Pipeline §2.1: `floor_to_floor_height: float | None` — required
    only for multi-floor; single-floor v1 may omit."""
    fs = FloorShape(level=1, parts=[_valid_part()], floor_to_floor_height=None)
    assert fs.floor_to_floor_height is None


def test_floor_shape_is_frozen():
    fs = FloorShape(level=1, parts=[_valid_part()], floor_to_floor_height=3.0)
    with pytest.raises(FrozenInstanceError):
        fs.level = 2


# --- ShapeInput ---


def _valid_floor() -> FloorShape:
    return FloorShape(level=1, parts=[_valid_part()], floor_to_floor_height=3.0)


def test_shape_input_valid_with_default_anchors():
    si = ShapeInput(name="demo", floors=[_valid_floor()])
    assert si.name == "demo"
    assert si.vertical_anchors == []


def test_shape_input_rejects_empty_name():
    with pytest.raises(ValueError, match="name"):
        ShapeInput(name="", floors=[_valid_floor()])


def test_shape_input_rejects_whitespace_only_name():
    with pytest.raises(ValueError, match="name"):
        ShapeInput(name="   ", floors=[_valid_floor()])


def test_shape_input_rejects_empty_floors():
    with pytest.raises(ValueError, match="floors"):
        ShapeInput(name="demo", floors=[])


def test_shape_input_is_frozen():
    si = ShapeInput(name="demo", floors=[_valid_floor()])
    with pytest.raises(FrozenInstanceError):
        si.name = "other"
