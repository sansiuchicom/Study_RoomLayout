"""Phase 8: Corridor Carving — base corridor + detour shortcut + cleanup (§4.13).

Plan reference: ``004_Step04_AlgorithmCore_Plan.md`` §4.13 + S04-D1 / S04-D2 / S04-D8.

Faithful port of Cell ``corridor.py`` — routes a hub-radial base corridor (Stage
1), adds detour shortcuts for high-ratio room pairs (Stage 2), then absorbs
leftover regions into corridor or adjacent rooms (cleanup). Emits
``CorridoredLayout`` — **Step 04's terminal output** (S04-D2): per-room region
sets (reduced where carved) + base / shortcut / leftover corridor region sets.
The polygonization + `LabeledRoomLayout` wrapping is Step 07.

**S04-D8**: ``carve_corridors`` takes the Step 03 ``regions`` + ``region_graph``
as parameters (passed to ``_build_region_index``) instead of recomputing;
``shape``→``floor`` (S03-D13); ``policy`` dropped. Algorithm unchanged.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.ops import unary_union

from room_layout.schema import FloorShape
from room_layout.stages.corridor_index import _build_region_index, _room_is_connected
from room_layout.stages.corridor_stage1 import _stage1_base_corridor
from room_layout.stages.corridor_stage2 import _stage2_detour_shortcut
from room_layout.stages.region_graph import RegionGraph
from room_layout.stages.regionize import Region
from room_layout.stages.room_growth import GrownRoom, GrowthResult, LayoutFixture

# ---------- Output type ------------------------------------------------


@dataclass(frozen=True)
class CorridoredLayout:
    """Output of Phase 8 — Step 04's terminal result (S04-D2).

    ``rooms`` is the post-carve copy of ``GrowthResult.rooms`` — region_ids are
    reduced for any room whose region was carved into corridor.

    ``base_corridor_region_ids`` come from Stage 1 (hub-radial), ``shortcut``
    from Stage 2 (detour). ``leftover_region_ids`` are unassigned regions that
    even cleanup could not absorb (usually empty).
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
    """Aspect ratio (long-side / short-side) of the geometry's minimum-area
    rotated rectangle. Works for rotated rooms where the axis-aligned bbox would
    over-estimate aspect.
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

    Priority 1 (iterative): any leftover 4-adjacent to corridor/hub → absorb into
    base_corridor. Newly absorbed regions extend the target set, so a cluster of
    adjacent leftovers all bordering corridor gets swallowed in a few sweeps.

    Priority 2 (single pass): any remaining leftover 4-adjacent to some room →
    absorb into the room whose OBB aspect after absorption is closest to 1.0
    (most-square). Tie-break: smaller room area first. Hard gate: skip a
    candidate if absorbing would push aspect above
    ``fixture.role_aspect_ranges[role].max`` (§6.3). If every candidate is gated,
    leftover stays for Priority 3.

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


def _route_extra_targets(
    extra_targets,
    *,
    room_region_ids: dict[int, set[int]],
    room_roles: dict[int, str],
    hub_regions: set[int],
    base_corridor: set[int],
    unassigned_set: set[int],
    region_poly,
    region_area: dict[int, float],
    region_adj: dict[int, set[int]],
    on_footprint_edge: dict[int, bool],
) -> list[dict]:
    """Route the base corridor to caller-specified polygons (CorridorTarget).

    For each target polygon: resolve the goal set = regions sharing a
    positive-length boundary with it, then Stage-1 style — already satisfied
    (a goal region is corridor / public-role) → skip; else damage-guarded A*
    from the hub. **The goal region is carved too** (unlike room targets) so
    the corridor physically touches the target polygon. Mutates
    ``room_region_ids`` / ``base_corridor`` / ``unassigned_set`` in place;
    returns a per-target log (diagnostics).
    """
    from room_layout.stages.corridor_path import (
        _minimize_offending,
        _path_damages_any_room,
    )
    from room_layout.stages.corridor_stage1 import (
        _CORRIDOR_MAX_RETRY,
        _astar_base_corridor,
    )

    log: list[dict] = []
    if not extra_targets:
        return log

    region_to_room: dict[int, int] = {}
    for room_idx, rids in room_region_ids.items():
        for rid in rids:
            region_to_room[rid] = room_idx

    for t_i, target in enumerate(extra_targets):
        goal_set = {
            rid
            for rid, poly in region_poly.items()
            if poly.boundary.intersection(target.boundary).length > 0.05
        }
        if not goal_set:
            log.append({"target": t_i, "result": "no-goal-regions"})
            continue
        satisfied = any(
            rid in base_corridor
            or rid in hub_regions
            or room_roles.get(region_to_room.get(rid, -1)) == "public"
            for rid in goal_set
        )
        if satisfied:
            log.append({"target": t_i, "result": "satisfied"})
            continue
        if not hub_regions:
            log.append({"target": t_i, "result": "no-hub"})
            continue

        forbidden: set[int] = set()
        path: list[int] | None = None
        attempts = 0
        for attempts in range(1, _CORRIDOR_MAX_RETRY + 1):
            candidate = _astar_base_corridor(
                start_set=hub_regions,
                goal_set=goal_set,
                room_region_ids=room_region_ids,
                base_corridor=base_corridor,
                unassigned_set=unassigned_set,
                region_area=region_area,
                region_adj=region_adj,
                on_footprint_edge=on_footprint_edge,
                forbidden=frozenset(forbidden),
            )
            if candidate is None:
                break
            # goal regions are NOT excluded — their owners must survive the
            # loss too (the goal region becomes corridor).
            damage = _path_damages_any_room(
                candidate,
                excluded=hub_regions,
                room_region_ids=room_region_ids,
                region_adj=region_adj,
            )
            if damage is None:
                path = candidate
                break
            offending, damaged_room = damage
            forbidden.update(
                _minimize_offending(offending, damaged_room, room_region_ids, region_adj)
            )
        if path is None:
            log.append({"target": t_i, "result": "astar-failed", "attempts": attempts})
            continue

        carved_now: list[int] = []
        for rid in path:
            if rid in hub_regions:
                continue
            for owner_set in room_region_ids.values():
                owner_set.discard(rid)
            unassigned_set.discard(rid)
            base_corridor.add(rid)
            carved_now.append(rid)
        log.append(
            {
                "target": t_i,
                "result": "ok",
                "attempts": attempts,
                "carved": carved_now,
            }
        )

    return log


def carve_corridors(
    floor: FloorShape,
    growth_result: GrowthResult,
    *,
    regions: tuple[Region, ...],
    region_graph: RegionGraph,
    extra_targets: tuple = (),
    carve: bool = True,
) -> CorridoredLayout:
    """Phase 8 entry — see ``PHASE8_Corridor.md``. Consumes Step 03 outputs
    (``regions`` + ``region_graph``) as the carve substrate (S04-D8).

    ``extra_targets``: shapely Polygons the circulation must additionally
    reach (CorridorTarget.polygon, already filtered to this floor) — routed
    after the room targets, before Stage 2 / cleanup.

    ``carve=False`` is a research ablation switch: skip circulation carving and
    return the grown rooms with no corridors (rooms tile the floor, connected by
    adjacency only). Do not use in production.
    """
    if not carve:
        return CorridoredLayout(
            fixture=growth_result.fixture,
            rooms=growth_result.rooms,
            base_corridor_region_ids=(),
            shortcut_corridor_region_ids=(),
            leftover_region_ids=(),
            diagnostics={"ablated": "no_carve"},
        )
    (
        _regions,
        region_poly,
        region_area,
        region_adj,
        on_footprint_edge,
    ) = _build_region_index(floor, regions, region_graph)

    room_region_ids, base_corridor, leftover, stage1_diag = _stage1_base_corridor(
        growth_result, region_area, region_adj, on_footprint_edge
    )

    extra_diag: list[dict] = []
    if extra_targets:
        hub_idx_pre = growth_result.fixture.hub_room_index
        extra_diag = _route_extra_targets(
            tuple(extra_targets),
            room_region_ids=room_region_ids,
            room_roles={i: r.role for i, r in enumerate(growth_result.rooms)},
            hub_regions=(
                set(room_region_ids.get(hub_idx_pre, set())) if hub_idx_pre is not None else set()
            ),
            base_corridor=base_corridor,
            unassigned_set=leftover,
            region_poly=region_poly,
            region_area=region_area,
            region_adj=region_adj,
            on_footprint_edge=on_footprint_edge,
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
    hub_regions_set = room_region_ids.get(hub_idx, set()) if hub_idx is not None else set()
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
        "extra_targets": extra_diag,
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
