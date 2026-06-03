"""Debug-run trace persistence test (Step 07 §4.7).

``write_debug_run`` runs ``run()`` with a ``DebugRunWriter`` callback and
persists the D006 layout (``NN_<stage>.json`` + ``final.json`` + ``manifest``)
to a directory. Writes go to ``tmp_path`` (not the real ``outputs/``).
"""

from __future__ import annotations

import json
from pathlib import Path

from tests._fixtures import load_growth_fixture

from room_layout.debug_run import write_debug_run
from room_layout.schema import ProgramRequest, ShapeInput, SpaceUnitSpec, from_dict

GOLDEN = Path(__file__).parent / "golden"


def _shape_and_program(case: str):
    with (GOLDEN / case / "input.json").open(encoding="utf-8") as f:
        shape = from_dict(ShapeInput, json.load(f)["shape"])
    level = shape.floors[0].level
    fx = load_growth_fixture(GOLDEN / case)
    specs = [
        SpaceUnitSpec(id=r.name, role=r.role, usage=None, area_min_m2=0.5, required=True)
        for r in fx.rooms
    ]
    return shape, ProgramRequest(target_type="apartment", floor_programs={level: specs})


def test_write_debug_run_persists_stages_and_manifest(tmp_path):
    shape, program = _shape_and_program("case_01_30py_flat")
    result, out_dir = write_debug_run(shape, program, seed=42, out_root=tmp_path, run_id="t")

    assert result.valid is True
    assert out_dir == tmp_path / "t"

    # one JSON per emitted stage; per-floor stages suffixed _f<level> (D006, no
    # multi-floor overwrite). input has level=None → no suffix.
    lvl = shape.floors[0].level
    expected = ["00_input"] + [
        f"{i:02d}_{name}_f{lvl}"
        for i, name in [
            (1, "atomize"),
            (2, "regionize"),
            (3, "region_graph"),
            (4, "growth"),
            (5, "corridor"),
            (6, "labeling"),
        ]
    ]
    for stem in expected:
        p = out_dir / f"{stem}.json"
        assert p.exists(), stem
        json.loads(p.read_text(encoding="utf-8"))  # valid JSON

    final = json.loads((out_dir / "final.json").read_text(encoding="utf-8"))
    assert final["valid"] is True
    assert final["floors"][0]["rooms"]

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["seed"] == 42
    assert manifest["package_version"]
    assert manifest["config"] == {"debug_artifacts": False}
    assert "started_at" in manifest and "duration_ms" in manifest


def test_default_run_id_is_seed_prefixed(tmp_path):
    shape, program = _shape_and_program("case_01_30py_flat")
    _, out_dir = write_debug_run(shape, program, seed=7, out_root=tmp_path)
    assert out_dir.name.startswith("seed7_")
