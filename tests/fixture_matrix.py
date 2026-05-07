"""Step 04 fixture matrix — ID → file mapping + expected_failure metadata (S04-D8).

Matrix metadata is kept here (not inside fixture JSON) so that fixture
files remain schema-clean for `from_json(BuildingInput, ...)` (D017
strict Literal validation).
"""
from __future__ import annotations

from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

MATRIX: dict[str, dict] = {
    "A1": {
        "file": "apartment_minimal.json",
        "expected_failure": None,
    },
    "A2": {
        "file": "apartment_4bed_2bath.json",
        "expected_failure": None,
    },
    "B1": {
        "file": "apartment_l_shape.json",
        "expected_failure": None,
    },
    "R1": {
        "file": "apartment_no_bath.json",
        "expected_failure": "ProgramInstantiationFailure",
        "verified_at": "Step 04",
    },
    "R2": {
        "file": "apartment_too_small.json",
        "expected_failure": "AreaGateFailure",
        "verified_at": "Step 06",
    },
}


def fixture_path(matrix_id: str) -> Path:
    return FIXTURES_DIR / MATRIX[matrix_id]["file"]
