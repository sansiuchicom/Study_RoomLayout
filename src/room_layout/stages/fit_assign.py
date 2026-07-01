"""fit-assign — grow-then-label 라벨 (PlanBIM 145 §11 Phase B).

corridor 후 방에 *최종 usage* 배정 (label-first 의 seed-id 복원 대체). 핵심:
  - hub(평면 앵커) → living.
  - 나머지 = 프로그램 demand(specs)를 **access 제약 안에서 크기-fit** 으로
    *제약-우선 greedy* 배정 (wet/service = 순환 닿는 방 중 크기 맞는 것 먼저).
  - access 없는 작은 방 = *침실 옆이면 ensuite 욕실* / 아니면 storage.
  - 잔여(split 조각) = bedroom(큼) / storage(작음).

role 은 *힌트가 아니라 demand 분류*(access 필요 여부)에만 — 최종 usage 는 geometry
가 결정 (grow-then-label). 수직 배관스택은 cross-floor 라 D축 별도 (145 §11).
"""

from __future__ import annotations

from shapely.geometry import Polygon

from room_layout.stages.room_split import _adjacency

# spec.area_target 없을 때 role 대표 target 크기(㎡)
_DEFAULT_TARGET: dict[str, float] = {
    "wet": 4.5,
    "service": 9.5,
    "private": 11.0,
    "public": 16.0,
}
_ACCESS_ROLES = frozenset({"wet", "service"})  # 순환 접근 필요
_ENSUITE_MAX = 12.0  # access 없는 방이 이보다 작으면 ensuite/storage 후보
_BEDROOM_MIN = 9.0  # 잔여가 이 이상이면 bedroom (미만 storage)


def fit_assign(
    rooms,
    region_poly: dict[int, Polygon],
    circ_region_ids,
    specs,
    *,
    hub_idx: int | None,
) -> dict[int, str]:
    """``rooms[i] → usage`` 배정 (rooms = post-corridor GrownRoom 리스트)."""
    adj = _adjacency(list(region_poly), region_poly)
    circ = set(circ_region_ids)
    if hub_idx is not None and rooms[hub_idx].region_ids:
        circ |= set(rooms[hub_idx].region_ids)
    live = [i for i in range(len(rooms)) if rooms[i].region_ids]
    access = {i: any(adj.get(r, set()) & circ for r in rooms[i].region_ids) for i in live}

    assigned: dict[int, str] = {}
    used: set[int] = set()

    # hub → living (앵커)
    non_special = [s for s in specs if s.role not in ("corridor", "vertical_circulation")]
    hub_spec = next((s for s in non_special if s.role == "public"), None)
    if hub_idx is not None and hub_idx in live:
        assigned[hub_idx] = hub_spec.usage if (hub_spec and hub_spec.usage) else "living"
        used.add(hub_idx)

    # demand = 나머지 specs, 제약 빡센 順 (access 필요 + 작은 target 먼저)
    def _target(s) -> float:
        return s.area_target_m2 or s.area_min_m2 or _DEFAULT_TARGET.get(s.role, 10.0)

    demand = sorted(
        (s for s in non_special if s is not hub_spec),
        key=lambda s: (0 if s.role in _ACCESS_ROLES else 1, _target(s)),
    )
    for s in demand:
        need = s.role in _ACCESS_ROLES
        cands = [i for i in live if i not in used and (access[i] or not need)]
        if not cands:  # access 못 맞추면 relax (그냥 남은 것)
            cands = [i for i in live if i not in used]
        if not cands:
            break
        tgt = _target(s)
        best = min(cands, key=lambda i: abs(rooms[i].area_m2 - tgt))
        assigned[best] = s.usage or s.role
        used.add(best)

    # 잔여 (split 조각 등): ensuite / storage / bedroom
    room_of = {r: k for k in live for r in rooms[k].region_ids}
    for i in live:
        if i in used:
            continue
        if not access[i] and rooms[i].area_m2 <= _ENSUITE_MAX:
            nbrs = {
                room_of[n] for r in rooms[i].region_ids for n in adj.get(r, set()) if n in room_of
            }
            ensuite = any(rooms[k].role == "private" for k in nbrs)  # 침실 옆 → ensuite
            assigned[i] = "bathroom" if ensuite else "storage"
        elif rooms[i].area_m2 >= _BEDROOM_MIN:
            assigned[i] = "bedroom"
        else:
            assigned[i] = "storage"
    return assigned
