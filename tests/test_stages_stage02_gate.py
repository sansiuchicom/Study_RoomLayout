"""Tests for `room_layout.stages.stage02_gate` — Plan §4.7 / S05-D6.

stage02 runs the two FLOOR-scoped gates (area + dim) against a single
FloorShape; fail-only, returns specs unchanged on accept. The building-level
multi-floor gate is NOT exercised here (it is the Step 07 caller's job —
S05-D6). Geometry derivation (union area, bbox short side) is covered via a
rectangular and an L-shaped (hole-free multi-part) floor.
"""

import pytest

from room_layout.schema.failure import AreaGateFailure, DimGateFailure
from room_layout.schema.geometry import FloorShape, ShapePart
from room_layout.schema.program import SpaceUnitSpec
from room_layout.schema.target import TargetRules
from room_layout.stages import stage02_gate


def _rect_floor(w: float, h: float) -> FloorShape:
    part = ShapePart(exterior=((0.0, 0.0), (w, 0.0), (w, h), (0.0, h)))
    return FloorShape(level=1, parts=[part], floor_to_floor_height=3.0)


def _sus(id, area_min_m2, *, min_dimension_m=None, required=True) -> SpaceUnitSpec:
    return SpaceUnitSpec(
        id=id,
        role="private",
        usage=None,
        area_min_m2=area_min_m2,
        required=required,
        min_dimension_m=min_dimension_m,
    )


def _rules(density_factor=0.7) -> TargetRules:
    return TargetRules(density_factor=density_factor, requires_single_floor=True)


# --- accept path ---


def test_accepts_and_returns_specs_unchanged():
    floor = _rect_floor(10.0, 10.0)  # 100 m², short side 10
    specs = [_sus("a", 20.0, min_dimension_m=2.0), _sus("b", 30.0)]
    out = stage02_gate.run(floor, specs, rules=_rules())
    assert out is specs


# --- area gate wiring ---


def test_area_gate_fires():
    floor = _rect_floor(10.0, 10.0)  # capacity 100 * 0.7 = 70
    specs = [_sus("a", 50.0), _sus("b", 40.0)]  # 90 > 70
    with pytest.raises(AreaGateFailure):
        stage02_gate.run(floor, specs, rules=_rules())


def test_area_gate_uses_density_factor():
    floor = _rect_floor(10.0, 10.0)
    specs = [_sus("a", 80.0)]  # 80 ≤ 100*1.0 but > 100*0.7
    stage02_gate.run(floor, specs, rules=_rules(density_factor=1.0))  # ok
    with pytest.raises(AreaGateFailure):
        stage02_gate.run(floor, specs, rules=_rules(density_factor=0.7))


# --- dim gate wiring (bbox short side) ---


def test_dim_gate_fires_on_short_side():
    floor = _rect_floor(20.0, 4.0)  # short side = 4
    specs = [_sus("a", 5.0, min_dimension_m=6.0)]  # needs 6 > 4
    with pytest.raises(DimGateFailure):
        stage02_gate.run(floor, specs, rules=_rules())


def test_dim_gate_passes_within_short_side():
    floor = _rect_floor(20.0, 4.0)  # short side = 4
    specs = [_sus("a", 5.0, min_dimension_m=3.5)]  # 3.5 ≤ 4
    out = stage02_gate.run(floor, specs, rules=_rules())
    assert out is specs


# --- geometry derivation: holes subtracted, multi-part union ---


def test_area_uses_union_with_holes_subtracted():
    """A floor with a hole has less usable area than its bbox suggests."""
    outer = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))
    hole = ((2.0, 2.0), (2.0, 8.0), (8.0, 8.0), (8.0, 2.0))  # CW hole, 36 m²
    part = ShapePart(exterior=outer, holes=(hole,))
    floor = FloorShape(level=1, parts=[part], floor_to_floor_height=3.0)
    # net area = 100 - 36 = 64; capacity = 64 * 0.7 = 44.8
    specs = [_sus("a", 50.0)]  # 50 > 44.8 → fails (would pass if hole ignored)
    with pytest.raises(AreaGateFailure) as exc:
        stage02_gate.run(floor, specs, rules=_rules())
    assert exc.value.record.data["footprint_area_m2"] == 64.0


def test_multi_part_floor_area_is_summed():
    p1 = ShapePart(exterior=((0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)))  # 16
    p2 = ShapePart(exterior=((5.0, 0.0), (9.0, 0.0), (9.0, 4.0), (5.0, 4.0)))  # 16
    floor = FloorShape(level=1, parts=[p1, p2], floor_to_floor_height=3.0)
    specs = [_sus("a", 20.0)]  # 20 ≤ 32 * 0.7 = 22.4
    out = stage02_gate.run(floor, specs, rules=_rules())
    assert out is specs
