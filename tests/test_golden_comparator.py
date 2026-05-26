"""Tests for ``tests/_golden.py::assert_layout_equal``.

Plan §4.4 verification: covers equal-pass, unequal-fail with path,
Polygon within / outside tolerance, float tolerance, nested
list/dict recursion, update-mode round-trip + error paths, and the
``--update-goldens`` fixture wiring.
"""

import json
from pathlib import Path

import pytest
from shapely.geometry import Polygon
from tests._golden import assert_layout_equal

from room_layout.schema import (
    FailureRecord,
    FloorShape,
    LabeledFloorLayout,
    LabeledRoom,
    LabeledRoomLayout,
    ShapeInput,
    ShapePart,
    SpaceUnitSpec,
    from_dict,
)


def _sus(area_target: float = 10.0) -> SpaceUnitSpec:
    return SpaceUnitSpec(
        id="x",
        role="public",
        usage=None,
        area_target_m2=area_target,
        area_min_m2=5.0,
        min_dimension_m=1.5,
        required=True,
        anchor_id=None,
    )


def _room(area: float = 25.0, poly: Polygon | None = None) -> LabeledRoom:
    return LabeledRoom(
        id="r1",
        polygon=poly or Polygon([(0, 0), (5, 0), (5, 5), (0, 5)]),
        role="public",
        usage=None,
        area_m2=area,
    )


# --- Equal cases pass ---


def test_equal_simple_dataclass():
    assert_layout_equal(_sus(), _sus())


def test_equal_with_polygon():
    p1 = Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])
    p2 = Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])
    assert_layout_equal(_room(poly=p1), _room(poly=p2))


def test_equal_list_of_dataclasses():
    a = [_sus(), _sus(area_target=20.0)]
    b = [_sus(), _sus(area_target=20.0)]
    assert_layout_equal(a, b)


def test_equal_dict_of_lists():
    a = {1: [_sus()], 2: [_sus(area_target=20.0)]}
    b = {1: [_sus()], 2: [_sus(area_target=20.0)]}
    assert_layout_equal(a, b)


def test_equal_nested_lrl():
    """Real-world shape: LabeledRoomLayout with Polygons through 3 levels."""
    lrl1 = LabeledRoomLayout(
        valid=True,
        floors=[LabeledFloorLayout(level=1, rooms=[_room()])],
        provenance={"seed": 42},
    )
    lrl2 = LabeledRoomLayout(
        valid=True,
        floors=[LabeledFloorLayout(level=1, rooms=[_room()])],
        provenance={"seed": 42},
    )
    assert_layout_equal(lrl1, lrl2)


def test_equal_shape_input_with_tuple_rings():
    """``ShapePart.exterior`` is a tuple of tuples — strict-tuple compare."""
    sp1 = ShapePart(exterior=((0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)))
    sp2 = ShapePart(exterior=((0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)))
    si1 = ShapeInput(
        name="demo",
        floors=[FloorShape(level=1, parts=[sp1], floor_to_floor_height=3.0)],
    )
    si2 = ShapeInput(
        name="demo",
        floors=[FloorShape(level=1, parts=[sp2], floor_to_floor_height=3.0)],
    )
    assert_layout_equal(si1, si2)


# --- Unequal cases fail with diagnostic path ---


def test_unequal_field_path_in_message():
    with pytest.raises(AssertionError, match="area_target_m2"):
        assert_layout_equal(_sus(area_target=10.0), _sus(area_target=20.0))


def test_unequal_role_in_message():
    a = _sus()
    b = SpaceUnitSpec(
        id="x",
        role="private",
        usage=None,
        area_target_m2=10.0,
        area_min_m2=5.0,
        min_dimension_m=1.5,
        required=True,
    )
    with pytest.raises(AssertionError, match="role"):
        assert_layout_equal(a, b)


def test_unequal_nested_list_index_in_path():
    a = [_sus(area_target=10.0), _sus(area_target=20.0)]
    b = [_sus(area_target=10.0), _sus(area_target=30.0)]
    with pytest.raises(AssertionError, match=r"\[1\]\.area_target_m2"):
        assert_layout_equal(a, b)


def test_dataclass_type_mismatch():
    fr = FailureRecord(code="X", stage="s", message="m")
    with pytest.raises(AssertionError, match="dataclass type mismatch"):
        assert_layout_equal(_sus(), fr)


def test_list_vs_tuple_mismatch_strict():
    with pytest.raises(AssertionError, match="container type mismatch"):
        assert_layout_equal([1, 2, 3], (1, 2, 3))


def test_dict_key_mismatch():
    with pytest.raises(AssertionError, match="dict key mismatch"):
        assert_layout_equal({"x": 1, "y": 2}, {"x": 1, "z": 2})


def test_top_level_value_mismatch():
    with pytest.raises(AssertionError, match="value mismatch"):
        assert_layout_equal("hello", "world")


# --- Polygon tolerance ---


def test_polygon_within_tolerance_passes():
    p1 = Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])
    p2 = Polygon([(0, 0), (5 + 1e-8, 0), (5 + 1e-8, 5), (0, 5)])
    assert_layout_equal(_room(poly=p1), _room(poly=p2), tol=1e-6)


def test_polygon_outside_tolerance_fails():
    p1 = Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])
    p2 = Polygon([(0, 0), (5.001, 0), (5.001, 5), (0, 5)])
    with pytest.raises(AssertionError, match="Polygon differs"):
        assert_layout_equal(_room(poly=p1), _room(poly=p2), tol=1e-6)


def test_polygon_vs_non_polygon_mismatch():
    p = Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])
    with pytest.raises(AssertionError, match="type mismatch"):
        assert_layout_equal(p, "not a polygon")


# --- Float tolerance ---


def test_float_within_tolerance_passes():
    assert_layout_equal(_sus(area_target=10.0), _sus(area_target=10.0 + 1e-8), tol=1e-6)


def test_float_outside_tolerance_fails():
    with pytest.raises(AssertionError, match="float differs"):
        assert_layout_equal(_sus(area_target=10.0), _sus(area_target=10.001), tol=1e-6)


def test_int_promoted_to_float_for_compare():
    """`from_dict(float, 5)` returns 5.0; comparing 5.0 vs 5 should pass."""
    assert_layout_equal(5.0, 5, tol=1e-6)


# --- Bool strictness (subclass-of-int quirk) ---


def test_bool_equal_passes():
    assert_layout_equal(True, True)
    assert_layout_equal(False, False)


def test_bool_mismatch_fails():
    with pytest.raises(AssertionError, match="bool mismatch"):
        assert_layout_equal(True, False)


# --- Update mode ---


def test_update_mode_writes_file(tmp_path: Path):
    p = tmp_path / "golden.json"
    sus = _sus()
    assert_layout_equal(sus, None, update_mode=True, golden_path=p)
    assert p.exists()
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    loaded = from_dict(SpaceUnitSpec, data)
    assert loaded == sus


def test_update_mode_creates_parent_dirs(tmp_path: Path):
    p = tmp_path / "sub" / "deeper" / "golden.json"
    assert_layout_equal(_sus(), None, update_mode=True, golden_path=p)
    assert p.exists()


def test_update_mode_requires_golden_path():
    with pytest.raises(ValueError, match="golden_path"):
        assert_layout_equal(_sus(), None, update_mode=True)


def test_update_mode_skips_comparison(tmp_path: Path):
    """When update_mode=True, comparison is skipped even if expected mismatches."""
    p = tmp_path / "golden.json"
    # expected is intentionally garbage; update_mode short-circuits.
    assert_layout_equal(_sus(), "garbage", update_mode=True, golden_path=p)
    assert p.exists()


# --- Conftest fixture wiring ---


def test_update_goldens_flag_registered(request):
    """The ``--update-goldens`` CLI flag is wired by ``tests/conftest.py``."""
    option = request.config.getoption("--update-goldens")
    assert isinstance(option, bool)


def test_update_goldens_fixture_is_bool(update_goldens):
    """The ``update_goldens`` fixture is exposed and bool-typed."""
    assert isinstance(update_goldens, bool)
