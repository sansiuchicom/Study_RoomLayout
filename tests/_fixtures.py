"""Golden fixture loaders (Step 04 §4.7).

``growth_fixture.json`` carries Cell's exact ``LayoutFixture`` (manual seeds +
role tables) for the algorithm-faithful 33-case growth goldens (S04-D7 a1).
Seeded by ``scripts/cell_growth_fixtures_to_json.py``.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from room_layout.stages.room_growth import LayoutFixture, RoomSpec


def load_growth_fixture(case_dir: Path) -> LayoutFixture:
    """Build a ``LayoutFixture`` from ``<case_dir>/growth_fixture.json``."""
    with (case_dir / "growth_fixture.json").open(encoding="utf-8") as f:
        d = json.load(f)

    rooms = tuple(
        RoomSpec(
            name=r["name"],
            role=r["role"],
            seed_position=(tuple(r["seed_position"]) if r["seed_position"] is not None else None),
            target_aspect_range=(
                tuple(r["target_aspect_range"]) if r["target_aspect_range"] is not None else None
            ),
        )
        for r in d["rooms"]
    )
    return LayoutFixture(
        case_index=d["case_index"],
        case_name=d["case_name"],
        footprint_area_m2=d["footprint_area_m2"],
        rooms=rooms,
        role_min_areas={k: float(v) for k, v in d["role_min_areas"].items()},
        role_aspect_ranges={k: tuple(v) for k, v in d["role_aspect_ranges"].items()},
        max_l_rooms=d["max_l_rooms"],
        detour_threshold=d["detour_threshold"],
    )


def to_auto_fixture(fixture: LayoutFixture) -> LayoutFixture:
    """Same program with all seeds stripped → ``auto_seed=True`` (S04-D7).

    Models the production path (the new schema has no ``seed_position``): same
    rooms / roles / role tables, but seed placement is computed by
    ``auto_place_seeds_by_cells`` instead of taken from Cell's manual coords.
    """
    auto_rooms = tuple(replace(r, seed_position=None) for r in fixture.rooms)
    return replace(fixture, rooms=auto_rooms)
