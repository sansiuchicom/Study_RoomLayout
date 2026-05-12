from shapely.geometry import MultiPolygon, box

from celllayout_tf.validation import validate_partition
from celllayout_tf.zoning import zone_footprint


def test_zone_footprint_auto_k_returns_valid_partition():
    footprint = box(0, 0, 10, 8)

    result = zone_footprint(footprint)

    assert result.planning.requested_k == 8
    assert len(result.zones) == 8
    assert len(result.subdivision.faces) == 8
    assert result.validation.ok


def test_validate_partition_detects_overlap():
    footprint = box(0, 0, 10, 10)
    zones = [
        {"polygon": box(0, 0, 6, 10)},
        {"polygon": box(5, 0, 10, 10)},
    ]

    report = validate_partition(footprint, zones)

    assert report.overlap_area > 0
    assert len(report.overlap_details) == 1
    assert "overlap" in report.failed_checks
    assert not report.ok


def test_validate_partition_detects_gap():
    footprint = box(0, 0, 10, 10)
    zones = [{"polygon": box(0, 0, 5, 10)}]

    report = validate_partition(footprint, zones)

    assert report.gap_area == 50
    assert report.gap_part_count == 1
    assert "gap" in report.failed_checks
    assert not report.ok


def test_validate_partition_detects_outside_area():
    footprint = box(0, 0, 10, 10)
    zones = [{"polygon": box(0, 0, 11, 10)}]

    report = validate_partition(footprint, zones)

    assert report.outside_area == 10
    assert report.largest_outside_area == 10
    assert "outside" in report.failed_checks
    assert not report.ok


def test_validate_partition_detects_empty_and_multipart_zones():
    footprint = box(0, 0, 10, 10)
    zones = [
        {"polygon": MultiPolygon([box(0, 0, 2, 2), box(8, 8, 10, 10)])},
        {"polygon": box(0, 0, 0, 0)},
    ]

    report = validate_partition(footprint, zones)

    assert report.empty_count == 1
    assert report.multipart_count == 1
    assert "empty" in report.failed_checks
    assert "multipart" in report.failed_checks
    assert not report.ok
