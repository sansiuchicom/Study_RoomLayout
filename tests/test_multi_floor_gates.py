"""Cross-floor gates — vertical-circulation continuity (Step 10 §4.4, S10-D6).

Continuity is on EMITTED vc rooms (a floor emits a stair only if its program
carries a vc spec — review #5), vertical-only (review #6). Integration cases go
through `run()`; the N-partial-core cases unit-test `check_vertical_continuity`.
"""

from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from room_layout import run
from room_layout.constraints.multi_floor import check_vertical_continuity
from room_layout.schema import ProgramRequest, ShapeInput
from room_layout.schema.failure import DomainGateFailure
from room_layout.schema.geometry import FloorShape, ShapePart, VerticalAnchor
from room_layout.schema.program import SpaceUnitSpec


def _floor(level: int) -> FloorShape:
    return FloorShape(
        level=level,
        parts=[ShapePart(exterior=((0, 0), (12, 0), (12, 10), (0, 10)))],
        floor_to_floor_height=3.0,
    )


def _spec(sid: str, role: str, **kw) -> SpaceUnitSpec:
    return SpaceUnitSpec(id=sid, role=role, usage=None, area_min_m2=0.5, required=True, **kw)


def _anchor(aid: str, levels: tuple[int, int], x0: float = 0.0) -> VerticalAnchor:
    return VerticalAnchor(
        id=aid,
        kind="stair_core",
        footprint_polygon=Polygon([(x0, 0), (x0 + 2, 0), (x0 + 2, 3), (x0, 3)]),
        floor_range=levels,
        host_role="vertical_circulation",
    )


def _vc(sid: str, aid: str) -> SpaceUnitSpec:
    return _spec(sid, "vertical_circulation", anchor_id=aid)


# --- run() integration -----------------------------------------------------


def test_one_shared_core_is_continuous():
    shape = ShapeInput(
        name="h", floors=[_floor(1), _floor(2), _floor(3)], vertical_anchors=[_anchor("s", (1, 3))]
    )
    prog = ProgramRequest(
        target_type="house",
        floor_programs={
            1: [_spec("living", "public"), _spec("kitchen", "wet"), _vc("st1", "s")],
            2: [_spec("bed1", "private"), _vc("st2", "s")],
            3: [_spec("bed2", "private"), _vc("st3", "s")],
        },
    )
    result = run(shape, prog, seed=42)
    assert "VERTICAL_CIRCULATION_DISCONTINUOUS" not in {f.code for f in result.failure_records}
    assert result.valid is True


def test_floor_missing_vc_spec_is_discontinuous():
    # the stair anchor spans 1-3, but floor 2's program omits the vc spec → no
    # stair room emitted there → floor 2 is vertically isolated (review #5).
    shape = ShapeInput(
        name="h", floors=[_floor(1), _floor(2), _floor(3)], vertical_anchors=[_anchor("s", (1, 3))]
    )
    prog = ProgramRequest(
        target_type="house",
        floor_programs={
            1: [_spec("living", "public"), _spec("kitchen", "wet"), _vc("st1", "s")],
            2: [_spec("bed1", "private"), _spec("bed2", "private")],  # no vc spec
            3: [_spec("bed3", "private"), _vc("st3", "s")],
        },
    )
    result = run(shape, prog, seed=42)
    recs = [f for f in result.failure_records if f.code == "VERTICAL_CIRCULATION_DISCONTINUOUS"]
    assert result.valid is False
    assert len(recs) == 1
    assert recs[0].data["isolated_levels"] == [2]
    # partial floors still rendered (never-crashes)
    assert len(result.floors) == 3


# --- unit: N partial cores -------------------------------------------------


def _shape_program(n_floors: int, anchors, vc_by_level):
    floors = [_floor(level) for level in range(1, n_floors + 1)]
    fps = {}
    for level in range(1, n_floors + 1):
        specs = [_spec(f"r{level}", "private")]
        for aid in vc_by_level.get(level, []):
            specs.append(_vc(f"st{level}_{aid}", aid))
        fps[level] = specs
    shape = ShapeInput(name="h", floors=floors, vertical_anchors=anchors)
    return shape, ProgramRequest(target_type="house", floor_programs=fps)


def test_partial_cores_with_a_gap_are_discontinuous():
    # stair A serves {1,2}, stair B serves {3,4}; nothing bridges 2↔3.
    shape, prog = _shape_program(
        4,
        anchors=[_anchor("A", (1, 2), x0=0.0), _anchor("B", (3, 4), x0=9.0)],
        vc_by_level={1: ["A"], 2: ["A"], 3: ["B"], 4: ["B"]},
    )
    with pytest.raises(DomainGateFailure) as ei:
        check_vertical_continuity(shape, prog)
    assert ei.value.record.code == "VERTICAL_CIRCULATION_DISCONTINUOUS"
    assert ei.value.record.data["components"] == [[1, 2], [3, 4]]


def test_partial_cores_that_overlap_are_continuous():
    # stair A serves {1,2}, stair B serves {2,3}; level 2 bridges them.
    shape, prog = _shape_program(
        3,
        anchors=[_anchor("A", (1, 2), x0=0.0), _anchor("B", (2, 3), x0=9.0)],
        vc_by_level={1: ["A"], 2: ["A", "B"], 3: ["B"]},
    )
    check_vertical_continuity(shape, prog)  # no raise


def test_single_floor_is_vacuously_continuous():
    shape = ShapeInput(name="h", floors=[_floor(1)], vertical_anchors=[])
    prog = ProgramRequest(target_type="house", floor_programs={1: [_spec("r", "private")]})
    check_vertical_continuity(shape, prog)  # no raise (single floor)


# --- vc-only / empty floor never-crashes (10.6, S10-D12) -------------------


def test_vc_only_floor_is_valid_and_does_not_crash():
    # floor 2 is circulation-only (just the shared stair, no growable room).
    # Building cardinality passes (floor 1 has public/private/wet); the
    # no-growable floor must emit just its vc room, not crash run().
    shape = ShapeInput(
        name="h", floors=[_floor(1), _floor(2)], vertical_anchors=[_anchor("s", (1, 2))]
    )
    prog = ProgramRequest(
        target_type="house",
        floor_programs={
            1: [
                _spec("living", "public"),
                _spec("bed", "private"),
                _spec("kitchen", "wet"),
                _vc("st1", "s"),
            ],
            2: [_vc("st2", "s")],  # vc-only floor
        },
    )
    result = run(shape, prog, seed=42)  # must not raise
    assert result.valid is True, [f.code for f in result.failure_records]
    assert [r.role for r in result.floors[1].rooms] == ["vertical_circulation"]


def test_empty_floor_does_not_crash_and_is_flagged_discontinuous():
    # floor 2 has an empty program → no rooms, no vc → no crash; continuity
    # flags it isolated (S10-D6) so the building is valid=False, not crashed.
    shape = ShapeInput(
        name="h", floors=[_floor(1), _floor(2)], vertical_anchors=[_anchor("s", (1, 1))]
    )
    prog = ProgramRequest(
        target_type="house",
        floor_programs={
            1: [
                _spec("living", "public"),
                _spec("bed", "private"),
                _spec("kitchen", "wet"),
                _vc("st1", "s"),
            ],
            2: [],  # empty floor
        },
    )
    result = run(shape, prog, seed=42)  # must not raise
    assert result.valid is False
    assert "VERTICAL_CIRCULATION_DISCONTINUOUS" in {f.code for f in result.failure_records}
    assert result.floors[1].rooms == []  # empty floor emits nothing, no crash


def test_vc_only_floor_emits_labeling_stage_to_trace():
    # S10 review #1: a vc-only floor short-circuits growth but must still emit
    # its `labeling` stage, or the debug JSON/SVG silently drop that floor.
    shape = ShapeInput(
        name="h", floors=[_floor(1), _floor(2)], vertical_anchors=[_anchor("s", (1, 2))]
    )
    prog = ProgramRequest(
        target_type="house",
        floor_programs={
            1: [
                _spec("living", "public"),
                _spec("bed", "private"),
                _spec("kitchen", "wet"),
                _vc("st1", "s"),
            ],
            2: [_vc("st2", "s")],  # vc-only floor
        },
    )
    seen: list[tuple[int | None, str]] = []
    run(shape, prog, seed=42, on_stage=lambda s: seen.append((s.level, s.stage_id)))
    labeling_levels = [lvl for lvl, sid in seen if sid == "labeling"]
    assert labeling_levels == [1, 2]  # both floors traced, incl. the vc-only one
