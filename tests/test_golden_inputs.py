"""Smoke tests for `tests/golden/<case>/input.json` integrity.

Parametrized over every discovered case directory. Verifies each
`input.json` loads cleanly via `from_dict(ShapeInput, ...)` +
`from_dict(ProgramRequest, ...)`. Plan §4.3 verification — guards
against fixture corruption and against the converter
(`scripts/cell_fixtures_to_json.py`) drifting from the schema.
"""

import json
from pathlib import Path

import pytest

from room_layout.schema import ProgramRequest, ShapeInput, from_dict

GOLDEN_DIR = Path(__file__).parent / "golden"


def _case_dirs() -> list[Path]:
    """Return every `case_*/` subdirectory of `tests/golden/`."""
    if not GOLDEN_DIR.exists():
        return []
    return sorted(p for p in GOLDEN_DIR.iterdir() if p.is_dir() and p.name.startswith("case_"))


CASE_DIRS = _case_dirs()


@pytest.mark.parametrize(
    "case_dir",
    CASE_DIRS,
    ids=[p.name for p in CASE_DIRS] if CASE_DIRS else None,
)
def test_input_json_round_trips(case_dir):
    """Each fixture's `input.json` must parse into `ShapeInput` + `ProgramRequest`."""
    input_path = case_dir / "input.json"
    assert input_path.exists(), f"missing {input_path}"

    with input_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert "shape" in data and "program" in data, (
        f"{input_path}: expected top-level 'shape' + 'program' keys, got {list(data)}"
    )

    shape = from_dict(ShapeInput, data["shape"])
    program = from_dict(ProgramRequest, data["program"])

    # Step 03 single-floor convention (Pipeline §2.1 / S03-D7).
    assert shape.name, f"{case_dir.name}: empty ShapeInput.name"
    assert len(shape.floors) == 1, (
        f"{case_dir.name}: expected single floor (v1), got {len(shape.floors)}"
    )
    assert shape.floors[0].level == 1
    assert shape.vertical_anchors == [], f"{case_dir.name}: Cell fixtures have no anchors"
    assert program.target_type == "apartment", (
        f"{case_dir.name}: expected target_type='apartment', got {program.target_type!r}"
    )
    assert 1 in program.floor_programs, f"{case_dir.name}: expected floor 1 in floor_programs"


def test_thirty_three_cases_present():
    """All 33 Cell showcase cases were converted (S03-D9 full-port)."""
    assert len(CASE_DIRS) == 33, (
        f"expected 33 case directories under tests/golden/, found {len(CASE_DIRS)}"
    )
