# Phase 8: Corridor Carving

Room placement이 끝난 layout 위에서, hub(주거실)로부터 모든 방으로
닿는 복도를 깎아내는 단계. door 배치는 별도 phase로 미룸.

**Scope**: 입력 `GrowthResult` (Phase 7 종료 산출물) → 출력 `CorridoredLayout`.
방 모양은 carve로 변경될 수 있음. 변경된 방의 `region_ids`는 갱신됨.
새로 만들어진 corridor는 `corridor_region_ids`로 분리.

**Two stages**:

1. **Base corridor (hub-radial)** — hub에서 모든 방으로 spanning tree.
2. **Detour shortcut** — 두 방 간 corridor 우회 비율이 큰 페어에 직접
   carve로 cycle 형성.

이어서 **cleanup** — 남은 unassigned region을 corridor/방으로 흡수.

---

## 1. Granularity: Region-level

### 결정

Carve 입자는 **region** 단위.

- `Region` (regionize.py 결과) = atom들의 axis-aligned 묶음.
- Region 단변 = atom 단변(0.2~0.4m)의 정수배 → 보통 0.4~2.0m.
- 한 region carve = 그 region을 방의 `region_ids` tuple에서 빼고
  `corridor_region_ids`에 추가.

### Atom/cell 단위 대비 이점

| 항목 | Region 단위 | Atom 단위 |
|---|---|---|
| 복도 폭 (두께) | region 단변이 그대로 (0.4~2.0m, 자연스러운 복도) | 1 atom = 0.3m → 명시적 thickness 로직 필요 |
| 인접 그래프 | `region_graph.py` 그대로 사용 | atom_graph 위에서 별도 BFS/A* 자료구조 |
| 데이터 모델 | `GrownRoom.region_ids` tuple 갱신만 | 새 cell-level mask 도입 → 이중화 |
| Carve path 정밀도 | 거침 (region 한 칸이 carve의 최소 단위) | 세밀 |
| 두께 균일성 | 코너에서 region 두 개 짜집기 → 두께 불균일 가능 | 1 atom 일관 |

복도 폭과 인프라 재활용을 우선해 region을 택함.

### 알려진 trade-off

- **카브 입자 거침**: sandbox v6의 "3 cells carved" 같은 작은 detour가
  region 단위로는 1 region 카브 = 폭×길이 둘 다 region 크기.
- **코너 두께 불균일**: ㄱ자 corridor가 region 두 개일 때 끝마다
  단변이 다를 수 있음. 비주얼적으로 거슬리면 **atom-level refinement
  phase** 추가 검토 (deferred).

---

## 2. 입출력

### 입력

```text
GrowthResult (Phase 7)
  fixture: LayoutFixture
  rooms: tuple[GrownRoom, ...]          # 각 방의 region_ids
  unassigned_region_ids: tuple[int, ...]
  diagnostics: dict
```

추가 필요 자료:

- `regions: tuple[Region, ...]` (Phase 5 산출물 재구성)
- `region_graph: RegionGraph` (Phase 6 산출물 재구성)
  - region 인접 관계 (4-인접 기준)

### 출력 (proposed)

```python
@dataclass(frozen=True)
class CorridoredLayout:
    fixture: LayoutFixture
    rooms: tuple[GrownRoom, ...]                  # 갱신: region_ids에서 carve된 거 제외
    corridor_region_ids: tuple[int, ...]          # base + shortcut 합쳐서
    base_corridor_region_ids: tuple[int, ...]     # Stage 1 산출
    shortcut_corridor_region_ids: tuple[int, ...] # Stage 2 산출
    leftover_region_ids: tuple[int, ...]          # cleanup 후에도 남은 것 (보통 0)
    diagnostics: dict                             # per-stage 로그, detour ratio 등
```

**Hub은 별도 필드 없음** — `fixture.hub_room_index` (또는 첫 `public` 방)로
조회. 이는 Phase 7 컨벤션 유지.

**Door 정보 없음** — 별도 phase로 미룸.

---

## 3. Stage 1: Base corridor (hub-radial)

### Hub 인접 사전 처리

각 non-hub 방에 대해:

- **Direct hub adjacency** — 방의 region 중 하나라도 hub의 region과
  region_graph 상 4-인접하면 그 방은 carve 없이 통과 (door는 별도 phase).
- 표시만 하고 다음 방으로 (그 방에 대한 carve 작업 0).

### Carve 처리 순서

남은 방들을 **현재 area 작은 순**으로 정렬해서 순차 처리. 이유:
작은 방을 먼저 처리하면 큰 방을 carve할 후보 region이 많이 남아있는
상태에서 처리 → A* cost가 더 잘 분산.

각 방 R에 대해:

1. **현재까지 깎인 corridor에 인접한가?** → 그렇다면 carve 없이 통과
   (이미 이전 carve로 corridor가 R 옆에 깔린 상태).
2. **아니면 A* carve**: hub의 region들에서 시작, R의 region들에서 종료.
   region_graph 위에서 A*.

### Stage 1 cost table (region 단위)

| Region 종류 | Cost |
|---|---|
| Hub region (시작점) | 0.01 |
| Target room R의 region (종료점) | 0.01 |
| Unclaimed region (`unassigned_region_ids`) | 0.01 (★ 변경: 0.1→0.01) |
| 이미 깎인 corridor region | 0.01 |
| 다른 방의 boundary region | `1.0 × (20 / room_size_m2)` |
| 다른 방의 interior region | `8.0 × (20 / room_size_m2)` |

**Boundary vs interior 판정**: 그 방의 region 중 하나라도 그 방이
아닌 region에 4-인접하면 boundary, 아니면 interior.

**`room_size_m2` 하한**: post-carve 방 area가 `fixture.role_area_ranges[role].min`
이하로 떨어질 위험이 있는 region은 **hard block** (cost ∞). 아래
"Hard gates" 참조.

### Carve action

A*가 찾은 path의 region들 중:

- hub region, target room region → 변경 없음
- 다른 방의 region → 그 방의 `region_ids`에서 빼고 `base_corridor_region_ids`에 추가
- unclaimed region → 바로 `base_corridor_region_ids`에 추가

### Disconnection 검사

Carve 후 각 방이 region_graph 상 single connected component인지 확인.
disconnect되면 그 carve를 abort + 다음 후보 path 시도. 후보가 없으면
A*를 cost penalty 올려서 재시도.

---

## 4. Stage 2: Detour shortcut

### 4.1 거리 측정 — 두 종류

**Map distance** — territory 안에서 모든 region 통과 가능한 BFS.
"벽/hole 빼고 직선 보행 가능"한 이상적 거리.

```python
def map_distance(R_ids_A, R_ids_B, region_graph, territory_region_ids):
    # BFS from any region in A, through any territory region,
    # until reaching any region in B.
    # 거리 = edge 수 (region hop count).
```

**Corridor distance (strict)** — corridor + hub + 시작/종료 방의
**corridor-adjacent boundary region**만 통과 가능한 BFS.

```python
def corridor_distance_strict(R_ids_A, R_ids_B, corridor_ids, hub_ids, region_graph):
    # 시작 노드 = A의 region 중 corridor 또는 hub에 인접한 것
    # 종료 노드 = B의 region 중 corridor 또는 hub에 인접한 것
    # 통과 가능: corridor + hub + 시작/종료 노드 그 자체만
    # (방 내부 region을 가로지르지 않음)
```

★ 정정 (sandbox 대비): sandbox는 BFS가 A/B의 **모든 cell**을 통과 허용했음.
우리는 **corridor-adjacent boundary region만** 시작/종료로 한정 → "두
방의 출입 후보점 사이 거리"가 명료해짐. 큰 방 내부 가로지르기로
인한 인위적 ratio 증가 방지.

### 4.2 Detour ratio + threshold

```
detour_ratio = corridor_distance / map_distance
```

**Threshold는 단일값** — hub도 일반 방과 동일 룰. Hub가 "특별한 방"이라
강조하지 않고, hub 모양 보호는 별도의 hard gate (§6.3)로 처리.

Building type이 사용자의 사용 의도를 표현하는 한 파라미터:

| Building type | Threshold | 효과 |
|---|---|---|
| 거주 (집/아파트) | 2.5~3.0 | 거실 중심, shortcut 최소. 거실 가로지르는 동선 자연스러움 |
| 호텔 / 공동주거 | 2.0 | 중간 — 복도형이지만 일부 단축 |
| 오피스 | 1.5~2.0 | 부서 간 직접 connection 많이 |
| 공공 / 병원 | 1.3~1.5 | grid 같은 corridor 네트워크 |

- ratio ≥ threshold이면 shortcut carve 발동
- **현재 33 케이스는 거주 (한국 아파트)** → 초기값 **2.5**
- LayoutFixture에 `detour_threshold: float` 필드 추가 (default 2.5)

### 4.3 Entrance 정의

- **일반 방 R**의 entrance = R의 region에 region_graph 상 4-인접한
  (corridor region ∪ hub region).
- **Hub**의 entrance = hub region 중 non-hub region에 4-인접한 것 (hub boundary).

### 4.4 Strict A* cost table

핵심: **기존 hub와 corridor 통과는 hard block**. 그래야 새 path가
다른 방을 깎으면서 진행 → 진짜 새 corridor 생성.

| Region 종류 | Cost |
|---|---|
| Entrance region (시작/끝) | 0.01 |
| 다른 hub region | **∞ (hard block, territory_mask에서 제외)** |
| 다른 corridor region | **∞ (hard block)** |
| 시작/종료 방 region | 5.0 (avoid entering) |
| Unclaimed region | 0.01 |
| 다른 방 boundary region | `1.0 × (20 / room_size_m2)` |
| 다른 방 interior region | `8.0 × (20 / room_size_m2)` |

★ 정정 (sandbox 대비): sandbox는 `BLOCKED_COST = 50`이라는 큰 값이라
실제론 soft block. 작은 방 interior가 `8 × 20/4 = 40`이 되면 50을
역전 가능 → hub/corridor가 새 carve로 가로질러지는 케이스 발생.
우리는 territory_mask에서 아예 제외해서 hard block.

### 4.5 Iterative greedy + retry semantics

```python
processed = set()      # carve 성공한 페어 (재처리 방지)
deferred = set()       # 이번 iter A* 실패한 페어 (다음 iter 재시도)
fail_count = {}        # 페어별 누적 실패 수

for it in range(MAX_ITER):
    # 모든 페어 (방-방, hub-방) 의 detour_ratio 계산
    # processed에 있는 페어는 제외
    # ratio 가장 큰 페어 선택
    if 모든 ratio < threshold:
        break
    페어 P = argmax(ratio)

    entrA, entrB = find_entrances(...)
    if not entrA or not entrB:
        deferred.add(P)        # 다음 iter에 entrance 다시 생길 수도
        continue
    path = astar_strict(...)
    if path is None:
        fail_count[P] += 1
        if fail_count[P] >= 3:
            processed.add(P)   # 3번 연속 실패 → 영구 제외
        else:
            deferred.add(P)
        continue
    # carve
    apply_path_carve(path)
    processed.add(P)
    deferred.discard(P)
```

★ 정정 (sandbox 대비): sandbox는 실패 시 즉시 `processed.add(P)`로
영구 제외 → 다음 carve가 P의 entrance를 만들어줘도 다시 못 봄.
deferred 도입으로 한 carve 후 entrance가 새로 생긴 페어를 재처리 가능.
무한루프 방지로 fail_count 3-strike.

### 4.6 Stage 2 carve action

A* path의 region 중:

- hub region, 기존 corridor region: 스킵 (skip — territory mask에서 막혀서
  도달 안 함, defense in depth)
- 시작/종료 방 region: 스킵
- 그 외 방 region: 원 주인 방의 `region_ids`에서 제거 + `shortcut_corridor_region_ids`에 추가
- unclaimed region: 바로 `shortcut_corridor_region_ids`에 추가

Disconnection 검사 (Stage 1과 동일).

---

## 5. Cleanup — Stage 2 종료 후

남은 unassigned region 처리. **우선순위 순서**:

1. **Corridor/hub 흡수**: corridor 또는 hub에 4-인접한 unassigned region →
   corridor에 흡수 (`base_corridor_region_ids`에 추가; 그냥 보조).
2. **인접 방 흡수**: 어떤 방에도 직접 인접하지만 corridor에는 인접 안 함.
   인접 후보 방들 중 **carve 후 aspect가 가장 정사각형에 가까운** 방
   (`abs(aspect - 1)` 최소) 의 `region_ids`에 추가.
   - tie-break: 더 작은 방 우선 (작은 방의 area 보전).
3. **외딴 region**: 위 둘 다 안 됨. `leftover_region_ids`로 남김
   (★ 추가 공간으로 간주, 별도 ID 부여 안 함).

★ Sandbox 대비: sandbox는 "residual ★ room"을 carve의 cost 후보로
미리 만들었음. 우리는 **사전 처리 없이 cost 0.01**로 두고 corridor가
자연스럽게 흡수하게 함. cleanup이 사후 처리.

---

## 6. Hard gates (모든 stage 공통)

다음 위반 시 그 carve action을 abort:

### 6.1 Post-carve min_area

각 방의 carve 후 area가 `fixture.role_area_ranges[role].min` 이상.
위반하는 region은 cost ∞로 막거나 path 자체 abort.

### 6.2 Post-carve connectivity

각 방이 region_graph 상 single connected component (Stage 1/2 모두).

### 6.3 Post-carve rectness/aspect (hub 보호)

Hub의 경우, carve 후:
- `aspect ratio ≤ fixture.role_aspect_ranges["public"].max` (현재 1:4)
- `rectness ≥ 0.7` (bbox 안에서 hub region 면적 비율)

일반 방도 동일하게 aspect range 적용 (이미 Phase 7에서 grow 시 적용).

위반 시 그 carve abort + 다음 후보.

### 6.4 Corridor 자체 width 보장

★ 추가: corridor region이 너무 좁아지면 안 됨 — region 단변이
`min_corridor_width` (예: 0.9m) 이상. 단변이 그 미만인 region은 cost ∞.
33 케이스 결과 보고 임계값 조정.

---

## 7. Deferred (다음 phase)

### Door 위치

각 방에서 corridor 또는 hub와 공유 변 → 그 변 위에 door 표시.
정교화는 별도 phase:

- 외벽 회피 (구조벽일 가능성)
- 공유 경계 중앙 우선
- 한 방에 multi-door 허용 여부

### Atom-level refinement

Region carve 결과 코너 두께 불균일이 비주얼적으로 거슬리면:

- Corridor region들을 atom으로 다시 쪼개기
- Atom 단위로 trim/extend로 두께 일정화
- 별도 sub-phase로 추가

---

## 8. Open questions

1. **거주 threshold 2.5는 추측치** — 33 케이스 돌려보고 조정 (2.5~3.0 범위 내).
2. **`min_corridor_width` 임계값** — 0.9m 추측. 실제 carve 결과 보고
   조정.
3. **Region이 너무 큰 경우 잘게 쪼개기** — regionize에 `max_region_size`
   파라미터를 추가해서 corridor용으로 더 잘게 만들 수 있게 할지.
   현재 phase에선 미루고 비주얼 보고 결정.
4. **Magic number들** (cost table의 1.0/8.0, `20/room_size`의 20, fail_count
   3-strike 등) — 일단 sandbox 값 그대로 가져옴, 33 케이스 결과 보고 튜닝.

---

## 9. Module layout (planned)

```text
celllayout_tf/
  corridor.py              # Stage 1 + Stage 2 + cleanup 메인 entry
  corridor_astar.py        # A* on region_graph (cost tables 분리)
  corridor_distance.py     # map_distance + corridor_distance_strict
  schema.py                # CorridoredLayout 추가
tests/
  test_corridor.py         # 33 케이스 회귀
demos/
  visualize_phase.py       # --phase corridor 추가
```

---

## 10. Decisions log

| # | 결정 | 이유 |
|---|---|---|
| 1 | 입자 단위 = region | 복도 폭 자연스러움 + region_graph 재활용; 코너 두께 불균일 trade-off 수용 |
| 2 | Sandbox 코드 ad-hoc port | sandbox는 cell-level, 우리는 region-level — 디자인만 가져옴 |
| 3 | Residual: 사전 무처리, cost 0.01 | corridor가 자연스럽게 빈 공간 먼저 채우게 |
| 4 | Cleanup 순서: corridor 흡수 → 인접 방 (aspect 정사각형 우선) → leftover | 작은 dent 메우기 우선, 모양 보존 |
| 5 | Hub-방 페어 포함, threshold 단일값 (거주=2.5) | hub도 일반 방과 동일 룰 — building type별 한 파라미터로 사용자 의도 반영. Hub 모양 보호는 별도 hard gate (§6.3)로 처리 |
| 6 | `corridor_distance_strict`는 corridor-adjacent boundary로 한정 | 방 내부 가로지르기로 인한 인위적 ratio 증가 방지 |
| 7 | Hub/corridor 통과 = hard block (territory_mask 제외) | sandbox의 cost=50은 작은 방 interior cost와 역전 가능 |
| 8 | A* 실패는 deferred, fail_count 3-strike로 영구 제외 | 다음 carve가 entrance 만들어줄 수 있음 |
| 9 | Door 위치는 별도 phase | corridor 안정화 후 정교화 |
| 10 | Atom-level refinement는 옵셔널 future phase | region 단위 결과 보고 결정 |

---

## 11. Validation 목표

Sandbox v6 결과 (12 territory)와 등가 또는 우월:

- **Disconnect 0건**: Stage 1/2 후 모든 방 single component.
- **모든 방이 hub와 직접/경유 연결**.
- **Corridor가 single connected component** (33 케이스 모두).
- **Hub 모양 보존**: aspect ≤ 1:4, rectness ≥ 0.7.
- **Carved 방의 area가 `min_area` 이상**.
- **Detour 적정**: 단순 territory (직사각, L) shortcut 0; 복잡 territory
  (donut, two-hole) 1~3개 shortcut.
- **각 corridor region 단변 ≥ `min_corridor_width`** (잠정 0.9m).
