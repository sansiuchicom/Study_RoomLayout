# celllayout — Vertex-First Deterministic Zoning

Footprint polygon을 sub-room building block으로 분할하는 알고리즘.

## 구조

```
algorithm/
├── celllayout/
│   ├── __init__.py
│   ├── atom/                # Cell decomposition (per-family theta extraction)
│   │   ├── angles.py
│   │   ├── fixed_grid.py
│   │   ├── lir_progressive.py
│   │   ├── per_family.py
│   │   └── theta.py
│   ├── zoning.py            # ★ Pipeline 20 algorithm (essence ~360 lines)
│   └── cases.py             # 33 showcase footprints
├── demo.py                  # Entry point (run all cases → save figures)
├── outputs/                 # Generated figures
├── requirements.txt
└── README.md (이 파일)
```

## 빠른 실행

```bash
cd algorithm
pip install -r requirements.txt
python demo.py              # 33 케이스 전체
python demo.py 4 14 29      # 특정 케이스만 (1-based index)
```

결과는 `outputs/g{1,2,3}.png`에 저장.

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

## Reference

Legacy 자료(이전 버전 pipeline12 + 비교 + 상세 doc)는 repo 루트의 [../legacy/](../legacy/) 폴더 참조.
