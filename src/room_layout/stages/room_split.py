"""Pre-corridor room split — 큰 방을 role별 상한 밑으로 잘게 (PlanBIM 145 §11).

growth 후·corridor 전 삽입. 비-hub 방 중 ``area > role-ceiling`` 을 **BFS 2-source
연결분할**로 재귀 2분할(상한 밑까지). corridor 가 새 방 access 를 떠맡고(PoC GO),
최종 usage 는 fit-assign 이 나중에(grow-then-label) — 본 단계는 *크기*만, label 무관.

growth/seed 무손상 (이 단계는 growth *결과* 변형). single-region·분리 조각은 스킵
(보수적; atom-split 보류). hub(public)=평면 앵커라 안 건드림.
"""

from __future__ import annotations

import dataclasses

from shapely.geometry import Polygon
from shapely.ops import unary_union

from room_layout.stages.polygonize import build_region_polygons
from room_layout.stages.regionize import Region
from room_layout.stages.room_growth import GrowthResult

# public/non-public 2-class max-cap(㎡) — *coarse*: 말도 안 되는 거대 방만 차단.
# fine role(wet/service)은 grow-then-label 이라 신뢰불가 → 안 씀 (public 여부만 신뢰).
# 크기 다양성·욕실 사이즈는 corridor·fit-assign 담당. type-agnostic; caller 가 덮음.
DEFAULT_CEILINGS: dict[str, float] = {
    "public": 50.0,  # 거실/가족실 앵커 — 오픈플랜, 높게
    "non_public": 25.0,  # 침실/욕실/주방 전부 — >25 면 absurd
}
_ADJ_MIN = 1e-6  # region 인접 판정 최소 공유 경계


def _adjacency(rids: list[int], region_poly: dict[int, Polygon]) -> dict[int, set[int]]:
    """방 내부 region 인접 그래프 (공유 경계 길이 > 0)."""
    adj: dict[int, set[int]] = {r: set() for r in rids}
    for i in range(len(rids)):
        for j in range(i + 1, len(rids)):
            a, b = rids[i], rids[j]
            inter = region_poly[a].boundary.intersection(region_poly[b].boundary)
            if not inter.is_empty and inter.length > _ADJ_MIN:
                adj[a].add(b)
                adj[b].add(a)
    return adj


def _bfs_two_source(
    rids: list[int], region_poly: dict[int, Polygon]
) -> tuple[list[int], list[int]]:
    """면적 ~반반 *둘 다 연결* 2그룹 — 양 끝 seed 2-source 성장 (PoC 검증).

    각 그룹이 seed 로부터 BFS 트리라 둘 다 연결 보장 (sweep orphan·단일seed B끊김
    둘 다 회피). 미청구 섬은 A 로.
    """
    adj = _adjacency(rids, region_poly)
    areas = {r: region_poly[r].area for r in rids}
    minx, miny, maxx, maxy = unary_union([region_poly[r] for r in rids]).bounds
    axis_x = (maxx - minx) >= (maxy - miny)

    def key(r: int) -> float:
        return region_poly[r].centroid.x if axis_x else region_poly[r].centroid.y

    rset = set(rids)
    ordered = sorted(rids, key=key)
    seed_a, seed_b = ordered[0], ordered[-1]
    grp_a, grp_b = {seed_a}, {seed_b}
    area_a, area_b = areas[seed_a], areas[seed_b]
    claimed = {seed_a, seed_b}
    while len(claimed) < len(rset):
        grow_a = area_a <= area_b  # 작은 쪽부터 → 균형
        grp = grp_a if grow_a else grp_b
        frontier = [n for r in grp for n in adj[r] if n not in claimed]
        if not frontier:  # 막히면 반대 그룹
            grow_a = not grow_a
            grp = grp_a if grow_a else grp_b
            frontier = [n for r in grp for n in adj[r] if n not in claimed]
            if not frontier:
                break
        nxt = (min if grow_a else max)(frontier, key=key)
        grp.add(nxt)
        claimed.add(nxt)
        if grow_a:
            area_a += areas[nxt]
        else:
            area_b += areas[nxt]
    grp_a |= rset - claimed  # 미청구(분리 섬) fallback
    return sorted(grp_a), sorted(grp_b)


def split_oversized(
    growth: GrowthResult,
    regions: tuple[Region, ...],
    *,
    ceilings: dict[str, float] | None = None,
    hub_idx: int | None = None,
) -> GrowthResult:
    """비-hub 방 중 ``area > role-ceiling`` → 재귀 2분할한 새 ``GrowthResult``.

    제자리 교체 + append 라 기존 인덱스(hub 포함) 안정. 상한 밑·single-region·
    분리불가면 그대로 둠. usage(role)는 안 건드림 (fit-assign 담당).
    """
    caps = {**DEFAULT_CEILINGS, **(ceilings or {})}
    if hub_idx is None:
        hub_idx = growth.fixture.hub_room_index
    region_poly = build_region_polygons(regions)
    rooms = list(growth.rooms)

    work = [i for i in range(len(rooms)) if i != hub_idx]
    while work:
        i = work.pop()
        room = rooms[i]
        cap = caps["public"] if room.role == "public" else caps["non_public"]
        if room.area_m2 <= cap:
            continue
        rids = [r for r in room.region_ids if r in region_poly]
        if len(rids) < 2:
            continue  # 단일 region — 재그룹 불가 (atom-split 보류)
        grp_a, grp_b = _bfs_two_source(rids, region_poly)
        if not grp_a or not grp_b:
            continue
        poly_a = unary_union([region_poly[r] for r in grp_a])
        poly_b = unary_union([region_poly[r] for r in grp_b])
        if not (isinstance(poly_a, Polygon) and isinstance(poly_b, Polygon)):
            continue  # 분리 조각 — 스킵 (2-source 라 드묾)
        rooms[i] = dataclasses.replace(room, region_ids=tuple(sorted(grp_a)), area_m2=poly_a.area)
        j = len(rooms)
        rooms.append(
            dataclasses.replace(
                room,
                name=f"{room.name}__s{j}",
                region_ids=tuple(sorted(grp_b)),
                area_m2=poly_b.area,
            )
        )
        work.extend((i, j))  # 두 조각 재검사 (상한 밑까지 재귀)
    return dataclasses.replace(growth, rooms=tuple(rooms))
