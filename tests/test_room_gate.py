"""Per-room post-growth gate tests (Step 07 §4.5).

Unit tests pin the reject paths (area / dim / both) + the vc exemption + the
None-min-dim skip + the OBB short-side metric on a rotated rect. The 33-case
sweep confirms no false positives on valid layouts (lenient min → 0 failures)
and that the gate fires per-room on real geometry (huge min → every non-vc
room rejected).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import shapely.affinity as aff
from shapely.geometry import Polygon
from tests._fixtures import load_growth_fixture

from room_layout.constraints.room_gate import _obb_short_side, check_grown_rooms
from room_layout.schema import LabeledRoom, ShapeInput, SpaceUnitSpec, from_dict
from room_layout.stages.atomize import atomize
from room_layout.stages.corridor import carve_corridors
from room_layout.stages.growth_partition import region_partition_growth
from room_layout.stages.labeling import label_floor
from room_layout.stages.region_graph import build_region_graph
from room_layout.stages.regionize import regionize

GOLDEN = Path(__file__).parent / "golden"


def _rect(w: float, h: float) -> Polygon:
    return Polygon([(0, 0), (w, 0), (w, h), (0, h)])


def _room(id_: str, role: str, area_m2: float, polygon: Polygon) -> LabeledRoom:
    return LabeledRoom(id=id_, polygon=polygon, role=role, usage=None, area_m2=area_m2)


def _spec(
    id_: str,
    role: str,
    area_min_m2: float,
    min_dimension_m: float | None = None,
    anchor_id: str | None = None,
) -> SpaceUnitSpec:
    return SpaceUnitSpec(
        id=id_,
        role=role,
        usage=None,
        area_min_m2=area_min_m2,
        required=True,
        min_dimension_m=min_dimension_m,
        anchor_id=anchor_id,
    )


# ---- unit -----------------------------------------------------------------


def test_room_below_min_area_is_rejected():
    fails = check_grown_rooms(
        [_room("bed", "private", 1.0, _rect(1, 1))],
        {"bed": _spec("bed", "private", area_min_m2=5.0)},
    )
    assert [f.code for f in fails] == ["ROOM_BELOW_MIN_AREA"]
    assert fails[0].stage == "per_room_gate"
    assert fails[0].data["room"] == "bed"


def test_room_below_min_dim_is_rejected():
    # 5 x 0.5 sliver: area 2.5 ok, short side 0.5 < 1.0
    fails = check_grown_rooms(
        [_room("hall", "private", 2.5, _rect(5, 0.5))],
        {"hall": _spec("hall", "private", area_min_m2=0.1, min_dimension_m=1.0)},
    )
    assert [f.code for f in fails] == ["ROOM_BELOW_MIN_DIM"]


def test_room_meeting_both_passes():
    fails = check_grown_rooms(
        [_room("liv", "public", 20.0, _rect(5, 4))],
        {"liv": _spec("liv", "public", area_min_m2=10.0, min_dimension_m=2.0)},
    )
    assert fails == []


def test_room_failing_both_yields_two_records():
    fails = check_grown_rooms(
        [_room("x", "private", 0.4, _rect(2, 0.2))],  # area 0.4, short 0.2
        {"x": _spec("x", "private", area_min_m2=5.0, min_dimension_m=1.0)},
    )
    assert sorted(f.code for f in fails) == ["ROOM_BELOW_MIN_AREA", "ROOM_BELOW_MIN_DIM"]


def test_vc_room_is_exempt():
    # a tiny vc room would fail area + dim, but vc is exempt (fixed anchor geom)
    fails = check_grown_rooms(
        [_room("vc", "vertical_circulation", 0.1, _rect(0.3, 0.3))],
        {
            "vc": _spec(
                "vc", "vertical_circulation", area_min_m2=5.0, min_dimension_m=2.0, anchor_id="a"
            )
        },
    )
    assert fails == []


def test_none_min_dim_skips_dim_check():
    fails = check_grown_rooms(
        [_room("hall", "private", 2.5, _rect(5, 0.5))],  # short side 0.5
        {"hall": _spec("hall", "private", area_min_m2=0.1, min_dimension_m=None)},
    )
    assert fails == []  # area ok, dim skipped


def test_obb_short_side_is_rotation_invariant():
    # a 4 x 1 rect rotated 30° — OBB short side must be ~1, not the axis bbox
    rot = aff.rotate(_rect(4, 1), 30, origin=(0, 0))
    assert _obb_short_side(rot) == pytest.approx(1.0, abs=1e-6)


# ---- 33-case sweep --------------------------------------------------------


def _carve(case_dir: Path):
    with (case_dir / "input.json").open(encoding="utf-8") as f:
        floor = from_dict(ShapeInput, json.load(f)["shape"]).floors[0]
    fixture = load_growth_fixture(case_dir)
    atoms = atomize(floor)
    regions = regionize(floor, atoms=atoms)
    rg = build_region_graph(floor, atoms=atoms, regions=regions)
    growth = region_partition_growth(floor, fixture, regions=regions, region_graph=rg)
    return carve_corridors(floor, growth, regions=regions, region_graph=rg), regions, floor


_CASES = sorted(p.name for p in GOLDEN.iterdir() if p.is_dir())


@pytest.mark.parametrize("case", _CASES)
def test_lenient_min_passes_all_rooms(case):
    cl, regions, floor = _carve(GOLDEN / case)
    specs = [_spec(gr.name, gr.role, area_min_m2=0.1) for gr in cl.rooms]
    fl = label_floor(cl, regions, specs, level=floor.level)
    assert check_grown_rooms(fl.rooms, {s.id: s for s in specs}) == []


@pytest.mark.parametrize("case", _CASES)
def test_huge_min_rejects_every_room(case):
    cl, regions, floor = _carve(GOLDEN / case)
    specs = [_spec(gr.name, gr.role, area_min_m2=1e6) for gr in cl.rooms]
    fl = label_floor(cl, regions, specs, level=floor.level)
    fails = check_grown_rooms(fl.rooms, {s.id: s for s in specs})
    assert len(fails) == len(fl.rooms)  # every (non-vc) room rejected on area
    assert all(f.code == "ROOM_BELOW_MIN_AREA" for f in fails)
