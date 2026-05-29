"""growth_partition deferred-gap PoC (Step 04 §4.11).

`auto_place_seeds_by_cells` can return fewer than K placements when the floor
has fewer seedable vertex-cells than rooms requested, but
`region_partition_growth` indexes `placements[si]` assuming exactly K — so an
over-subscribed program crashes with ``IndexError`` instead of failing
gracefully. This is faithful to Cell (same assumption) and is not triggered by
the 33 showcase fixtures (all have ample regions). Graceful handling — a
program-feasibility gate raising ``DomainGateFailure`` / ``valid=False`` — is a
Step 07 concern. Pinned strict so the fix flips it loudly.
"""

from __future__ import annotations

import pytest

from room_layout.schema import FloorShape, ShapePart
from room_layout.stages.atomize import atomize
from room_layout.stages.growth_partition import region_partition_growth
from room_layout.stages.region_graph import build_region_graph
from room_layout.stages.regionize import regionize
from room_layout.stages.room_growth import (
    DEFAULT_ROLE_ASPECT_RANGES,
    DEFAULT_ROLE_MIN_AREAS,
    LayoutFixture,
    RoomSpec,
)


@pytest.mark.xfail(
    reason="K > seedable regions: auto_place_seeds_by_cells returns < K placements "
    "(faithful Cell), but region_partition_growth indexes placements[si] → IndexError "
    "instead of a graceful failure. Not triggered by the 33 fixtures; graceful handling "
    "(program-feasibility gate / DomainGateFailure) deferred to Step 07.",
    strict=True,
)
def test_more_rooms_than_seedable_regions_fails_gracefully():
    # 1x1 floor → a single region; an auto program of 2 rooms over-subscribes it.
    floor = FloorShape(
        level=1,
        parts=[ShapePart(exterior=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)))],
        floor_to_floor_height=None,
    )
    atoms = atomize(floor)
    regions = regionize(floor, atoms=atoms)
    rg = build_region_graph(floor, atoms=atoms, regions=regions)
    fixture = LayoutFixture(
        case_index=0,
        case_name="tiny",
        footprint_area_m2=1.0,
        rooms=(RoomSpec("a", "public", None), RoomSpec("b", "private", None)),
        role_min_areas=dict(DEFAULT_ROLE_MIN_AREAS),
        role_aspect_ranges=dict(DEFAULT_ROLE_ASPECT_RANGES),
    )
    # Desired: a clean ValueError, not IndexError. Currently raises IndexError → xfail.
    with pytest.raises(ValueError):
        region_partition_growth(floor, fixture, regions=regions, region_graph=rg)
