"""Phase 8: Corridor Carving — base corridor + detour shortcut + cleanup.

See ``PHASE8_Corridor.md`` for the full spec. The implementation routes a
hub-radial base corridor, adds detour shortcuts for high-ratio room pairs,
then absorbs leftover regions into corridor or adjacent rooms.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.ops import unary_union

from .corridor_index import (
    _build_region_index,
    _room_is_connected,
)
from .corridor_stage1 import (
    _astar_base_corridor,
    _stage1_base_corridor,
)
from .corridor_stage2 import (
    _astar_shortcut,
    _bfs_hop_collapse_hub,
    _corridor_distance_hop,
    _find_entrances,
    _map_distance_hop,
    _stage2_detour_shortcut,
)
from .dimensions import DimensionPolicy
from .room_growth import GrownRoom, GrowthResult, LayoutFixture
from .schema import ShapeInput


# ---------- Output type ------------------------------------------------


@dataclass(frozen=True)
class CorridoredLayout:
    """Output of Phase 8.

    ``rooms`` is the post-carve copy of ``GrowthResult.rooms`` — region_ids
    are reduced for any room whose region was carved into corridor.

    ``base_corridor_region_ids`` come from Stage 1 (hub-radial), ``shortcut``
    from Stage 2 (detour). ``leftover_region_ids`` are unassigned regions
    that even cleanup could not absorb (usually empty).
    """
    fixture: LayoutFixture
    rooms: tuple[GrownRoom, ...]
    base_corridor_region_ids: tuple[int, ...]
    shortcut_corridor_region_ids: tuple[int, ...]
    leftover_region_ids: tuple[int, ...]
    diagnostics: dict = field(default_factory=dict)

    @property
    def corridor_region_ids(self) -> tuple[int, ...]:
        """All corridor regions — base + shortcut."""
        return self.base_corridor_region_ids + self.shortcut_corridor_region_ids


# ---------- Cleanup ----------------------------------------------------


def _obb_aspect(geom) -> float:
    """Aspect ratio (long-side / short-side) of the geometry's
    minimum-area rotated rectangle. Works for rotated rooms where
    axis-aligned bbox would over-estimate aspect.
    """
    obb = geom.minimum_rotated_rectangle
    coords = list(obb.exterior.coords)[:4]
    side_lens = []
    for i in range(4):
        ax, ay = coords[i]
        bx, by = coords[(i + 1) % 4]
        side_lens.append(math.hypot(bx - ax, by - ay))
    long_side = max(side_lens)
    short_side = min(side_lens)
    return long_side / max(short_side, 1e-9)


def _cleanup_leftover(
    *,
    fixture: LayoutFixture,
    room_meta: tuple[GrownRoom, ...],
    room_region_ids: dict[int, set[int]],
    base_corridor: set[int],
    shortcut_corridor: set[int],
    leftover: set[int],
    hub_regions: set[int],
    region_poly: dict,
    region_area: dict[int, float],
    region_adj: dict[int, set[int]],
) -> dict:
    """PHASE8_Corridor.md §5 cleanup. Mutates ``room_region_ids``,
    ``base_corridor``, and ``leftover`` in place.

    Priority 1 (iterative): any leftover 4-adjacent to corridor/hub →
    absorb into base_corridor. Newly absorbed regions extend the target
    set, so a cluster of adjacent leftovers all bordering corridor gets
    swallowed in a few sweeps.

    Priority 2 (single pass): any remaining leftover 4-adjacent to some
    room → absorb into the room whose OBB aspect after absorption is
    closest to 1.0 (most-square). Tie-break: smaller room area first.
    Hard gate: skip a candidate if absorbing would push aspect above
    ``fixture.role_aspect_ranges[role].max`` (§6.3). If every candidate
    is gated, leftover stays for Priority 3.

    Priority 3: silent — region remains in ``leftover`` (★ extra space).
    """
    log: dict = {
        "priority1_absorbed": [],
        "priority2_absorbed": [],
        "priority3_kept": [],
    }

    # ----- Priority 1 -----
    target_set: set[int] = base_corridor | shortcut_corridor | hub_regions
    changed = True
    while changed:
        changed = False
        for rid in sorted(leftover):
            if any(nbr in target_set for nbr in region_adj[rid]):
                leftover.discard(rid)
                base_corridor.add(rid)
                target_set.add(rid)
                log["priority1_absorbed"].append(rid)
                changed = True

    # ----- Priority 2 -----
    for rid in sorted(leftover):
        candidate_rooms: set[int] = set()
        for nbr in region_adj[rid]:
            for room_idx, regs in room_region_ids.items():
                if nbr in regs:
                    candidate_rooms.add(room_idx)
                    break
        if not candidate_rooms:
            continue

        best_key: tuple[float, float, int] | None = None
        best_room: int | None = None
        rid_poly = region_poly[rid]
        for room_idx in candidate_rooms:
            room_regs = room_region_ids[room_idx]
            if not room_regs:
                continue
            polys = [region_poly[r] for r in room_regs] + [rid_poly]
            union = unary_union(polys)
            aspect = _obb_aspect(union)
            role = room_meta[room_idx].role
            max_aspect = fixture.role_aspect_ranges[role][1]
            if aspect > max_aspect:
                continue
            room_area_pre = sum(region_area[r] for r in room_regs)
            key = (abs(aspect - 1.0), room_area_pre, room_idx)
            if best_key is None or key < best_key:
                best_key = key
                best_room = room_idx

        if best_room is None:
            continue

        leftover.discard(rid)
        room_region_ids[best_room].add(rid)
        log["priority2_absorbed"].append((rid, best_room))

    # ----- Priority 3 -----
    log["priority3_kept"] = sorted(leftover)
    return log


# ---------- Public entry -----------------------------------------------


def carve_corridors(
    shape: ShapeInput,
    growth_result: GrowthResult,
    *,
    policy: DimensionPolicy | None = None,
) -> CorridoredLayout:
    """Phase 8 entry — see ``PHASE8_Corridor.md``."""
    (
        _regions, region_poly, region_area, region_adj, on_footprint_edge,
    ) = _build_region_index(shape, policy)

    room_region_ids, base_corridor, leftover, stage1_diag = _stage1_base_corridor(
        growth_result, region_area, region_adj, on_footprint_edge,
    )

    shortcut_corridor, stage2_diag = _stage2_detour_shortcut(
        room_region_ids=room_region_ids,
        base_corridor=base_corridor,
        unassigned_set=leftover,
        hub_idx=growth_result.fixture.hub_room_index,
        region_area=region_area,
        region_adj=region_adj,
        on_footprint_edge=on_footprint_edge,
        threshold=growth_result.fixture.detour_threshold,
    )

    hub_idx = growth_result.fixture.hub_room_index
    hub_regions_set = (
        room_region_ids.get(hub_idx, set()) if hub_idx is not None else set()
    )
    cleanup_diag = _cleanup_leftover(
        fixture=growth_result.fixture,
        room_meta=growth_result.rooms,
        room_region_ids=room_region_ids,
        base_corridor=base_corridor,
        shortcut_corridor=shortcut_corridor,
        leftover=leftover,
        hub_regions=hub_regions_set,
        region_poly=region_poly,
        region_area=region_area,
        region_adj=region_adj,
    )

    disconnected: list[int] = []
    emptied: list[int] = []
    for room_idx, regions_set in room_region_ids.items():
        if not regions_set:
            if growth_result.rooms[room_idx].region_ids:
                emptied.append(room_idx)
            continue
        if not _room_is_connected(regions_set, region_adj):
            disconnected.append(room_idx)

    new_rooms = tuple(
        GrownRoom(
            name=old.name,
            role=old.role,
            region_ids=tuple(sorted(room_region_ids[i])),
            area_m2=sum(region_area[r] for r in room_region_ids[i]),
        )
        for i, old in enumerate(growth_result.rooms)
    )

    diagnostics = {
        "phase": "w4-stage1+stage2+cleanup",
        "stage1": stage1_diag,
        "stage2": stage2_diag,
        "cleanup": cleanup_diag,
        "base_corridor_count": len(base_corridor),
        "shortcut_corridor_count": len(shortcut_corridor),
        "disconnected_rooms": tuple(disconnected),
        "emptied_rooms": tuple(emptied),
    }

    return CorridoredLayout(
        fixture=growth_result.fixture,
        rooms=new_rooms,
        base_corridor_region_ids=tuple(sorted(base_corridor)),
        shortcut_corridor_region_ids=tuple(sorted(shortcut_corridor)),
        leftover_region_ids=tuple(sorted(leftover)),
        diagnostics=diagnostics,
    )
