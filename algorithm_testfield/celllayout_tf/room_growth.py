"""Seeded room growth — Phase 7 algorithm sandbox.

External fixture (``LayoutFixture``) declares K rooms with seed positions
and per-role aspect / min-area tables. The algorithm consumes the
fixture and grows each room from its seed into a contiguous set of
regions, honoring the aspect range and weak hub-connectivity as hard
gates (D005 spirit), and the per-role min_area as a target.

The first ``RoomSpec`` with ``role == "public"`` is the hub. If no
``public`` room exists (K=2 cases), hub invariant is disabled.

Out of scope (deferred): atom-level corridor carving, hub selection,
seed positioning, door-capability validation, repair.

See ``README.md`` § Phase 7 for the full spec; see ``PHASE7_Fixtures.md``
for fixture data conventions.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal

import shapely.geometry as sg
from shapely.ops import unary_union

from .atomize import atomize
from .dimensions import DimensionPolicy
from .region_graph import build_region_graph
from .regionize import regionize
from .schema import ShapeInput, ShapePart
from .seed_placement import auto_place_seeds
from .shape_gate import make_shape_gate
from .territory import resolve_territories


Role = Literal["public", "private", "service", "wet"]

ROLE_VALUES: frozenset[str] = frozenset(("public", "private", "service", "wet"))


@dataclass(frozen=True)
class RoomSpec:
    """One room's input declaration in a fixture.

    ``seed_position``: ``(x, y)`` for manual placement, or ``None`` to let
    the algorithm auto-place via ``auto_place_seeds``. A fixture's rooms
    must be all-None or all-tuples — mixed mode is rejected by
    ``LayoutFixture``.

    ``target_aspect_range``: ``None`` → fall back to fixture's per-role
    default; ``(a_min, a_max)`` → explicit range. Algorithm uses this as
    a hard gate when deciding which region to absorb next.
    """
    name: str
    role: Role
    seed_position: tuple[float, float] | None
    target_aspect_range: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("RoomSpec.name must be non-empty")
        if self.role not in ROLE_VALUES:
            raise ValueError(
                f"RoomSpec.role must be one of {sorted(ROLE_VALUES)}, "
                f"got {self.role!r}"
            )
        if self.seed_position is not None and len(self.seed_position) != 2:
            raise ValueError(
                f"RoomSpec.seed_position must be (x, y) or None, "
                f"got {self.seed_position!r}"
            )
        if self.target_aspect_range is not None:
            a_min, a_max = self.target_aspect_range
            if not (1.0 <= a_min <= a_max):
                raise ValueError(
                    f"RoomSpec.target_aspect_range must satisfy "
                    f"1.0 <= min <= max, got {self.target_aspect_range!r}"
                )


@dataclass(frozen=True)
class LayoutFixture:
    """One case's external input. K = len(rooms).

    No central ``target_area`` or ``max_area`` — growth dynamics +
    role-based constraints determine the final distribution. The
    algorithm halts when every room is saturated (no in-gate
    candidate left).
    """
    case_index: int
    case_name: str
    footprint_area_m2: float
    rooms: tuple[RoomSpec, ...]
    role_min_areas: dict[str, float]
    role_aspect_ranges: dict[str, tuple[float, float]]
    max_l_rooms: int = 2

    def __post_init__(self) -> None:
        if not self.rooms:
            raise ValueError(f"LayoutFixture case {self.case_index}: no rooms")
        if self.footprint_area_m2 <= 0:
            raise ValueError(
                f"LayoutFixture case {self.case_index}: "
                f"footprint_area_m2 must be > 0"
            )
        if self.max_l_rooms < 0:
            raise ValueError(
                f"LayoutFixture case {self.case_index}: "
                f"max_l_rooms must be >= 0, got {self.max_l_rooms}"
            )

        # role coverage: every role used by a RoomSpec must have entries
        # in both tables.
        roles_used = {r.role for r in self.rooms}
        missing_min = roles_used - set(self.role_min_areas.keys())
        missing_aspect = roles_used - set(self.role_aspect_ranges.keys())
        if missing_min:
            raise ValueError(
                f"LayoutFixture case {self.case_index}: "
                f"role_min_areas missing entries for "
                f"{sorted(missing_min)}"
            )
        if missing_aspect:
            raise ValueError(
                f"LayoutFixture case {self.case_index}: "
                f"role_aspect_ranges missing entries for "
                f"{sorted(missing_aspect)}"
            )

        for role, val in self.role_min_areas.items():
            if role not in ROLE_VALUES:
                raise ValueError(
                    f"LayoutFixture case {self.case_index}: "
                    f"unknown role {role!r} in role_min_areas"
                )
            if val < 0:
                raise ValueError(
                    f"LayoutFixture case {self.case_index}: "
                    f"role_min_areas[{role!r}] = {val} must be >= 0"
                )

        for role, rng in self.role_aspect_ranges.items():
            if role not in ROLE_VALUES:
                raise ValueError(
                    f"LayoutFixture case {self.case_index}: "
                    f"unknown role {role!r} in role_aspect_ranges"
                )
            a_min, a_max = rng
            if not (1.0 <= a_min <= a_max):
                raise ValueError(
                    f"LayoutFixture case {self.case_index}: "
                    f"role_aspect_ranges[{role!r}] = {rng} must satisfy "
                    f"1.0 <= min <= max"
                )

        # seed_position consistency: all-None (auto-placement) or all-tuple
        # (manual placement). Mixed mode rejected to avoid ambiguity over
        # which seeds the algorithm should treat as fixed anchors.
        seed_states = {r.seed_position is None for r in self.rooms}
        if len(seed_states) > 1:
            raise ValueError(
                f"LayoutFixture case {self.case_index}: "
                f"seed_position must be all-None (auto placement) or "
                f"all-tuple (manual placement) — mixed mode is not allowed."
            )

    @property
    def K(self) -> int:
        return len(self.rooms)

    @property
    def auto_seed(self) -> bool:
        """True iff every room has ``seed_position=None`` (auto-placement)."""
        return all(r.seed_position is None for r in self.rooms)

    @property
    def hub_room_index(self) -> int | None:
        """Index of the first ``public``-role room, or ``None`` if absent.

        K=2 원룸 cases have no ``public`` room → hub invariant disabled.
        """
        for idx, room in enumerate(self.rooms):
            if room.role == "public":
                return idx
        return None

    def resolved_aspect_range(
        self, room: RoomSpec,
    ) -> tuple[float, float] | None:
        """Per-room aspect range after applying role default fallback."""
        if room.target_aspect_range is not None:
            return room.target_aspect_range
        return self.role_aspect_ranges.get(room.role)

    def resolved_min_area(self, room: RoomSpec) -> float:
        """Per-room min area resolved from ``role_min_areas``."""
        return self.role_min_areas[room.role]


@dataclass(frozen=True)
class GrownRoom:
    """One room's growth result: which regions were assigned, and area."""
    name: str
    role: Role
    region_ids: tuple[int, ...]
    area_m2: float


@dataclass(frozen=True)
class GrowthResult:
    """Final state after growth: per-room assignments + diagnostics.

    ``unassigned_region_ids`` lists regions that no room absorbed (either
    because every room's aspect/hub gate rejected them, or because growth
    terminated with the rest unreachable). These are candidates for the
    later atom-level corridor / access phase.
    """
    fixture: LayoutFixture
    rooms: tuple[GrownRoom, ...]
    unassigned_region_ids: tuple[int, ...]
    diagnostics: dict = field(default_factory=dict)


def region_unit_greedy(
    shape: ShapeInput,
    fixture: LayoutFixture,
    *,
    policy: DimensionPolicy | None = None,
) -> GrowthResult:
    """Region-unit greedy seeded growth — Phase 7 first algorithm.

    See README § Phase 7 for the full spec. Summary:

      - seed each room: manual fixture ``seed_position`` or, if all rooms
        have ``seed_position=None``, ``auto_place_seeds`` (hub + territory
        coverage + FPS).
      - rank rooms by min-area shortfall (descending), else by smallest
        current area (ascending)
      - absorb one in-gate neighbor per iteration:
          shape gate (cross-theta + curved exempt + reflex + L budget) +
          aspect gate (hard, role-based range) +
          weak hub-connectivity gate (no room loses its hub path)
      - stop when no room can grow without violating a gate.

    Unassigned regions are returned in ``GrowthResult.unassigned_region_ids``
    — they are the candidates for the later atom-level corridor / access
    phase.
    """
    atoms = atomize(shape, policy)
    regions = regionize(shape, atoms=atoms, policy=policy)
    rg = build_region_graph(shape, atoms=atoms, regions=regions, policy=policy)
    territories = resolve_territories(shape)

    region_poly_by_id: dict[int, sg.Polygon] = {
        r.region_id: _to_shapely(r.shape) for r in regions
    }
    region_area_by_id: dict[int, float] = {
        rid: poly.area for rid, poly in region_poly_by_id.items()
    }
    regions_by_id = {r.region_id: r for r in regions}

    neighbors_map: dict[int, set[int]] = defaultdict(set)
    edge_shared: dict[tuple[int, int], float] = {}
    for e in rg.edges:
        neighbors_map[e.region_a].add(e.region_b)
        neighbors_map[e.region_b].add(e.region_a)
        key = (min(e.region_a, e.region_b), max(e.region_a, e.region_b))
        edge_shared[key] = e.shared_boundary_length

    num_rooms = len(fixture.rooms)
    room_regions: dict[int, list[int]] = {i: [] for i in range(num_rooms)}
    region_to_room: dict[int, int] = {}

    shape_gate = make_shape_gate(territories, fixture.max_l_rooms)

    if fixture.auto_seed:
        has_public = fixture.hub_room_index is not None
        placements = auto_place_seeds(
            rg, territories, K=fixture.K, has_public=has_public,
        )
        # Distribute placements: hub (index 0 in placements when has_public)
        # → fixture.hub_room_index. Remaining placements fill remaining rooms
        # in listed order. K=2 (no public) just zips placements with rooms.
        if has_public:
            hub_room_idx = fixture.hub_room_index
            seed_for_room: dict[int, int] = {
                hub_room_idx: placements[0].region.region_id,
            }
            si = 1
            for room_idx in range(num_rooms):
                if room_idx == hub_room_idx:
                    continue
                seed_for_room[room_idx] = placements[si].region.region_id
                si += 1
        else:
            seed_for_room = {
                room_idx: placements[room_idx].region.region_id
                for room_idx in range(num_rooms)
            }
        for room_idx, region_id in seed_for_room.items():
            room_regions[room_idx].append(region_id)
            region_to_room[region_id] = room_idx
    else:
        for room_idx, spec in enumerate(fixture.rooms):
            pt = sg.Point(*spec.seed_position)
            # ``covers`` (not ``contains``) so seeds sitting exactly on a
            # region boundary still resolve to the first region in iteration
            # order. Deterministic tie-break by region_id ascending.
            found = None
            for r in sorted(regions, key=lambda r: r.region_id):
                if region_poly_by_id[r.region_id].covers(pt):
                    found = r.region_id
                    break
            if found is None:
                raise ValueError(
                    f"case {fixture.case_index} ({fixture.case_name}): "
                    f"seed {spec.name} at {spec.seed_position} does not fall "
                    f"inside any region (footprint hole or far outside?)"
                )
            if found in region_to_room:
                other = fixture.rooms[region_to_room[found]].name
                raise ValueError(
                    f"case {fixture.case_index} ({fixture.case_name}): "
                    f"seed {spec.name} at {spec.seed_position} resolves to "
                    f"region {found} already claimed by {other}"
                )
            region_to_room[found] = room_idx
            room_regions[room_idx].append(found)

    hub_idx = fixture.hub_room_index
    aspect_ranges = [fixture.resolved_aspect_range(r) for r in fixture.rooms]
    min_areas = [fixture.resolved_min_area(r) for r in fixture.rooms]
    current_areas = [
        region_area_by_id[room_regions[i][0]] for i in range(num_rooms)
    ]

    saturated = [False] * num_rooms
    iterations: list[dict] = []

    while True:
        active = [i for i in range(num_rooms) if not saturated[i]]
        if not active:
            break

        unmet = [i for i in active if current_areas[i] < min_areas[i]]
        if unmet:
            ranked = sorted(
                unmet,
                key=lambda i: -(min_areas[i] - current_areas[i]),
            )
        else:
            ranked = sorted(active, key=lambda i: current_areas[i])

        if hub_idx is not None:
            before_hub_set = _rooms_connected_to_hub(
                room_regions, hub_idx, region_to_room, neighbors_map,
            )
        else:
            before_hub_set = None

        picked = False
        for room_idx in ranked:
            cands: set[int] = set()
            for region_id in room_regions[room_idx]:
                for nbr in neighbors_map.get(region_id, ()):
                    if nbr not in region_to_room:
                        cands.add(nbr)
            if not cands:
                saturated[room_idx] = True
                continue

            a_range = aspect_ranges[room_idx]
            # Pre-cache rooms_state_before for shape gate (immutable in this
            # candidate loop — only one absorption commits per while iter).
            rooms_state_before: dict[int, tuple[int, ...]] = {
                i: tuple(rs) for i, rs in room_regions.items()
            }
            in_gate: list[int] = []
            for cand_id in cands:
                # shape gate (cross-theta + curved exempt + reflex + L budget)
                room_after = rooms_state_before[room_idx] + (cand_id,)
                if not shape_gate(
                    room_idx,
                    room_after,
                    rooms_state_before,
                    regions_by_id,
                ):
                    continue
                # aspect gate
                if a_range is not None:
                    a_min, a_max = a_range
                    union_poly = unary_union(
                        [region_poly_by_id[rid]
                         for rid in room_regions[room_idx]]
                        + [region_poly_by_id[cand_id]]
                    )
                    if not (a_min <= _bbox_aspect(union_poly) <= a_max):
                        continue
                # hub gate (only when hub exists)
                if hub_idx is not None:
                    sim_region_to_room = dict(region_to_room)
                    sim_region_to_room[cand_id] = room_idx
                    sim_room_regions = {
                        i: list(rs) for i, rs in room_regions.items()
                    }
                    sim_room_regions[room_idx].append(cand_id)
                    after_hub_set = _rooms_connected_to_hub(
                        sim_room_regions, hub_idx,
                        sim_region_to_room, neighbors_map,
                    )
                    if not before_hub_set.issubset(after_hub_set):
                        continue
                in_gate.append(cand_id)

            if not in_gate:
                saturated[room_idx] = True
                continue

            def shared_with_room(cand_id: int, _room=room_idx) -> float:
                total = 0.0
                for rid in room_regions[_room]:
                    key = (min(rid, cand_id), max(rid, cand_id))
                    total += edge_shared.get(key, 0.0)
                return total

            best = max(in_gate, key=shared_with_room)
            room_regions[room_idx].append(best)
            region_to_room[best] = room_idx
            current_areas[room_idx] += region_area_by_id[best]
            iterations.append({
                "room_idx": room_idx,
                "absorbed_region_id": best,
                "new_area_m2": current_areas[room_idx],
            })
            picked = True
            break

        if not picked:
            break

    grown_rooms = tuple(
        GrownRoom(
            name=spec.name,
            role=spec.role,
            region_ids=tuple(room_regions[i]),
            area_m2=current_areas[i],
        )
        for i, spec in enumerate(fixture.rooms)
    )
    unassigned = tuple(sorted(
        rid for rid in region_poly_by_id if rid not in region_to_room
    ))
    diagnostics = {
        "iterations": iterations,
        "hub_room_index": hub_idx,
        "total_iterations": len(iterations),
        "below_min_area": tuple(
            i for i in range(num_rooms) if current_areas[i] < min_areas[i]
        ),
    }
    return GrowthResult(
        fixture=fixture,
        rooms=grown_rooms,
        unassigned_region_ids=unassigned,
        diagnostics=diagnostics,
    )


def _to_shapely(part: ShapePart) -> sg.Polygon:
    return sg.Polygon(part.exterior, [list(h) for h in part.holes])


def _bbox_aspect(geom) -> float:
    """Aspect ratio of the axis-aligned bbox: max_side / min_side, ≥ 1."""
    xmin, ymin, xmax, ymax = geom.bounds
    w = xmax - xmin
    h = ymax - ymin
    if w <= 0 or h <= 0:
        return float("inf")
    return max(w, h) / min(w, h)


def _rooms_connected_to_hub(
    room_regions: dict[int, list[int]],
    hub_idx: int,
    region_to_room: dict[int, int],
    neighbors_map: dict[int, set[int]],
) -> set[int]:
    """Room indices path-connected to ``hub_idx`` in the room-supernode graph.

    Two rooms are adjacent iff one region from each room is adjacent in
    ``neighbors_map``. BFS from the hub supernode returns the reachable
    set (always includes ``hub_idx`` itself).
    """
    room_adj: dict[int, set[int]] = defaultdict(set)
    for region_id, r_idx in region_to_room.items():
        for nbr in neighbors_map.get(region_id, ()):
            other = region_to_room.get(nbr)
            if other is not None and other != r_idx:
                room_adj[r_idx].add(other)
                room_adj[other].add(r_idx)

    visited = {hub_idx}
    queue = [hub_idx]
    while queue:
        nxt: list[int] = []
        for cur in queue:
            for nbr in room_adj[cur]:
                if nbr not in visited:
                    visited.add(nbr)
                    nxt.append(nbr)
        queue = nxt
    return visited
