# RoomLayoutCell Algorithm Testfield

This directory is the safe rewrite area for a topology-first zoning engine.
The existing `celllayout/` package is a copied reference of the current
algorithm. New atomic-subdivision work should happen in `celllayout_tf/`.

## Phase 3 Baseline Planner + Atomic Subdivision

```text
algorithm_testfield/
├── celllayout/              # copied reference algorithm; keep as reference
├── celllayout_tf/           # new topology-first experiment package
│   ├── assignment.py        # atomic faces -> provisional zones
│   ├── cases.py             # showcase case facade
│   ├── geometry.py          # shared geometry helpers
│   ├── graph.py             # temporary graph facade
│   ├── planner.py           # cut planning data structures
│   ├── subdivision.py       # atomic face API skeleton
│   ├── validation.py        # partition invariant checks
│   └── zoning.py            # public testfield entry point
├── demos/
│   └── zoning_demo_tf.py    # strict-capable Phase 0 demo
└── tests/
    └── test_phase0_scaffold.py
```

Run the new scaffold:

```bash
cd /workspace/Study_RoomLayout_Cell/algorithm_testfield
PYTHONPATH=. python demos/zoning_demo_tf.py --strict
PYTHONPATH=. python demos/zoning_demo_tf.py --strict --tolerance 1e-6 --precision 0.001
PYTHONPATH=. python demos/zoning_demo_tf.py --save-figures 6 16 18 25
PYTHONPATH=. pytest -q tests
```

Phase 2 implemented the core linework polygonization in `subdivision.py`:

```text
snapped footprint boundary + holes
+ clipped planned cut lines
-> unary_union noding
-> polygonize
-> clip/keep faces inside footprint
-> shared atomic faces
```

Phase 3 adds a conservative baseline planner in `planner.py`:

```text
k = explicit k or round(area / area_per_zone)
recursive balanced world-axis cuts
cut records emitted for subdivision
candidate zones rebuilt from atomic faces
```

This is intentionally a topology-first baseline. It can already produce multiple
zones and keeps the 33 showcase cases gap/overlap/outside clean under strict
validation. It is not yet the final quality planner: rotated, curved, or awkward
concave shapes may achieve fewer zones than requested until the next planner
passes add rotated-frame/family-aware cuts.

Visualization is available through `demos/zoning_demo_tf.py --save-figures`.
Each saved PNG has three panels:

```text
Atomic Faces | Planned Cuts | Final Zones
```

By default figures are written to `outputs/testfield_zoning/`.

Strict validation reports the exact areas and counts that matter for downstream
layout work:

```text
gap_area / gap_part_count
overlap_area / pairwise overlap count
outside_area
invalid zone parts
empty zones
multipart zones
```

Next phases:

1. Improve planner quality with rotated-frame/family-aware cuts.
2. Add native graph/demo outputs and CI-friendly strict mode.

---

# Copied Reference: celllayout — Vertex-First Deterministic Zoning

Footprint polygon을 sub-room building block으로 분할하는 알고리즘.

## 구조

```
algorithm/
├── demos/
│   ├── zoning_demo.py       # Current zoning showcase runner
│   └── layout_demo.py       # Planned room-group + access runner
├── celllayout/
│   ├── __init__.py
│   ├── atom/                # Cell decomposition (per-family theta extraction)
│   │   ├── angles.py
│   │   ├── fixed_grid.py
│   │   ├── lir_progressive.py
│   │   ├── per_family.py
│   │   └── theta.py
│   ├── graph.py             # Zone adjacency graph utilities
│   ├── zoning.py            # ★ Pipeline 20 algorithm (essence ~360 lines)
│   └── cases.py             # 33 showcase footprints
├── demo.py                  # Backward-compatible wrapper for demos/zoning_demo.py
├── outputs/
│   ├── zoning/              # Generated zoning showcase figures
│   └── layout/              # Future room-group + access figures
├── requirements.txt
└── README.md (이 파일)
```

## 빠른 실행

```bash
cd algorithm
pip install -r requirements.txt
python demo.py              # 33 케이스 전체
python demo.py 4 14 29      # 특정 케이스만 (1-based index)
python demos/zoning_demo.py # same behavior, canonical zoning demo path
```

결과는 `outputs/zoning/g{1,2,3}.png`에 저장. Zoning demo는 M1
zone graph도 함께 계산해서 shared-boundary graph를 centroid-edge overlay로
표시한다.

`demos/layout_demo.py`는 다음 실험(`zone → room_group → hub/corridor`)을
위한 자리만 잡아둔 상태다. 구현 계획은 repo root의
`room_layout_experiment_plan.md`를 따른다.

## 알고리즘 한 페이지 요약

```
zone_footprint(footprint, k=None):
    1. get_families(footprint)               # cell-decomp으로 family + theta
    2. filter big families (small drop)
    3. allocate k by area
    4. for each family:
        rotate to local frame
        recursive_partition (3-tier hierarchy)
        rotate back
    5. coverage fix: gap → nearest zone
    6. clip to footprint
    7. tail cleanup (multi-axis transition wedge → orientation-compatible
       recipient zones, family long-axis slicing + bridge merge)
    return zones, families

select_cut(polygon):
    Tier 1a: cross_cut       (vertex의 V+H 동시, 3-4 piece)
    Tier 1b: vertex_aligned  (single V or H, structural coords 포함)
    Tier 2:  reflex_pair     (사선)
    Tier 3:  axis_mid        (fallback, balance threshold 무관)

핵심 디자인 선택:
- 점수 함수 X — hierarchical priority + balance threshold + tie-break
- Stage-aware aspect — final piece에만 max_aspect 강제
- Float-tolerant balance tie-break — round(balance, 6) (rotated polygon drift 방지)
- Structural coords inheritance — parent reflex 좌표를 sub-recursion에 전파
- Tail cleanup — family-theta LIR 밖의 thin foreign 영역을 orientation-호환
  recipient에 long-axis slicing으로 분배 (자세한 내용: [notes/tail_cleanup.md](notes/tail_cleanup.md))
```

## 주요 parameter

| Name | Default | 의미 |
|---|---|---|
| `MIN_AREA` | 3.0 m² | sub-room 최소 면적 |
| `MARGIN` | 0.5 m | vertex가 boundary 가까울 때 cut 제외 |
| `MIN_CUT_LEN` | 1.0 m | reflex pair line 최소 polygon 내부 길이 |
| `MAX_ASPECT` | 4.0 | final zone MRR aspect 한도 |
| `BAL_MIN` | 0.15 | T1/T2에서 한 zone ≥ 다른 zone의 ~14% |
| `SIMPLIFY_TOL` | 0.15 m | vertex 좌표 추출 시 polygon 단순화 |
| `area_per_zone` (auto k) | 10.0 m² | `k=None`일 때 자동 산정 (1 zone당 평균 면적) |
| `TAIL_MIN_AREA` | 0.3 m² | tail cleanup 대상 최소 면적 |
| `TAIL_MIN_ASPECT` | 6.0 | tail로 인정할 MRR 종횡비 (얇은 영역만) |
| `TAIL_MIN_CORE` | 0.4 | family-theta LIR이 zone 면적의 이 비율 이상이어야 동작 |
| `TAIL_THETA_TOL` | 10° | recipient family theta 매칭 허용 오차 |
| `TAIL_BRIDGE_TOL` | 0.02 m | sub-tolerance gap을 buffer로 메꾸는 한도 |
| `TAIL_SLICE_MIN` | 0.01 m² | numerical noise slice drop threshold |

## Reference

Legacy 자료(이전 버전 pipeline12 + 비교 + 상세 doc)는 repo 루트의 [../legacy/](../legacy/) 폴더 참조.
