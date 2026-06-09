"""Multi-floor house golden corpus (Step 10 §4.7).

The first multi-floor goldens — locking the building-level behaviors Step 10
added (building cardinality, vc continuity, vc-only floors) that the apartment
corpora cannot reach. Fixtures are built in-code (like corpus B) and modelled
on a ResearchBIM `Building` (per-storey footprint + one shared core, S10-D8/D9):

- ``house_3floor`` — a current-ResearchBIM-translatable 3-floor house (single
  simple footprint/floor, one shared stair): living/kitchen on 1F, bedrooms
  above. ``valid=True`` — the building-cardinality win (S10-D5).
- ``house_courtyard`` — a forward-compatible variant whose 2F has a courtyard
  hole (room_layout's footprint superset; not a today-ResearchBIM input, #9).
  ``valid=True``.
- ``house_discontinuous`` — a discontinuity injection: 2F omits its vc spec, so
  no stair room emits there (review #5). ``valid=False`` +
  ``VERTICAL_CIRCULATION_DISCONTINUOUS``.

Same GEOS-stable ``run_golden`` digest as corpus A/B. Heights are set on every
floor (multi-floor requires it — #10).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from shapely.geometry import Polygon
from tests._golden import assert_golden
from tests.test_golden_run import run_golden

from room_layout import run
from room_layout.schema import (
    FloorShape,
    ProgramRequest,
    ShapeInput,
    ShapePart,
    SpaceUnitSpec,
    VerticalAnchor,
)

GOLDEN_DIR = Path(__file__).parent / "golden"

_W, _H = 12.0, 10.0


def _floor(level: int, *, courtyard: bool = False) -> FloorShape:
    exterior = ((0, 0), (_W, 0), (_W, _H), (0, _H))
    # CW hole (room_layout convention) — same ring order as the courtyard spike.
    holes = (((5, 4), (5, 6), (7, 6), (7, 4)),) if courtyard else ()
    return FloorShape(
        level=level,
        parts=[ShapePart(exterior=exterior, holes=holes)],
        floor_to_floor_height=3.0,
    )


def _spec(sid: str, role: str, area_min_m2: float = 0.5, **kw) -> SpaceUnitSpec:
    return SpaceUnitSpec(
        id=sid, role=role, usage=None, area_min_m2=area_min_m2, required=True, **kw
    )


def _stair(levels: tuple[int, int]) -> VerticalAnchor:
    return VerticalAnchor(
        id="stair",
        kind="stair_core",
        footprint_polygon=Polygon([(0, 0), (2, 0), (2, 3), (0, 3)]),
        floor_range=levels,
        host_role="vertical_circulation",
    )


def _vc(sid: str) -> SpaceUnitSpec:
    return _spec(sid, "vertical_circulation", 2.0, anchor_id="stair")


def house_3floor() -> tuple[ShapeInput, ProgramRequest]:
    shape = ShapeInput(
        name="house_3floor",
        floors=[_floor(1), _floor(2), _floor(3)],
        vertical_anchors=[_stair((1, 3))],
    )
    program = ProgramRequest(
        target_type="house",
        floor_programs={
            1: [_spec("living", "public", 10.0), _spec("kitchen", "wet", 3.0), _vc("stair_1")],
            2: [_spec("bed1", "private", 8.0), _spec("bed2", "private", 8.0), _vc("stair_2")],
            3: [_spec("bed3", "private", 8.0), _spec("study", "service", 4.0), _vc("stair_3")],
        },
    )
    return shape, program


def house_courtyard() -> tuple[ShapeInput, ProgramRequest]:
    shape = ShapeInput(
        name="house_courtyard",
        floors=[_floor(1), _floor(2, courtyard=True), _floor(3)],
        vertical_anchors=[_stair((1, 3))],
    )
    program = ProgramRequest(
        target_type="house",
        floor_programs={
            1: [_spec("living", "public", 10.0), _spec("kitchen", "wet", 3.0), _vc("stair_1")],
            2: [_spec("bed1", "private", 8.0), _spec("bed2", "private", 8.0), _vc("stair_2")],
            3: [_spec("bed3", "private", 8.0), _vc("stair_3")],
        },
    )
    return shape, program


def house_discontinuous() -> tuple[ShapeInput, ProgramRequest]:
    """2F omits its vc spec → no stair room there → vertically isolated."""
    shape = ShapeInput(
        name="house_discontinuous",
        floors=[_floor(1), _floor(2), _floor(3)],
        vertical_anchors=[_stair((1, 3))],
    )
    program = ProgramRequest(
        target_type="house",
        floor_programs={
            1: [_spec("living", "public", 10.0), _spec("kitchen", "wet", 3.0), _vc("stair_1")],
            2: [_spec("bed1", "private", 8.0), _spec("bed2", "private", 8.0)],  # no vc
            3: [_spec("bed3", "private", 8.0), _vc("stair_3")],
        },
    )
    return shape, program


_FIXTURES = {
    "house_3floor": house_3floor,
    "house_courtyard": house_courtyard,
    "house_discontinuous": house_discontinuous,
}


@pytest.mark.parametrize("name", sorted(_FIXTURES))
def test_house_golden(name: str, update_goldens: bool):
    shape, program = _FIXTURES[name]()
    result = run(shape, program, seed=42)
    assert_golden(run_golden(result), GOLDEN_DIR / name / "run.json", update_goldens=update_goldens)


# --- behaviors beyond the digest -------------------------------------------


def test_3floor_house_valid_with_stair_on_every_floor():
    result = run(*house_3floor(), seed=42)
    assert result.valid is True
    assert len(result.floors) == 3
    for fl in result.floors:
        vc = [r for r in fl.rooms if r.role == "vertical_circulation"]
        assert len(vc) == 1, f"floor {fl.level} should have exactly one stair room"


def test_courtyard_floor_is_valid():
    result = run(*house_courtyard(), seed=42)
    assert result.valid is True
    # 2F (the courtyard floor) still grows rooms around the hole
    assert result.floors[1].rooms


def test_discontinuous_house_flagged():
    result = run(*house_discontinuous(), seed=42)
    assert result.valid is False
    rec = [f for f in result.failure_records if f.code == "VERTICAL_CIRCULATION_DISCONTINUOUS"]
    assert len(rec) == 1
    assert rec[0].data["isolated_levels"] == [2]


# --- multi-floor height required (#10) -------------------------------------


def test_multi_floor_requires_per_floor_height():
    shape = ShapeInput(
        name="noheight",
        floors=[
            FloorShape(
                level=1,
                parts=[ShapePart(exterior=((0, 0), (12, 0), (12, 10), (0, 10)))],
                floor_to_floor_height=3.0,
            ),
            FloorShape(
                level=2,
                parts=[ShapePart(exterior=((0, 0), (12, 0), (12, 10), (0, 10)))],
                floor_to_floor_height=None,
            ),
        ],
        vertical_anchors=[_stair((1, 2))],
    )
    program = ProgramRequest(
        target_type="house",
        floor_programs={
            1: [
                _spec("living", "public", 10.0),
                _spec("bed", "private", 8.0),
                _spec("kitchen", "wet", 3.0),
                _vc("st1"),
            ],
            2: [_spec("bed2", "private", 8.0), _vc("st2")],
        },
    )
    result = run(shape, program, seed=42)
    assert result.valid is False
    assert any(f.code == "MULTI_FLOOR_HEIGHT_REQUIRED" for f in result.failure_records)


def test_single_floor_height_optional():
    # a 1-floor building may omit floor_to_floor_height (apartment path unchanged)
    shape = ShapeInput(
        name="single",
        floors=[
            FloorShape(
                level=1,
                parts=[ShapePart(exterior=((0, 0), (12, 0), (12, 10), (0, 10)))],
                floor_to_floor_height=None,
            )
        ],
        vertical_anchors=[],
    )
    program = ProgramRequest(
        target_type="house",
        floor_programs={
            1: [
                _spec("living", "public", 10.0),
                _spec("bed", "private", 8.0),
                _spec("kitchen", "wet", 3.0),
            ]
        },
    )
    result = run(shape, program, seed=42)
    assert "MULTI_FLOOR_HEIGHT_REQUIRED" not in {f.code for f in result.failure_records}
    assert result.valid is True


# --- per-floor viz reused for multi-floor (10.8, S10-D10) ------------------


def test_house_floors_render_to_per_floor_svg(tmp_path):
    """The Step 08 SVG renderer is per-floor, so multi-floor reuses it as-is
    (S10-D10): each house floor renders to its own layered SVG. (matplotlib-free
    — svg.py is pure.)"""
    import xml.etree.ElementTree as ET

    from room_layout.viz.svg import render

    shape, program = house_3floor()
    result = run(shape, program, seed=42)
    assert len(result.floors) == 3
    for fl, fs in zip(result.floors, shape.floors, strict=True):
        out = render(fs, fl, tmp_path / f"f{fl.level}.svg", anchors=shape.vertical_anchors)
        root = ET.parse(out).getroot()
        groups = [g for g in root if g.tag.endswith("}g")]
        assert len(groups) == 12  # the stable 12-layer stack
        rooms_layer = next(g for g in groups if g.attrib.get("class") == "layer-09-rooms")
        n_room_paths = len([c for c in rooms_layer if c.tag.endswith("}path")])
        assert n_room_paths == len(fl.rooms)  # every labeled room is drawn
