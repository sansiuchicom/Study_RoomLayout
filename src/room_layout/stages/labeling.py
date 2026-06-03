"""Labeling (Pipeline §3.8) — grown rooms → `LabeledRoom` / `LabeledFloorLayout`.

Plan reference: ``007_Step07_EntryPoint_Plan.md`` §4.3.

The growth half works in a collapsed 4-class role space (S04-D3): a
``GrownRoom`` carries the Cell ``GrowthRole`` (public / private / service /
wet) and only its ``name`` (== ``SpaceUnitSpec.id``, preserved by
``program_adapter``), **not** the authoritative output role. Labeling recovers
the 7-class ``role`` + the human ``usage`` from the original ``SpaceUnitSpec``
by id, polygonizes the room (§4.2), and assembles the per-floor
``LabeledFloorLayout`` (rooms + corridor polygons).

``area_m2`` is taken from the **polygon**, not from ``GrownRoom.area_m2``
(S07-D6): the output geometry is the single source of truth, so the reported
area can never disagree with the emitted polygon (the two match within float
tolerance — the §4.2 area-conservation test).

Not handled here (by design):

- ``vertical_circulation`` rooms — anchor-locked, excluded from growth
  (``program_adapter``), re-inserted as fixed rooms in §4.4.
- ``corridor`` regions — an *output* role (D004); they become
  ``corridor_polygons``, never rooms.
- ``leftover_region_ids`` — unassigned regions cleanup could not absorb
  (usually empty); a coverage concern surfaced by ``run()``, not emitted here.
"""

from __future__ import annotations

from collections.abc import Iterable

from shapely.geometry import Polygon

from room_layout.schema import LabeledFloorLayout, LabeledRoom, SpaceUnitSpec
from room_layout.stages.corridor import CorridoredLayout
from room_layout.stages.polygonize import (
    build_region_polygons,
    polygonize_corridors,
    polygonize_room,
)
from room_layout.stages.regionize import Region
from room_layout.stages.room_growth import GrownRoom


def label_room(grown: GrownRoom, spec: SpaceUnitSpec, polygon: Polygon) -> LabeledRoom:
    """Build a `LabeledRoom` from a grown room, its spec, and its polygon.

    Recovers the authoritative 7-class ``role`` + ``usage`` from ``spec``
    (growth collapsed the role to 4-class — S04-D3). ``area_m2`` is the
    polygon's area (S07-D6). ``anchor_id`` carries through (``None`` for grown
    rooms — vc rooms are re-inserted separately in §4.4).
    """
    return LabeledRoom(
        id=spec.id,
        polygon=polygon,
        role=spec.role,
        usage=spec.usage,
        area_m2=polygon.area,
        anchor_id=spec.anchor_id,
    )


def label_floor(
    corridored: CorridoredLayout,
    regions: Iterable[Region],
    specs: Iterable[SpaceUnitSpec],
    *,
    level: int,
) -> LabeledFloorLayout:
    """Assemble one floor's `LabeledFloorLayout` from its carved layout.

    Each grown room is polygonized (§4.2) and labeled (role/usage recovered via
    ``GrownRoom.name == SpaceUnitSpec.id``); corridor regions become
    ``corridor_polygons``. Raises ``KeyError`` if a grown room has no matching
    spec (a ``program_adapter`` invariant violation — should never happen).
    """
    specs_by_id = {s.id: s for s in specs}
    region_poly = build_region_polygons(regions)
    rooms = [
        label_room(
            gr,
            specs_by_id[gr.name],
            polygonize_room(gr.region_ids, region_poly, room_name=gr.name),
        )
        for gr in corridored.rooms
    ]
    corridor_polygons = polygonize_corridors(corridored.corridor_region_ids, region_poly)
    return LabeledFloorLayout(level=level, rooms=rooms, corridor_polygons=corridor_polygons)
