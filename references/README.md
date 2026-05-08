# References

External research artifacts ported into proto3.

## Auto LIR + Per-family Recursive Progressive Fill (v3.2)

Source: User external development, dated 2026-05-08.

| 파일 | 내용 |
|---|---|
| `lir_recursive_per_family_v3_2.py` | Algorithm implementation (~500 lines). Original filename: `02M_per_family.py`. |
| `lir_recursive_per_family_v3_2.md` | Self-contained algorithm documentation. Original filename: `auto_lir_progressive_algorithm_v3_2.md`. |
| `stress_test_15_shapes.png` | 15 일반 footprint stress test — 한글 자모(ㄱㄴ7ㅗ十口UH ㄷZ), mirror, 회전 wing, multi-wing complex. 모두 0% gap. |
| `stress_test_15_edge_cases.png` | 15 LIR-unfriendly edge case — star/blob/swiss cheese/circle/ellipse/triangle/rhombus/spiky 등. 14/15 0% gap (1개 0.17% gap, 45° floating-point edge case). |

Ported into `src/proto3/geometry/` during Step 05 (Geometry Kernel) per Plan §2 (S05-Dxx) and Architecture Decision D019 (D006 amendment — per-family proportional atom sizing).

이 디렉토리는 origin 보존용입니다. 직접 수정하지 마세요. 알고리즘 변경은 `src/proto3/geometry/` 쪽에서 처리합니다.
