"""viz.svg.render strict-kwarg tests (Step 06 §4.7, S06-D11).

Step 03 frame silently ignored every layer kwarg (atoms / regions / spine /
anchors / ...). Step 05 produced real atoms but the renderer still drew
only a 100mm reference grid — the silent ignore hid the disconnect
(외부 review #11).

Step 06 fix is narrow: atoms / regions / spine raise ValueError when
non-None, since their producing Stages (04, 04, 09) land at Step 07 with
real rendering. Other kwargs remain silent no-ops until their producing
Stage lands.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from proto3.schema.input import BuildingInput
from proto3.schema.serialize import from_json
from proto3.viz.svg import render


_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load_minimal() -> BuildingInput:
    return from_json(BuildingInput, _FIXTURES / "apartment_minimal.json")


def test_render_no_kwargs_still_works(tmp_path: Path):
    """Baseline — Step 03 contract preserved when only out_path is given."""
    out = tmp_path / "minimal.svg"
    render(_load_minimal(), out_path=str(out))
    assert out.is_file()
    assert out.stat().st_size > 0


@pytest.mark.parametrize("kwarg_name", ["atoms", "regions", "spine"])
def test_render_step07_kwargs_raise_when_non_none(tmp_path: Path, kwarg_name):
    """atoms / regions / spine are Step 07 territory — Step 06 must not
    silently swallow them."""
    out = tmp_path / "x.svg"
    sentinel = ["something_truthy"]   # any non-None value triggers
    with pytest.raises(ValueError, match="Step 07 territory"):
        render(_load_minimal(), out_path=str(out), **{kwarg_name: sentinel})


def test_render_step07_kwargs_none_passes(tmp_path: Path):
    """Explicit None should pass — only non-None values trip the strict guard."""
    out = tmp_path / "explicit_none.svg"
    render(_load_minimal(), out_path=str(out),
           atoms=None, regions=None, spine=None)
    assert out.is_file()


def test_render_other_kwargs_remain_silent_noops(tmp_path: Path):
    """anchors / graph / role_scores / slots / seeds / grown / doors / failure
    stay silent until their producing Stage lands (Step 03 contract — narrow
    Step 06 scope, S06-D11)."""
    out = tmp_path / "silent.svg"
    render(
        _load_minimal(),
        out_path=str(out),
        anchors="ignored",
        graph="ignored",
        role_scores="ignored",
        slots="ignored",
        seeds="ignored",
        grown="ignored",
        doors="ignored",
        failure="ignored",
    )
    assert out.is_file()
