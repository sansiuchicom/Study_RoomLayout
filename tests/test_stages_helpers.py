"""Tests for ``room_layout.stages._helpers`` — work item 4.5 / Plan §4.5.

Covers the six geometry utilities ported from Cell: to_shapely /
from_shapely (incl. the orient + degenerate-reject tightening) /
polygon_parts / line_length / rotate_radians / part_theta.
"""

from math import pi, radians

import pytest
import shapely.geometry as sg

from room_layout.schema import ShapePart
from room_layout.stages._helpers import (
    from_shapely,
    line_length,
    part_theta,
    polygon_parts,
    rotate_radians,
    to_shapely,
)

_CCW_SQUARE = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))
_CW_HOLE = ((2.0, 2.0), (2.0, 5.0), (5.0, 5.0), (5.0, 2.0))


# --- to_shapely ---


def test_to_shapely_simple():
    poly = to_shapely(ShapePart(exterior=_CCW_SQUARE))
    assert isinstance(poly, sg.Polygon)
    assert poly.area == pytest.approx(100.0)
    assert len(poly.interiors) == 0


def test_to_shapely_with_hole():
    poly = to_shapely(ShapePart(exterior=_CCW_SQUARE, holes=(_CW_HOLE,)))
    assert len(poly.interiors) == 1
    # 100 (square) - 9 (3x3 hole) = 91
    assert poly.area == pytest.approx(91.0)


# --- from_shapely ---


def test_from_shapely_round_trip():
    part = ShapePart(exterior=_CCW_SQUARE, holes=(_CW_HOLE,))
    part2 = from_shapely(to_shapely(part))
    assert part2 == part


def test_from_shapely_orients_ccw():
    """A CW-exterior shapely polygon comes back as a CCW ShapePart."""
    cw_poly = sg.Polygon([(0, 0), (0, 10), (10, 10), (10, 0)])  # CW order
    part = from_shapely(cw_poly)
    # ShapePart.__post_init__ enforces CCW — if from_shapely didn't orient,
    # construction would have raised. Reaching here means it oriented.
    assert to_shapely(part).area == pytest.approx(100.0)


def test_from_shapely_rejects_degenerate():
    """Zero-area (collinear) polygons are rejected by the new ShapePart.

    Tightening over Cell's lax schema — bad atoms fail at the boundary.
    """
    degenerate = sg.Polygon([(0, 0), (1, 0), (2, 0)])
    with pytest.raises(ValueError, match="zero signed area"):
        from_shapely(degenerate)


def test_from_shapely_strips_closing_point():
    poly = sg.Polygon(_CCW_SQUARE)
    part = from_shapely(poly)
    # 4 distinct vertices, no duplicated closing point
    assert len(part.exterior) == 4


# --- polygon_parts ---


def test_polygon_parts_single():
    poly = sg.Polygon(_CCW_SQUARE)
    assert polygon_parts(poly) == [poly]


def test_polygon_parts_empty():
    assert polygon_parts(sg.Polygon()) == []


def test_polygon_parts_multipolygon():
    a = sg.Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    b = sg.Polygon([(5, 5), (6, 5), (6, 6), (5, 6)])
    mp = sg.MultiPolygon([a, b])
    parts = polygon_parts(mp)
    assert len(parts) == 2
    assert all(isinstance(p, sg.Polygon) for p in parts)


def test_polygon_parts_geometry_collection():
    a = sg.Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    line = sg.LineString([(0, 0), (1, 1)])
    gc = sg.GeometryCollection([a, line])
    parts = polygon_parts(gc)
    # only the polygon survives; the line is dropped
    assert len(parts) == 1
    assert parts[0].area == pytest.approx(1.0)


# --- line_length ---


def test_line_length_linestring():
    assert line_length(sg.LineString([(0, 0), (3, 4)])) == pytest.approx(5.0)


def test_line_length_multilinestring():
    mls = sg.MultiLineString([[(0, 0), (3, 0)], [(0, 0), (0, 4)]])
    assert line_length(mls) == pytest.approx(7.0)


def test_line_length_empty():
    assert line_length(sg.LineString()) == 0.0


def test_line_length_polygon_has_no_lines():
    # A bare polygon has no LineString components → 0
    assert line_length(sg.Polygon(_CCW_SQUARE)) == 0.0


def test_line_length_geometry_collection():
    gc = sg.GeometryCollection([sg.LineString([(0, 0), (3, 0)]), sg.LineString([(0, 0), (0, 4)])])
    assert line_length(gc) == pytest.approx(7.0)


# --- rotate_radians ---


def test_rotate_radians_quarter_turn():
    poly = sg.Polygon([(0, 0), (2, 0), (2, 1), (0, 1)])
    rotated = rotate_radians(poly, pi / 2, origin=(0, 0))
    # area is preserved under rotation
    assert rotated.area == pytest.approx(poly.area)
    # bounding box swaps width/height (2x1 → 1x2 footprint span)
    minx, miny, maxx, maxy = rotated.bounds
    assert (maxx - minx) == pytest.approx(1.0)
    assert (maxy - miny) == pytest.approx(2.0)


def test_rotate_radians_zero_is_noop_identity():
    poly = sg.Polygon(_CCW_SQUARE)
    # below 1e-12 → returns the *same* object unchanged
    assert rotate_radians(poly, 0.0) is poly
    assert rotate_radians(poly, 1e-13) is poly


def test_rotate_radians_sign_flips_direction():
    poly = sg.Polygon([(1, 0), (2, 0), (2, 1), (1, 1)])
    pos = rotate_radians(poly, radians(90), sign=1, origin=(0, 0))
    neg = rotate_radians(poly, radians(90), sign=-1, origin=(0, 0))
    # +90 lands in upper-left quadrant (x<0), -90 in lower-right (y<0)
    assert pos.centroid.x < 0
    assert neg.centroid.y < 0


# --- part_theta ---


def test_part_theta_axis_aligned_is_zero():
    assert part_theta(ShapePart(exterior=_CCW_SQUARE)) == pytest.approx(0.0)


def test_part_theta_rotated_45():
    # a square rotated 45°: first edge points at 45°
    part = ShapePart(exterior=((0.0, 0.0), (1.0, 1.0), (0.0, 2.0), (-1.0, 1.0)))
    assert part_theta(part) == pytest.approx(pi / 4)


def test_part_theta_always_in_first_quadrant():
    """Result is always folded onto [0, pi/2) regardless of edge direction."""
    # axis-aligned CCW square: first edge points east (0°)
    part = ShapePart(exterior=((0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)))
    theta = part_theta(part)
    assert 0.0 <= theta < pi / 2


def test_part_theta_on_curved_part_returns_valid_range():
    """Curved parts (high-vertex disk) read the first-edge tangent; the
    result must still fall in [0, pi/2). Exercises the loop on a real
    many-vertex part."""
    disk = from_shapely(sg.Point(0, 0).buffer(5, quad_segs=16))
    theta = part_theta(disk)
    assert 0.0 <= theta < pi / 2
