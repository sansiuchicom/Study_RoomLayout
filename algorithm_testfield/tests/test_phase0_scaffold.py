from shapely.geometry import box

from celllayout_tf.validation import validate_partition
from celllayout_tf.zoning import zone_footprint


def test_phase0_zone_footprint_returns_valid_single_face_partition():
    footprint = box(0, 0, 10, 8)

    result = zone_footprint(footprint)

    assert len(result.zones) == 1
    assert len(result.subdivision.faces) == 1
    assert result.validation.ok


def test_validate_partition_detects_overlap():
    footprint = box(0, 0, 10, 10)
    zones = [
        {"polygon": box(0, 0, 6, 10)},
        {"polygon": box(5, 0, 10, 10)},
    ]

    report = validate_partition(footprint, zones)

    assert report.overlap_area > 0
    assert not report.ok
