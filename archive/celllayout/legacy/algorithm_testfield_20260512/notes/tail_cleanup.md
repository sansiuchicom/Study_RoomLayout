# Tail Cleanup — Multi-axis Transition Wedge 처리

**작성일**: 2026-05-12
**관련 파일**: [`celllayout/zoning.py`](../celllayout/zoning.py) §7 Tail cleanup
**트리거 케이스**: `cases.py` #24 `"7자 angled (-25 + 0°)"`

## 1. 문제 — group 2 마지막 케이스의 graph 이상 동작

`7자 angled` footprint = 기울어진 wing (-25°) + 수직바 (0°). 초기 zoning 결과:

- Z4 (수직바 중간, family 1 / theta=0°)의 polygon이 `(0, 8)`까지 사선으로
  뻗는 thin needle을 포함
- Graph에서 Z4가 Z0/Z1 (rotated wing zones)와 320cm씩 phantom diagonal
  edge로 연결됨
- 반대로 Z2와는 4cm sliver만 공유 (5cm filter에서 떨어져 미연결)

가설은 graph hallucination이었지만 polygon vertex 추적 결과 **실제 polygon
boundary가 그렇게 생겨 있음** — graph는 옳게 그린 것.

## 2. 진단 — wedge가 axis-aligned family에 흡수됨

`get_families()`가 만든 family polygon 출력:

```
fam 0: area=30.819, theta=65° (= -25° mod 90°)  ← rotated wing family
fam 1: area=14.256, theta=0°                    ← axis-aligned family
```

Family 1 (axis-aligned)의 vertex 목록에 `(0, 8)`, `(8.7039, 3.95)` 등
사선 위 점들이 포함. 즉 **사선 wedge가 축정렬 family에 들어가 있음** — 직관과 반대.

메커니즘 (`recursive_progressive_per_family`):

1. Level 0: 기울어진 wing 내부에서 -25° rotated LIR 잡힘 → family 0
2. Remainder = footprint − rotated_LIR = (수직바) + (기울어진 wing의 잔여
   strip들). 한 polygon으로 연결됨
3. Level 1: remainder의 새 LIR (수직바 axis-aligned) → family 1
4. Level 1 remainder = 기울어진 wing의 사선 wedge. **같은 family chain
   안에서 theta=0으로 흘러감** (theta 변화 없으면 family_id 상속)
5. 결과: family 1 polygon = 수직바 + 사선 wedge

`partition_family`는 family 1을 theta=0 frame에서 axis_mid로 자름.
Z3 (아래 사각형) + Z4 (위, 수직바 윗부분 **+ 사선 wedge** 흡수).

## 3. 1차 시도 — 단일 recipient 이동

**전략**: zone의 family-theta-aligned LIR 밖에 있고 thin elongated (aspect
≥ 6)인 영역을 "foreign tail"로 검출해, orientation 호환되는 (theta가
±10° 안에서 일치) 이웃 zone 중 가장 길게 접한 zone에 이동.

**결과**: Z4의 wedge가 Z0 (rotated wing 중간)으로 옮겨가서 Z4는 깔끔해졌으나,
Z0이 **peanut 모양** (hull_ratio 0.457). 시각적으로 "한 zone이 두 덩어리"로
보임.

**원인**: wedge가 길이 ~10m × 폭 ~7mm의 needle. 어느 한 wing zone에 통째로
붙이면 그 zone은 본체 + thin spike의 peanut이 됨. 단일 recipient로는
unavoidable.

## 4. 2차 시도 — Multi-recipient slicing

**전략**: wedge를 family rotated frame의 long-axis (여기선 y)로 잘라서
호환되는 모든 recipient에 분배.

```
wedge in rotated frame: x∈[6.54, 7.26], y∈[-6.21, 3.38]
  → long axis: y (span 9.59 > 0.72)

recipient ranges (in rotated y):
  Z2: [-6.26, -3.05]  ← 슬라이스 0.683 m² (wedge의 93%)
  Z0: [-3.05,  0.16]  ← 슬라이스 0.025 m²
  Z1: [ 0.16,  3.38]  ← 슬라이스 0.025 m²
```

각 슬라이스를 자기 recipient에 merge.

### 4a. Sub-tolerance gap bridge

Z2와 wedge는 **평행하지만 7mm offset**인 line으로 분리되어 있음
(`shapely`의 contact 계산은 0 cm). 직접 `unary_union(Z2, slice)` 하면
MultiPolygon 반환.

해결: **morphological opening**으로 sub-tolerance gap 메꿈.

```python
direct = unary_union([target, piece])  # MultiPolygon
bridged = direct.buffer(+0.02, mitre).buffer(-0.02, mitre)
# tol=2cm > 7mm gap이라 메꿔지지만, 외부 boundary는 거의 변화 없음
```

**검증**: bridge 후 area change = 0.000 m² (옆 zone에 침범 없음). Z2 area
11.57 → 12.25, hull_ratio 0.963 (compact, no peanut).

### 4b. Coordinate precision quantization

Slicing + bridge merge가 끝나도 graph가 **2 components**로 갈라짐 —
Z0-Z2 shared boundary가 3m → **1.8 cm**로 collapse.

원인: Z0와 Z2가 같은 vertex `(5.838, 5.298)`, `(5.831, 5.281)`을 가지고
`distance=0`인데도 `boundary.intersection()`은 1.8cm만 잡음. Shapely
내부의 ULP-level 좌표 차이가 segment match를 방해.

해결: 마지막에 **`shapely.set_precision(polygon, 0.001)`** (1mm grid)
로 모든 zone polygon을 quantize. Z0-Z2 boundary 3.00m 정상 복원.

```python
for z in zones:
    z['polygon'] = shapely.set_precision(z['polygon'], 0.001)
```

## 5. False positive 방지를 위한 3중 필터

`_detect_foreign_tails`는 다음 조건을 **모두** 만족하는 영역만 tail로 인정:

1. **Shape**: `area ≥ TAIL_MIN_AREA(0.3 m²)` AND
   `MRR aspect ≥ TAIL_MIN_ASPECT(6.0)` — chunky한 일반 bulge 제외
2. **Source orientation**: `tail_theta ≠ family_theta` (mod 90°, 10° tol)
   — family와 같은 방향의 LIR 잔여는 native이라 foreign 아님
3. **Recipient orientation**: 이동하려는 zone의 `family_theta ≈
   tail_theta`. 매칭되는 recipient 없으면 source에 그대로 둠.

특히 (3) 없으면 `Mirror wings ±30°` 케이스에서 +30° wing의 tail이 0° main
box zone으로 옮겨가서 거기서 또 foreign tail이 되는 **idempotency
실패** 발생.

## 6. 최종 알고리즘

```
zone_footprint() 끝부분에 추가:

7. tail cleanup:
   for each zone:
     tails = _detect_foreign_tails(zone, family_theta)
       (LIR diff + shape/orientation 필터)
     for each tail:
       compatibles = [z for z in zones
                       if z != source and theta_match(tail, z)]
       if not compatibles: skip
       slices = _slice_tail_among_recipients(tail, family_theta,
                                              compatibles)
       leftovers = tail - union(slices)
     if no slices: skip
     source.polygon = _strip_tails(source, all_pieces)  # mitre opening
     for slice, target in slices:
       merged = _bridge_merge(target, slice)
         (direct union → fallback: buffer(+tol).buffer(-tol))
       if merged: target.polygon = merged
       else: return slice to source
     source += leftovers

8. clip all zones to footprint
9. shapely.set_precision(0.001) on all zones
```

## 7. 33 케이스 회귀 결과

| 항목 | 결과 |
|---|---|
| Disconnected components | 0/33 |
| max aspect 6 초과 | 1/33 (60평 큰 ㄱ자, pre-existing, tail cleanup과 무관) |
| Gap > 0.1% | 0/33 |
| Inter-zone overlap > 0.1% | 0/33 |
| 7자 angled Z0 hull_ratio | 0.457 (peanut) → 1.000 (clean) |
| 7자 angled Z2 hull_ratio | (변동 없음) → 0.963 (자연 확장) |

7자 angled 외의 multi-axis 케이스 (`Main + wing 25°`, `Mirror wings ±30°`)
는 baseline 그대로 — orientation 매칭 안되는 recipient를 만나지 못해
cleanup이 발동하지 않음. 의도된 동작.

## 8. Parameter 표

| Constant | 값 | 의미 |
|---|---|---|
| `TAIL_MIN_AREA` | 0.3 m² | tail 최소 면적 |
| `TAIL_MIN_ASPECT` | 6.0 | tail 최소 MRR aspect |
| `TAIL_MIN_CORE` | 0.4 | family-theta LIR / zone area 비율 하한 |
| `TAIL_THETA_TOL` | 10° | source/recipient theta 매칭 오차 |
| `TAIL_BRIDGE_TOL` | 0.02 m | morphological opening 반경 |
| `TAIL_SLICE_MIN` | 0.01 m² | slice numerical noise drop |

## 9. 알려진 한계

- **Multi-axis 케이스 중 wedge가 단방향만 분포한 경우**: 호환 recipient가
  하나뿐이면 단일 흡수 → 약간의 peanut 가능. 7자 angled은 3개 recipient
  덕분에 깨끗하게 분배됨.
- **`set_precision(0.001)`의 부작용**: 회전된 polygon은 1mm 격자로 양자화
  되면서 footprint와 sub-mm 오차 발생 (gap/overlap < 0.01%). 실용상 무시
  가능.
- **`MIN_AREA(3.0 m²)` 미만 wedge**: 자체 zone 생성 불가라 항상 다른
  zone에 흡수돼야 함. Wedge가 더 크고 호환 recipient가 없으면 현재는
  source에 잔류 (transition zone 별도 모델링은 다음 단계).
