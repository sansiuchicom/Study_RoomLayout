"""Polygonization — `CorridoredLayout` region-id sets → room / corridor polygons.

Plan reference: ``007_Step07_EntryPoint_Plan.md`` §4.2 + S04-D2 + S07-D5.

Step 04 stopped at a region-based ``CorridoredLayout`` (S04-D2): each
``GrownRoom`` carries ``region_ids`` (a set of region ids), **not** a polygon.
The viz path unions those regions on the fly only to draw, then discards the
result; nothing in the pipeline ever persists a room polygon. This module does
the deferred polygonization — the bridge from the internal region-graph
representation to the external geometric contract (Pipeline §2.4: shapely
``Polygon``, CCW, meters):

- A room's regions are unioned into **one** ``Polygon``. A disconnected union
  is a should-never-happen invariant violation (0/137 rooms across the 33
  goldens — growth only absorbs *adjacent* regions), so it raises
  ``GeometryFailure`` rather than silently taking the largest piece (S07-D5,
  honest-fix). ``run()`` catches it → ``valid=False`` (proto3:D018).
- A corridor region set may legitimately be multi-component (4/33 goldens — a
  Stage-2 detour shortcut attaches through a room entrance, leaving the carved
  set in ≥2 pieces), so it maps to a ``list[Polygon]``
  (``LabeledFloorLayout.corridor_polygons`` is plural).

Area is conserved: regions partition the floor and share edges, so
``unary_union`` dissolves the internal seams without gaining or losing area
(the area-conservation test).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from room_layout.schema.failure import FailureRecord, GeometryFailure
from room_layout.stages._helpers import polygon_parts, to_shapely
from room_layout.stages.regionize import Region


def build_region_polygons(regions: Iterable[Region]) -> dict[int, Polygon]:
    """Map each ``region_id`` to its shapely ``Polygon`` (world frame).

    Mirrors ``corridor_index._build_region_index``'s ``region_poly`` so the
    polygons here are identical to the ones growth / carving reasoned over.
    """
    return {r.region_id: to_shapely(r.shape) for r in regions}


def polygonize_room(
    region_ids: Sequence[int],
    region_poly: Mapping[int, Polygon],
    *,
    room_name: str,
) -> Polygon:
    """Union a room's regions into one CCW ``Polygon``.

    Raises ``GeometryFailure`` if the room has no regions (``ROOM_EMPTY``) or
    its region union is not a single polygon (``ROOM_DISCONNECTED``) — an
    invariant violation, not an expected outcome (S07-D5). The caller
    (``run()``) converts the carried ``FailureRecord`` into ``valid=False``.
    """
    if not region_ids:
        raise GeometryFailure(
            FailureRecord(
                code="ROOM_EMPTY",
                stage="polygonize",
                message=f"room {room_name!r} has no regions to polygonize",
                data={"room": room_name},
            )
        )
    merged = unary_union([region_poly[rid] for rid in region_ids])
    parts = polygon_parts(merged)
    if len(parts) != 1:
        raise GeometryFailure(
            FailureRecord(
                code="ROOM_DISCONNECTED",
                stage="polygonize",
                message=(
                    f"room {room_name!r} region union is disconnected: "
                    f"{len(parts)} pieces (areas {[round(p.area, 3) for p in parts]})"
                ),
                data={"room": room_name, "piece_areas": [p.area for p in parts]},
            )
        )
    return orient(parts[0], sign=1.0)


def polygonize_corridors(
    region_ids: Sequence[int],
    region_poly: Mapping[int, Polygon],
) -> list[Polygon]:
    """Union a corridor region set into a list of CCW ``Polygon`` components.

    A multi-component corridor is legitimate (S07-D5), so this returns one
    polygon per connected component — zero (empty set), one, or several.
    """
    if not region_ids:
        return []
    merged = unary_union([region_poly[rid] for rid in region_ids])
    return [orient(p, sign=1.0) for p in polygon_parts(merged)]
