"""run() golden corpus B (§4.10) — authored apartment fixtures.

Corpus A (test_golden_run.py) locks 33-shape regression. Corpus B adds the
coverage A cannot — three DISTINCT behaviors, not a redundant "realistic
apartment" suite (growth is target-agnostic, S04-D3, so a realistic program
grows the same greedy layout as A — and can even make a realistic apartment
*invalid*, see ``apt_undersized_room``):

- ``apt_anchored_core`` — a central stair core: the **anchor end-to-end path**
  (subtract_anchors hole → grow on the holed floor → vc re-insert at the
  footprint), which nothing else exercises integrated (4.4 was a unit test).
  ``valid=True``.
- ``apt_infeasible`` — a program whose Σ overflows the floor: the **pre-growth
  admission** failure (``valid=False`` + ``DOMAIN_AREA_GATE_FAIL``).
- ``apt_undersized_room`` — admission passes, but the living room grows below
  its own ``area_min`` (target-agnostic greedy growth gives it the smallest
  share): the **post-growth per-room** failure at the ``run()`` level
  (``valid=False`` + ``ROOM_BELOW_MIN_AREA``). This is the realistic-program
  case from the §4.10 finding — kept as a golden because it locks the
  admission-passes-but-a-room-grows-too-small path.

valid non-anchored layouts are corpus A's 31 valid cases. Fixtures are built
in-code (anchored shapes are coordinate-heavy — Python is cleaner + type-checked
than hand-authored JSON). Same GEOS-stable ``run_golden`` digest as corpus A.
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


def _spec(id_, role, area_min_m2, *, usage=None, anchor_id=None):
    return SpaceUnitSpec(
        id=id_,
        role=role,
        usage=usage,
        area_min_m2=area_min_m2,
        required=True,
        anchor_id=anchor_id,
    )


def _rect_floor(w: float, h: float, *, level: int = 0) -> FloorShape:
    return FloorShape(
        level=level,
        parts=[ShapePart(exterior=((0, 0), (w, 0), (w, h), (0, h)))],
        floor_to_floor_height=None,
    )


def apt_anchored_core() -> tuple[ShapeInput, ProgramRequest]:
    """10x8 apartment with a 2x2 central stair core (anchor end-to-end)."""
    shape = ShapeInput(
        name="apt_anchored_core",
        floors=[_rect_floor(10, 8)],
        vertical_anchors=[
            VerticalAnchor(
                id="stair",
                kind="stair_core",
                footprint_polygon=Polygon([(4, 3), (6, 3), (6, 5), (4, 5)]),
                floor_range=(0, 0),
                host_role="vertical_circulation",
            )
        ],
    )
    program = ProgramRequest(
        target_type="apartment",
        floor_programs={
            0: [
                _spec("living", "public", 10.0, usage="living"),
                _spec("bed1", "private", 7.0, usage="bedroom"),
                _spec("bath", "wet", 2.5, usage="bathroom"),
                _spec("stair_room", "vertical_circulation", 2.0, usage="stair", anchor_id="stair"),
            ]
        },
    )
    return shape, program


def apt_infeasible() -> tuple[ShapeInput, ProgramRequest]:
    """5x4 floor (20 m²) with a program that overflows it → admission area gate."""
    shape = ShapeInput(name="apt_infeasible", floors=[_rect_floor(5, 4)], vertical_anchors=[])
    program = ProgramRequest(
        target_type="apartment",
        floor_programs={
            0: [
                _spec("living", "public", 50.0, usage="living"),  # alone exceeds capacity
                _spec("bed1", "private", 1.0, usage="bedroom"),
                _spec("bath", "wet", 1.0, usage="bathroom"),
            ]
        },
    )
    return shape, program


def apt_undersized_room() -> tuple[ShapeInput, ProgramRequest]:
    """9x7 apartment with realistic mins — admission passes, but target-agnostic
    growth gives the living room the smallest share (≈8.8 m² < its 12 m² min),
    so the post-growth per-room gate rejects it (ROOM_BELOW_MIN_AREA)."""
    shape = ShapeInput(name="apt_undersized_room", floors=[_rect_floor(9, 7)], vertical_anchors=[])
    program = ProgramRequest(
        target_type="apartment",
        floor_programs={
            0: [
                _spec("living", "public", 12.0, usage="living"),
                _spec("bed1", "private", 8.0, usage="bedroom"),
                _spec("bed2", "private", 8.0, usage="bedroom"),
                _spec("kitchen", "service", 5.0, usage="kitchen"),
                _spec("bath", "wet", 3.0, usage="bathroom"),
            ]
        },
    )
    return shape, program


_FIXTURES = {
    "apt_anchored_core": apt_anchored_core,
    "apt_infeasible": apt_infeasible,
    "apt_undersized_room": apt_undersized_room,
}


@pytest.mark.parametrize("name", sorted(_FIXTURES))
def test_corpus_b_golden(name: str, update_goldens: bool):
    shape, program = _FIXTURES[name]()
    result = run(shape, program, seed=42)
    assert_golden(run_golden(result), GOLDEN_DIR / name / "run.json", update_goldens=update_goldens)


def test_anchored_core_reinserts_vc_room_around_the_hole():
    """The anchor end-to-end path (beyond the digest): vc room == the footprint,
    grown rooms tile around it with zero overlap."""
    shape, program = apt_anchored_core()
    result = run(shape, program, seed=42)
    assert result.valid is True
    rooms = {r.id: r for r in result.floors[0].rooms}
    vc = rooms["stair_room"]
    assert vc.role == "vertical_circulation"
    assert vc.anchor_id == "stair"
    assert vc.area_m2 == pytest.approx(4.0)  # the 2x2 anchor footprint
    anchor = shape.vertical_anchors[0].footprint_polygon
    for rid, room in rooms.items():
        if rid == "stair_room":
            continue
        assert room.polygon.intersection(anchor).area == pytest.approx(0.0, abs=1e-9)


def test_infeasible_fails_admission_area_gate():
    shape, program = apt_infeasible()
    result = run(shape, program, seed=42)
    assert result.valid is False
    assert any(f.code == "DOMAIN_AREA_GATE_FAIL" for f in result.failure_records)


def test_undersized_room_rejected_post_growth():
    """run()-level per-room rejection: admission passes, a room grows too small."""
    shape, program = apt_undersized_room()
    result = run(shape, program, seed=42)
    assert result.valid is False
    assert any(f.code == "ROOM_BELOW_MIN_AREA" for f in result.failure_records)
    # the floor is still populated (partial output preserved — Pipeline §2.4)
    assert result.floors and result.floors[0].rooms
