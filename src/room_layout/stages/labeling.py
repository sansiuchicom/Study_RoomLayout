"""Labeling (Pipeline §3.8) — grown rooms → `LabeledRoom` / `LabeledFloorLayout`.

Plan reference: ``007_Step07_EntryPoint_Plan.md`` §4.3 + §4.4.

The growth half works in a collapsed 4-class role space (S04-D3): a
``GrownRoom`` carries the Cell ``GrowthRole`` (public / private / service /
wet) and only its ``name`` (== ``SpaceUnitSpec.id``, preserved by
``program_adapter``), **not** the authoritative output role. Labeling recovers
the 7-class ``role`` + the human ``usage`` from the original ``SpaceUnitSpec``
by id, polygonizes the room (§4.2), re-inserts ``vertical_circulation`` anchor
rooms (§4.4), and assembles the per-floor ``LabeledFloorLayout`` (rooms +
corridor polygons).

``area_m2`` is taken from the **polygon**, not from ``GrownRoom.area_m2``
(S07-D6): the output geometry is the single source of truth, so the reported
area can never disagree with the emitted polygon (the two match within float
tolerance — the §4.2 area-conservation test).

``vertical_circulation`` rooms (§4.4): excluded from growth and re-inserted
here as **fixed** rooms whose polygon is the linked
``VerticalAnchor.footprint_polygon`` (the same polygon ``subtract_anchors``
punched out before growth, S04-D4) — so grown rooms and the anchor room tile
without overlap.

Not handled here (by design):

- ``corridor`` regions — an *output* role (D004); they become
  ``corridor_polygons``, never rooms.
- ``leftover_region_ids`` — unassigned regions cleanup could not absorb
  (usually empty); a coverage concern surfaced by ``run()``, not emitted here.
"""

from __future__ import annotations

from collections.abc import Iterable

from shapely.geometry import Polygon

from room_layout.schema import LabeledFloorLayout, LabeledRoom, SpaceUnitSpec, VerticalAnchor
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
    rooms — vc rooms are re-inserted separately by ``vc_rooms``).
    """
    return LabeledRoom(
        id=spec.id,
        polygon=polygon,
        role=spec.role,
        usage=spec.usage,
        area_m2=polygon.area,
        anchor_id=spec.anchor_id,
    )


def vc_rooms(
    specs: Iterable[SpaceUnitSpec],
    anchors: Iterable[VerticalAnchor],
) -> list[LabeledRoom]:
    """Fixed `LabeledRoom`s for ``vertical_circulation`` specs (S04-D4 re-insert).

    vc rooms are excluded from growth (``program_adapter``) and re-inserted here
    as fixed polygons: the polygon is the linked
    ``VerticalAnchor.footprint_polygon`` — the same polygon ``subtract_anchors``
    punched out before growth — so the grown rooms and the vc room tile without
    overlap. ``host_role=None`` shafts carry no vc spec, so no room is emitted
    for them (they stay forbidden holes). ``area_m2`` is the footprint area.

    Raises ``KeyError`` if a vc spec's ``anchor_id`` has no matching anchor (a
    validator invariant — ``ANCHOR_ID_NOT_FOUND`` is checked upstream).
    """
    anchors_by_id = {a.id: a for a in anchors}
    rooms: list[LabeledRoom] = []
    for spec in specs:
        if spec.role != "vertical_circulation":
            continue
        poly = anchors_by_id[spec.anchor_id].footprint_polygon
        rooms.append(
            LabeledRoom(
                id=spec.id,
                polygon=poly,
                role="vertical_circulation",
                usage=spec.usage,
                area_m2=poly.area,
                anchor_id=spec.anchor_id,
            )
        )
    return rooms


def label_floor(
    corridored: CorridoredLayout,
    regions: Iterable[Region],
    specs: Iterable[SpaceUnitSpec],
    *,
    level: int,
    anchors: Iterable[VerticalAnchor] = (),
) -> LabeledFloorLayout:
    """Assemble one floor's `LabeledFloorLayout` — grown rooms + fixed vc rooms.

    Each grown room is polygonized (§4.2) and labeled (role/usage recovered via
    ``GrownRoom.name == SpaceUnitSpec.id``); ``vertical_circulation`` specs are
    re-inserted as fixed anchor rooms (§4.4, ``vc_rooms``); corridor regions
    become ``corridor_polygons``. Raises ``KeyError`` if a grown room has no
    matching spec, or a vc spec's ``anchor_id`` has no anchor (both are
    ``program_adapter`` / validator invariants — should never happen).
    """
    specs = list(specs)
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
    rooms.extend(vc_rooms(specs, anchors))
    corridor_polygons = polygonize_corridors(corridored.corridor_region_ids, region_poly)
    return LabeledFloorLayout(level=level, rooms=rooms, corridor_polygons=corridor_polygons)
