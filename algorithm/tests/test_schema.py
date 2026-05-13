import math

import pytest

from celllayout_tf.schema import ShapeInput, ShapePart, part_theta


def test_shape_part_rejects_fewer_than_three_vertices():
    with pytest.raises(ValueError):
        ShapePart(exterior=((0, 0), (1, 0)))


def test_shape_part_rejects_hole_with_fewer_than_three_vertices():
    with pytest.raises(ValueError):
        ShapePart(
            exterior=((0, 0), (1, 0), (1, 1), (0, 1)),
            holes=(((0.5, 0.5), (0.6, 0.5)),),
        )


def test_shape_part_holds_holes_field():
    part = ShapePart(
        exterior=((0, 0), (10, 0), (10, 10), (0, 10)),
        holes=(((3, 3), (3, 5), (5, 5), (5, 3)),),
    )

    assert len(part.holes) == 1
    assert len(part.holes[0]) == 4


def test_shape_input_rejects_empty_parts():
    with pytest.raises(ValueError):
        ShapeInput(name="empty", parts=())


def test_shape_input_is_hashable_and_frozen():
    part = ShapePart(exterior=((0, 0), (1, 0), (1, 1), (0, 1)))
    shape = ShapeInput(name="x", parts=(part,))

    with pytest.raises(Exception):
        shape.name = "y"  # type: ignore[misc]
    assert hash(shape) == hash(ShapeInput(name="x", parts=(part,)))


def test_part_theta_for_axis_aligned_rect_is_zero():
    part = ShapePart(exterior=((0, 0), (12, 0), (12, 8), (0, 8)))
    assert part_theta(part) == 0.0


def test_part_theta_for_rotated_rect_matches_design_angle():
    deg = 25.0
    rad = math.radians(deg)
    # first edge from (0,0) at angle 25°
    e0 = (0.0, 0.0)
    e1 = (math.cos(rad) * 5, math.sin(rad) * 5)
    e2 = (e1[0] - math.sin(rad) * 4, e1[1] + math.cos(rad) * 4)
    e3 = (-math.sin(rad) * 4, math.cos(rad) * 4)
    part = ShapePart(exterior=(e0, e1, e2, e3))

    theta = part_theta(part)
    assert abs(theta - rad) < 1e-9


def test_part_theta_skips_degenerate_first_edge():
    part = ShapePart(exterior=((0, 0), (0, 0), (5, 0), (5, 3)))
    assert part_theta(part) == 0.0
