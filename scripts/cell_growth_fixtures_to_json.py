"""One-shot converter: Cell 33 LayoutFixtures → per-case growth_fixture.json.

Plan reference: ``004_Step04_AlgorithmCore_Plan.md`` §4.7 + S04-D7.

Step 03's ``cell_fixtures_to_json.py`` already wrote ``input.json`` per case
(shape + a *new-schema* ``ProgramRequest``) but **dropped the manual seed
positions** (seeds were a Phase 6+ concern then). The 33-case growth goldens
follow strategy (a1): drive growth with Cell's exact ``LayoutFixture`` —
manual seeds + role tables — to reproduce Cell's results faithfully. This
script emits that fixture as ``growth_fixture.json`` alongside ``input.json``.

``input.json`` is left untouched: its seed-less ``ProgramRequest`` is the
*auto-placement* path input (program_adapter, 4.14; auto golden coverage,
4.12). ``growth_fixture.json`` is the *manual-seed* algorithm-faithful path.

After this runs once and goldens are committed, Cell's Python fixtures stay
retired (S03-D7) — the script is kept in-tree as documentation.

Usage::

    PYTHONPATH=src python scripts/cell_growth_fixtures_to_json.py
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CELL_ALGORITHM_ROOT = REPO_ROOT / "archive" / "celllayout" / "algorithm"
GOLDEN_DIR = REPO_ROOT / "tests" / "golden"

sys.path.insert(0, str(CELL_ALGORITHM_ROOT))

from celllayout_tf.layout_fixtures import selected_fixtures  # noqa: E402


def _room_to_dict(room) -> dict:
    return {
        "name": room.name,
        "role": room.role,
        "seed_position": list(room.seed_position) if room.seed_position is not None else None,
        "target_aspect_range": (
            list(room.target_aspect_range) if room.target_aspect_range is not None else None
        ),
    }


def _fixture_to_dict(fixture) -> dict:
    return {
        "case_index": fixture.case_index,
        "case_name": fixture.case_name,
        "footprint_area_m2": fixture.footprint_area_m2,
        "rooms": [_room_to_dict(r) for r in fixture.rooms],
        "role_min_areas": dict(fixture.role_min_areas),
        "role_aspect_ranges": {k: list(v) for k, v in fixture.role_aspect_ranges.items()},
        "max_l_rooms": fixture.max_l_rooms,
        "detour_threshold": fixture.detour_threshold,
    }


def _case_dir_for(idx: int) -> Path:
    matches = sorted(GOLDEN_DIR.glob(f"case_{idx:02d}_*"))
    if len(matches) != 1:
        raise RuntimeError(f"case {idx}: expected exactly one case dir, found {matches}")
    return matches[0]


def main() -> int:
    fixtures = selected_fixtures()
    written = 0
    for fixture in fixtures:
        case_dir = _case_dir_for(fixture.case_index)
        path = case_dir / "growth_fixture.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(_fixture_to_dict(fixture), f, indent=2, ensure_ascii=False)
            f.write("\n")
        written += 1
        print(f"  case {fixture.case_index:2d}: wrote {path.relative_to(REPO_ROOT)}")
    print(f"\nwrote {written}/{len(fixtures)} growth_fixture.json files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
