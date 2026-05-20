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

### Stage 1 cost table (region 단위, W2 구현)

| Region 종류 | Cost |
|---|---|
| Hub region (시작점) | 0.01 |
| Target room R의 region (종료점) | 0.01 |
| Unclaimed region (`unassigned_region_ids`) | 0.01 |
| 이미 깎인 corridor region | 0.01 |
| 다른 방의 **outline** region | `1.0 × (20 / room_size_m2)` |
| 다른 방의 interior region | `8.0 × (20 / room_size_m2)` |

`room_size_m2`는 carve 시점의 그 방 area, `max(room_size, 4 m²)` 하한.

**Outline 판정** (room R에 속하는 region X에 대해):

X의 둘레 어딘가가 R의 **outer outline**에 닿으면 outline. 한 가지로
통일:

- 다른 방의 region과 4-인접 — outline ✓
- **Footprint 외벽 또는 구멍 경계에 닿음** — outline ✓
- 위 둘 다 아니고 모든 둘레가 같은 방 region과 공유 — interior

호텔처럼 내부 corridor도 자연스러우니 footprint-edge와 다른방-인접은
동등 cost. "방 쪼개기 금지"는 cost 차별이 아니라 별도 hard gate(아래)로 보장.

### Carve action

A*가 찾은 path의 region들 중:

- hub region, target room region → 변경 없음
- 다른 방의 region → 그 방의 `region_ids`에서 빼고 `base_corridor_region_ids`에 추가
- unclaimed region → 바로 `base_corridor_region_ids`에 추가

### Disconnection gate (simulation + minimal-cut retry)

A* path는 **commit 전 simulation**으로 검증:

> 이 path를 carve하면 어떤 non-target 방이 empty되거나 split되는가?

위반 시 그 path의 carved regions 중 *진짜로* split/empty를 일으키는
**greedy minimal cut**만 `forbidden`에 추가 (각 region을 한 번씩
빼보면서 그래도 split이면 그 region은 무고하므로 drop). 무고한
region — slicing path와 valid path가 공유하는 region — 은 보호되어
다음 A* 시도에서 재사용 가능.

`forbidden` 갱신 후 A* 재시도, 최대 30회. 30회 이내에 valid path를
못 찾으면 그 target은 unreached로 기록 (`stage1.log`에 `astar-failed`).

★ 정정 (초기 설계 대비): single-removal cut vertex 사전 차단은 시도
했으나 multi-region carve에서 false positive 너무 많음 (각 region은
무고하지만 합쳐서 slicing). 제거하고 full-path simulation으로 일원화.

---

## 4. Stage 2: Detour shortcut

### 4.1 거리 측정 — 두 종류 (hub-collapse BFS)

두 거리 모두 **hub 영역을 단일 supernode**로 취급하는 BFS hop count.
Hub는 사람이 자유롭게 이동하는 공간이라 region 5개 통과나 1개 통과나
실제 동선상 차이 없음 — region-level hop으로 누적되면 dc/dm 모두
인위적으로 부풀어. Corridor와 일반 방은 region-level 그대로 (corridor는
실제로 통과 거리).

**Map distance** — territory 내 모든 region 통과 가능한 BFS.

```python
def map_distance(R_ids_A, R_ids_B, hub_regions, region_adj, all_regions):
    # hub_regions는 단일 supernode로 collapse
    # BFS from any region in A, through any territory region,
    # until reaching any region in B. hub 진입 = 1 hop, hub 내 이동 = 0.
```

**Corridor distance (strict)** — corridor + hub + 시작/종료 방의
**corridor-adjacent boundary region**만 통과 가능한 BFS. hub collapse 동일.

```python
def corridor_distance_strict(entr_A, entr_B, corridor, hub_regions, region_adj):
    # 시작 노드 = A의 region 중 corridor 또는 hub에 4-인접 (= entr_A)
    # 종료 노드 = B의 region 중 corridor 또는 hub에 4-인접 (= entr_B)
    # passable = corridor ∪ hub ∪ entr_A ∪ entr_B
    # hub_regions는 단일 supernode로 collapse
```

★ 정정 (W3 추가): 초기 region-level BFS는 hub가 큰 거주 케이스에서
ratio를 부풀려 단순 L-shape에서도 false positive 발동. Hub-collapse로
ratio가 "공간 traversal 수"에 더 가까운 의미가 됨.

★ 정정 (sandbox 대비): sandbox는 BFS가 A/B의 **모든 cell**을 통과 허용했음.
우리는 entrance만 시작/종료. 큰 방 내부 가로지르기로 인한 인위적
ratio 증가 방지.

### 4.2 Detour ratio + threshold

```
detour_ratio = corridor_distance / map_distance
```

**Threshold는 단일값** — hub도 일반 방과 동일 룰. Hub가 "특별한 방"이라
강조하지 않고, hub 모양 보호는 별도의 hard gate (§6.3)로 처리.

Building type이 사용자의 사용 의도를 표현하는 한 파라미터 (hub-collapse
기준 새 값):

| Building type | Threshold | 효과 |
|---|---|---|
| **거주 (집/아파트)** | **2.0** | 거실 중심, donut처럼 hole이 강제하는 우회만 shortcut |
| 호텔 / 공동주거 | 1.7 | 일부 직접 connection |
| 오피스 | 1.4~1.7 | 부서 간 직접 connection 많이 |
| 공공 / 병원 | 1.2~1.4 | grid 같은 corridor 네트워크 |

- ratio > threshold이면 shortcut carve 발동 (**strict `>`** — 동일값은 발동 안 함)
- **현재 33 케이스는 거주 (한국 아파트)** → 초기값 **2.0**
- LayoutFixture에 `detour_threshold: float` 필드 (default 2.0, validation `>= 1.0`)

★ 정정 (W3 추가): 처음 표는 region-level distance 기준이었음 (거주 2.5).
Hub-collapse 도입 후 ratio 분포가 줄어 거주 cases 대부분 1.0~1.5,
genuine donut만 2.3+. 새 단위로 표 재조정. Strict `>`로 L-shape의
"ratio 정확히 2.0" 경계 케이스 (case 10, 28) 자연 제외.

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

W2 Stage 1과 동일한 mechanism (simulation + minimal-cut retry) 재사용.
바깥 loop은 max ratio 페어 greedy 선택.

```python
processed_pairs = set()
for it in range(MAX_OUTER_ITER):  # 30
    # 모든 페어 (방-방, hub-방, 단 processed 제외)의 detour_ratio 계산
    # 필터: dm > 1 (이미 4-인접하면 detour 없음, skip)
    # 필터: entrance 비어있으면 skip
    if 모든 ratio <= threshold:
        break
    P = argmax(ratio)

    # Stage 1과 동일한 simulation + minimal-cut retry (30회)
    path = astar_with_retry(P, ...)
    if path is None:
        processed_pairs.add(P)
        continue
    apply_carve(path)  # path 위 (corridor + hub + src/tgt 제외) regions를 shortcut으로
    processed_pairs.add(P)
```

★ 정정 (초기 설계 대비): 처음 spec은 deferred + 3-strike retry 매커니즘
이었는데 (sandbox 정정), 실제로는 Stage 1과 동일한 simulation + minimal-cut
retry로 통일. 더 단순하고 Stage 1과 동일한 안전성 보장.

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
**Enforcement**: §3 "Disconnection gate" 참조 — A* simulation + minimal-cut
forbidden retry로 hard 보장. Stage 2도 같은 mechanism 적용 예정.

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

## 9. Module layout

```text
celllayout_tf/
  corridor.py              # Stage 1 (W2 구현됨); Stage 2/cleanup 들어갈 자리
  viz.py                   # save_corridor_figure (W2)
tests/
  test_corridor.py         # 33 케이스 회귀 + invariant
demos/
  visualize_phase.py       # --phase corridor (auto-seed 고정)
```

원래 `corridor_astar.py`/`corridor_distance.py` 분리 예정이었으나, W2
시점에 `corridor.py` 한 파일이 ~470줄로 아직 다룰 만함. Stage 2/cleanup
들어가면서 파일 키지면 그때 분리.

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
| 11 | **Outline = 다른 방 인접 OR 외벽/구멍 접촉** (W2 추가) | spec 의도 "방 외곽선을 따라 흐르고"는 외벽도 포함 — 호텔 같은 내부 corridor 자연스러움. 차별화 없이 동일 cost. |
| 12 | **Disconnection gate = simulation + greedy minimal-cut retry** (W2 추가) | Cut vertex 단일 제거 사전 차단은 multi-region carve를 over-block. Full path simulation으로 실제 위반만 reject + minimal cut으로 무고한 공유 region 보호. |
| 13 | Stage 1은 단일 module `corridor.py` (W2 구현) | 470줄 수준이라 분리 보류; Stage 2/cleanup 추가로 커지면 그때 split |
| 14 | Viz는 항상 auto-seed로 강제 (W2) | Manual fixture seed는 `auto_place_seeds_by_cells`와 어긋나 비현실적 partition 생성. 테스트는 manual fixture 그대로 (deterministic). |
| 15 | **거주 threshold 2.5 → 2.0 strict `>`** (W3) | Hub-collapse로 ratio 분포 압축 후 단순 L-shape(case 10/28)가 정확히 2.0, donut(case 17)이 2.33. Strict 비교로 경계 자연 제외, donut만 통과. |
| 16 | **Hub-collapse BFS** for dm, dc (W3) | Region-level hop count는 큰 hub를 통과할 때 dc 인위 부풀려져서 L-shape도 false positive. Hub는 walking 자유 구역이라 단일 supernode로 취급이 의미적으로 정확. Corridor는 region-level 유지 (실제 통과 거리). |
| 17 | Stage 2 retry mechanism = Stage 1과 동일 (W3) | Spec 초기의 deferred + 3-strike 매커니즘 → simulation + minimal-cut retry로 통일. 코드 단순. |
| 18 | Stage 2 pair pre-filter: `dm > 1` (W3) | 두 방이 이미 4-인접하면 detour 없음. Trivial path가 trivially "carved"라 마킹되는 false log 방지. |
| 19 | Case 17 fixture K=4 → K=5 (W3) | K=4 partition에서 한 방이 36㎡ wrap-around로 비현실적. 5번째 private 추가로 균형 잡힘. (방 분포 spec PHASE7_Fixtures.md과 일관) |

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

### W2 측정 결과 (Stage 1만)

| Metric | 결과 |
|---|---|
| Auto-seed 33 cases | 0 unreached, 0 split, 0 emptied |
| Manual seed fixtures (tests) | 41/41 pass |
| 직접/corridor 경유 hub 연결 | 모든 non-hub 방 ✓ |

### W3 측정 결과 (Stage 1 + Stage 2, threshold > 2.0)

| Metric | 결과 |
|---|---|
| Auto-seed 33 cases | 0 unreached, 0 split, 0 emptied |
| Stage 2 발동 | **1건** — case 17 (ㅁ자 big hole, donut), ratio 2.33, 2 region carved |
| 다른 32 cases | Stage 2 dormant (단순 L-shape 등은 hub-collapse로 ratio < 2) |

**Worst-case ratio 분포 (33 cases, hub-collapse)**:
- 1.00: ~22 cases (단순 layout)
- 1.20–1.50: ~7 cases (약한 비대칭)
- 2.00 (정확): case 10, 28 (L-shape — strict `>` 로 제외)
- 2.33: case 17 (donut — 유일하게 발동)

§6.1 min_area gate, §6.3 hub aspect/rectness gate, §6.4 corridor 단변
보장, cleanup — 모두 후속 W에서 측정.
