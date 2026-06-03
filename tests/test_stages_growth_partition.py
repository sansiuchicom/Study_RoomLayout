"""growth_partition oversubscription guard (Step 07 §4.11 ①).

`auto_place_seeds_by_cells` can return fewer than K placements when the floor
has fewer seedable vertex-cells than rooms requested. `region_partition_growth`
now **guards** this: instead of an ``IndexError`` on ``placements[si]``, it
raises ``DomainGateFailure`` (``GROWTH_OVERSUBSCRIBED``), which ``run()`` catches
→ ``valid=False`` (graceful, never crashes out). Not triggered by the 33
showcase fixtures (ample regions); the minimal direct trigger (1×1 floor,
2-room program) is below.
"""

from __future__ import annotations

import pytest

from room_layout.schema import FloorShape, ShapePart
from room_layout.schema.failure import DomainGateFailure
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
    # K=2 rooms but only 1 seedable region → graceful DomainGateFailure (S07 §4.11 ①),
    # which run() catches → valid=False (was an IndexError before the guard).
    with pytest.raises(DomainGateFailure) as exc:
        region_partition_growth(floor, fixture, regions=regions, region_graph=rg)
    assert exc.value.record.code == "GROWTH_OVERSUBSCRIBED"
