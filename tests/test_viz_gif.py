"""make_gif smoke tests (Step 08 §4.7 / S08-D5).

Smoke only (file written, multi-frame, uniform frame size) — not pixel-golden.
Needs the viz extra (matplotlib stage renderers + pillow).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("PIL")

from PIL import Image, ImageSequence  # noqa: E402
from tests._fixtures import load_growth_fixture  # noqa: E402

from room_layout.schema import ProgramRequest, ShapeInput, SpaceUnitSpec, from_dict  # noqa: E402
from room_layout.viz.gif import make_gif  # noqa: E402

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


def test_make_gif_writes_multiframe_gif(tmp_path):
    shape, program = _shape_and_program("case_04_50py_c_shape")
    out = make_gif(shape, program, seed=42, out_path=tmp_path / "p.gif", frame_ms=500)
    assert Path(out).exists() and Path(out).stat().st_size > 0

    im = Image.open(out)
    frames = list(ImageSequence.Iterator(im))
    # full happy-path run emits 7 renderable stages (seed omitted — S08-D4)
    assert len(frames) == 7
    # all frames padded to one canvas size (no jitter/crop)
    assert len({f.size for f in frames}) == 1


def test_make_gif_returns_path_string(tmp_path):
    shape, program = _shape_and_program("case_01_30py_flat")
    out = make_gif(shape, program, seed=1, out_path=tmp_path / "q.gif")
    assert isinstance(out, str)
    assert out.endswith("q.gif")
