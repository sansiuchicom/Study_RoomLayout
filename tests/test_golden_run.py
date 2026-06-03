"""End-to-end run() golden regression across the 33 showcase fixtures (§4.9).

Drives each case through the public ``run()`` with a program synthesized from
the case's ``growth_fixture`` (corpus A, S07-D2 — same auto-seed path as the
``corridor_auto`` golden, now carried through labeling) and goldens a digest of
the ``LabeledRoomLayout``: ``valid`` + ``failure_codes`` + per-room
id/role/usage/area + per-floor corridor count/area.

The digest is GEOS-**stable** (region-id-derived areas rounded to 6 dp, like
the ``layout`` / ``corridor`` region-id digests — not the coordinate-level
``atomize`` / ``regionize`` goldens), but still run under the canonical runtime
(IfcOpenHouse, GEOS 3.14.1) like the rest of the suite.

Note: the program is the case's *own* rooms. A few abstract shapes lack a
``public`` or ``wet`` room, so apartment ``min_cardinality`` rejects them →
those goldens correctly capture ``valid=False`` + the cardinality failure (the
failure path is part of the contract). Realistic apartment fixtures + dedicated
failure-injection goldens are corpus B (§4.10).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests._fixtures import load_growth_fixture
from tests._golden import assert_golden

from room_layout import run
from room_layout.schema import ProgramRequest, ShapeInput, SpaceUnitSpec, from_dict

GOLDEN_DIR = Path(__file__).parent / "golden"
CASE_DIRS = sorted(p for p in GOLDEN_DIR.iterdir() if p.is_dir() and p.name.startswith("case_"))
_CASE_IDS = [p.name for p in CASE_DIRS] or None


def _shape_and_program(case_dir: Path) -> tuple[ShapeInput, ProgramRequest]:
    with (case_dir / "input.json").open(encoding="utf-8") as f:
        shape = from_dict(ShapeInput, json.load(f)["shape"])
    level = shape.floors[0].level
    fx = load_growth_fixture(case_dir)
    specs = [
        SpaceUnitSpec(id=r.name, role=r.role, usage=None, area_min_m2=0.5, required=True)
        for r in fx.rooms
    ]
    return shape, ProgramRequest(target_type="apartment", floor_programs={level: specs})


def run_golden(result) -> dict:
    """GEOS-stable digest of a ``LabeledRoomLayout`` (rooms sorted by id)."""
    return {
        "valid": result.valid,
        "failure_codes": sorted(f.code for f in result.failure_records),
        "floors": [
            {
                "level": fl.level,
                "n_rooms": len(fl.rooms),
                "rooms": [
                    {
                        "id": rm.id,
                        "role": rm.role,
                        "usage": rm.usage,
                        "area_m2": round(rm.area_m2, 6),
                        "anchor_id": rm.anchor_id,
                    }
                    for rm in sorted(fl.rooms, key=lambda r: r.id)
                ],
                "n_corridor_polygons": len(fl.corridor_polygons),
                "corridor_area_m2": round(sum(p.area for p in fl.corridor_polygons), 6),
            }
            for fl in result.floors
        ],
    }


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=_CASE_IDS)
def test_run_golden(case_dir: Path, update_goldens: bool):
    shape, program = _shape_and_program(case_dir)
    result = run(shape, program, seed=42)
    assert_golden(run_golden(result), case_dir / "run.json", update_goldens=update_goldens)
