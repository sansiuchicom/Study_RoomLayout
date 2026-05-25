"""Tests for `room_layout.schema.validators` — work item 4.8 / Plan §4.8.

Covers `validate_input(shape, program)` — each of the 4 stable failure
codes (3 errors + 1 warning), happy path, accumulation across multiple
violations, and the `WARN_PREFIX` consumer-side error/warning split.
"""

from shapely.geometry import Polygon

from room_layout.schema import (
    WARN_PREFIX,
    FloorShape,
    ProgramRequest,
    ShapeInput,
    ShapePart,
    SpaceUnitSpec,
    VerticalAnchor,
    validate_input,
)

_SQ = ((0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0))


def _shape() -> ShapeInput:
    sp = ShapePart(exterior=_SQ)
    return ShapeInput(
        name="demo",
        floors=[
            FloorShape(level=1, parts=[sp], floor_to_floor_height=3.0),
            FloorShape(level=2, parts=[sp], floor_to_floor_height=3.0),
        ],
        vertical_anchors=[
            VerticalAnchor(
                id="stair_1",
                kind="stair_core",
                footprint_polygon=Polygon([(0, 0), (3, 0), (3, 3), (0, 3)]),
                floor_range=(1, 2),
                host_role="vertical_circulation",
            ),
            VerticalAnchor(
                id="ps_1",
                kind="ps_shaft",
                footprint_polygon=Polygon([(15, 15), (16, 15), (16, 16), (15, 16)]),
                floor_range=(1, 2),
                host_role=None,
            ),
        ],
    )


def _sus(id_="x", role="public", anchor_id=None) -> SpaceUnitSpec:
    return SpaceUnitSpec(
        id=id_,
        role=role,
        usage=None,
        area_target_m2=10.0,
        area_min_m2=8.0,
        min_dimension_m=2.0,
        required=True,
        anchor_id=anchor_id,
    )


def test_happy_path_returns_empty_list():
    shape = _shape()
    program = ProgramRequest(
        target_type="apartment",
        floor_programs={
            1: [
                _sus("living", "public"),
                _sus("vc1", "vertical_circulation", "stair_1"),
            ]
        },
    )
    assert validate_input(shape, program) == []


def test_anchor_id_not_found():
    program = ProgramRequest(
        target_type="apartment",
        floor_programs={1: [_sus("vc1", "vertical_circulation", "nope")]},
    )
    records = validate_input(_shape(), program)
    notfound = next(r for r in records if r.code == "ANCHOR_ID_NOT_FOUND")
    assert notfound.data["spec_id"] == "vc1"
    assert notfound.data["anchor_id"] == "nope"
    assert "stair_1" in notfound.data["available_anchor_ids"]


def test_anchor_host_role_mismatch():
    """vc-spec pointing at a ps_shaft (host_role=None) triggers mismatch."""
    program = ProgramRequest(
        target_type="apartment",
        floor_programs={1: [_sus("vc1", "vertical_circulation", "ps_1")]},
    )
    records = validate_input(_shape(), program)
    hrm = next(r for r in records if r.code == "ANCHOR_HOST_ROLE_MISMATCH")
    assert hrm.data["anchor_host_role"] is None
    assert hrm.data["anchor_kind"] == "ps_shaft"


def test_program_floor_not_in_shape():
    program = ProgramRequest(
        target_type="apartment",
        floor_programs={
            1: [_sus("vc1", "vertical_circulation", "stair_1")],
            99: [_sus("ghost", "public")],
        },
    )
    records = validate_input(_shape(), program)
    pfns = next(r for r in records if r.code == "PROGRAM_FLOOR_NOT_IN_SHAPE")
    assert pfns.data["level"] == 99
    assert pfns.data["available_levels"] == [1, 2]


def test_warn_anchor_unused():
    """A vc-anchor referenced by no spec produces a WARN-level record."""
    program = ProgramRequest(
        target_type="apartment",
        floor_programs={1: [_sus("living", "public")]},
    )
    records = validate_input(_shape(), program)
    assert len(records) == 1
    assert records[0].code == "WARN_ANCHOR_UNUSED"
    assert records[0].code.startswith(WARN_PREFIX)
    assert records[0].data["anchor_id"] == "stair_1"


def test_non_vc_anchor_unused_does_not_warn():
    """ps_shaft has host_role=None; being unused is normal — no warning."""
    program = ProgramRequest(
        target_type="apartment",
        floor_programs={1: [_sus("vc1", "vertical_circulation", "stair_1")]},
    )
    assert validate_input(_shape(), program) == []


def test_multiple_failures_accumulate():
    program = ProgramRequest(
        target_type="apartment",
        floor_programs={
            1: [
                _sus("vc1", "vertical_circulation", "wrong_id"),
                _sus("vc2", "vertical_circulation", "ps_1"),
            ],
            99: [_sus("ghost", "public")],
        },
    )
    records = validate_input(_shape(), program)
    codes = sorted(r.code for r in records)
    assert codes.count("ANCHOR_ID_NOT_FOUND") == 1
    assert codes.count("ANCHOR_HOST_ROLE_MISMATCH") == 1
    assert codes.count("PROGRAM_FLOOR_NOT_IN_SHAPE") == 1
    assert codes.count("WARN_ANCHOR_UNUSED") == 1


def test_duplicate_anchor_id():
    """Two VerticalAnchors with the same id → DUPLICATE_ANCHOR_ID."""
    sp = ShapePart(exterior=_SQ)
    poly = Polygon([(0, 0), (3, 0), (3, 3), (0, 3)])
    shape = ShapeInput(
        name="dup-anchor",
        floors=[FloorShape(level=1, parts=[sp], floor_to_floor_height=3.0)],
        vertical_anchors=[
            VerticalAnchor(
                id="stair_1",
                kind="stair_core",
                footprint_polygon=poly,
                floor_range=(1, 1),
                host_role="vertical_circulation",
            ),
            VerticalAnchor(
                id="stair_1",
                kind="elevator_shaft",
                footprint_polygon=poly,
                floor_range=(1, 1),
                host_role="vertical_circulation",
            ),
        ],
    )
    program = ProgramRequest(
        target_type="apartment",
        floor_programs={1: [_sus("vc1", "vertical_circulation", "stair_1")]},
    )
    records = validate_input(shape, program)
    dup = next(r for r in records if r.code == "DUPLICATE_ANCHOR_ID")
    assert dup.data["anchor_id"] == "stair_1"
    assert dup.data["count"] == 2


def test_duplicate_floor_level():
    """Two FloorShapes with the same level → DUPLICATE_FLOOR_LEVEL."""
    sp = ShapePart(exterior=_SQ)
    shape = ShapeInput(
        name="dup-floor",
        floors=[
            FloorShape(level=1, parts=[sp], floor_to_floor_height=3.0),
            FloorShape(level=1, parts=[sp], floor_to_floor_height=3.0),
        ],
    )
    program = ProgramRequest(target_type="apartment", floor_programs={1: [_sus("a", "public")]})
    records = validate_input(shape, program)
    dup = next(r for r in records if r.code == "DUPLICATE_FLOOR_LEVEL")
    assert dup.data["level"] == 1
    assert dup.data["count"] == 2


def test_duplicate_spec_id_across_floors():
    """SpaceUnitSpec.id is a global identifier — duplicates across floors
    surface DUPLICATE_SPEC_ID (Pipeline §2.3)."""
    shape = _shape()
    program = ProgramRequest(
        target_type="apartment",
        floor_programs={
            1: [_sus("living", "public"), _sus("vc", "vertical_circulation", "stair_1")],
            2: [_sus("living", "private")],  # `living` reused
        },
    )
    records = validate_input(shape, program)
    dup = next(r for r in records if r.code == "DUPLICATE_SPEC_ID")
    assert dup.data["spec_id"] == "living"
    assert dup.data["count"] == 2


def test_anchor_floor_range_mismatch():
    """A vc-spec on a floor outside the anchor's floor_range → mismatch.

    The anchor still counts as 'used' so no redundant WARN_ANCHOR_UNUSED
    fires for the same anchor."""
    sp = ShapePart(exterior=_SQ)
    shape = ShapeInput(
        name="range-mismatch",
        floors=[
            FloorShape(level=1, parts=[sp], floor_to_floor_height=3.0),
            FloorShape(level=2, parts=[sp], floor_to_floor_height=3.0),
        ],
        vertical_anchors=[
            VerticalAnchor(
                id="stair_lower",
                kind="stair_core",
                footprint_polygon=Polygon([(0, 0), (3, 0), (3, 3), (0, 3)]),
                floor_range=(1, 1),
                host_role="vertical_circulation",
            ),
        ],
    )
    program = ProgramRequest(
        target_type="apartment",
        floor_programs={2: [_sus("vc1", "vertical_circulation", "stair_lower")]},
    )
    records = validate_input(shape, program)
    codes = {r.code for r in records}
    assert "ANCHOR_FLOOR_RANGE_MISMATCH" in codes
    assert "WARN_ANCHOR_UNUSED" not in codes
    mismatch = next(r for r in records if r.code == "ANCHOR_FLOOR_RANGE_MISMATCH")
    assert mismatch.data["spec_floor"] == 2
    assert mismatch.data["anchor_floor_range"] == [1, 1]


def test_warn_prefix_consumer_split():
    """Consumers (Step 06 run) filter by WARN_PREFIX to separate severities."""
    program = ProgramRequest(
        target_type="apartment",
        floor_programs={
            1: [
                _sus("vc1", "vertical_circulation", "wrong_id"),
                _sus("vc2", "vertical_circulation", "ps_1"),
            ],
            99: [_sus("ghost", "public")],
        },
    )
    records = validate_input(_shape(), program)
    errors = [r for r in records if not r.code.startswith(WARN_PREFIX)]
    warnings = [r for r in records if r.code.startswith(WARN_PREFIX)]
    assert len(errors) == 3
    assert len(warnings) == 1
