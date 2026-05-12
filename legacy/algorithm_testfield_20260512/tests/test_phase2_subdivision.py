import shapely.affinity as sa
from shapely.geometry import LineString, box
from shapely.ops import unary_union

from celllayout_tf.subdivision import build_atomic_faces
from celllayout_tf.validation import validate_partition


def _face_zones(result):
    return [
        {"zone_id": face.face_id, "polygon": face.polygon}
        for face in result.faces
    ]


def _assert_faces_partition_footprint(footprint, result):
    report = validate_partition(footprint, _face_zones(result))
    assert report.ok, report


def test_subdivision_without_cut_returns_one_face():
    footprint = box(0, 0, 10, 8)

    result = build_atomic_faces(footprint)

    assert len(result.faces) == 1
    assert result.faces[0].area == 80
    _assert_faces_partition_footprint(footprint, result)


def test_subdivision_vertical_cut_splits_rectangle_into_two_faces():
    footprint = box(0, 0, 10, 10)
    line = LineString([(5, -5), (5, 15)])

    result = build_atomic_faces(footprint, [line])

    assert len(result.faces) == 2
    assert sorted(face.area for face in result.faces) == [50, 50]
    _assert_faces_partition_footprint(footprint, result)


def test_subdivision_cross_cut_splits_rectangle_into_four_faces():
    footprint = box(0, 0, 10, 10)
    lines = [
        LineString([(5, -5), (5, 15)]),
        LineString([(-5, 4), (15, 4)]),
    ]

    result = build_atomic_faces(footprint, lines)

    assert len(result.faces) == 4
    assert sorted(face.area for face in result.faces) == [20, 20, 30, 30]
    _assert_faces_partition_footprint(footprint, result)


def test_subdivision_respects_holes():
    hole = box(4, 4, 6, 6)
    footprint = box(0, 0, 10, 10).difference(hole)
    line = LineString([(5, -5), (5, 15)])

    result = build_atomic_faces(footprint, [line])

    assert len(result.faces) == 2
    assert sorted(face.area for face in result.faces) == [48, 48]
    assert unary_union([face.polygon for face in result.faces]).intersection(hole).area == 0
    _assert_faces_partition_footprint(footprint, result)


def test_subdivision_handles_rotated_footprint_with_world_axis_cut():
    footprint = sa.rotate(box(0, 0, 12, 8), 30, origin=(6, 4))
    line = LineString([(6, -10), (6, 18)])

    result = build_atomic_faces(footprint, [line])

    assert len(result.faces) == 2
    _assert_faces_partition_footprint(footprint, result)


def test_subdivision_handles_concave_l_shape():
    footprint = unary_union([box(0, 0, 10, 4), box(0, 4, 4, 10)])
    line = LineString([(2, -5), (2, 15)])

    result = build_atomic_faces(footprint, [line])

    assert len(result.faces) == 2
    assert sorted(face.area for face in result.faces) == [20, 44]
    _assert_faces_partition_footprint(footprint, result)
