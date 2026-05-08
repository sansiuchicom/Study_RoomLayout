# References

External research artifacts ported into proto3.

## Cell partition (v3.2) — atom layer

Source: User external development, dated 2026-05-08. Originally in author's dev env as `02M_per_family.py` + `auto_lir_progressive_algorithm_v3_2.md`.

| 파일 | 내용 |
|---|---|
| `cell_v3_2.py` | Algorithm implementation (~500 lines) — LIR + per-family recursive + anisotropic grid + 50% merge rule |
| `cell_v3_2.md` | Self-contained algorithm documentation |
| `cell_v3_2_stress.png` | 15 일반 footprint stress test 시각화 — 한글 자모(ㄱㄴ7ㅗ十口UH ㄷZ), mirror, 회전 wing, multi-wing complex. 모두 0% gap. |
| `cell_v3_2_edges.png` | 15 LIR-unfriendly edge case 시각화 — star/blob/swiss cheese/circle/ellipse/triangle/rhombus/spiky 등. 14/15 0% gap (1개 0.17% gap, 45° floating-point edge case). |

Ported into `src/proto3/geometry/{lir,grid,recursive,decompose}.py` during Step 05 (Geometry Kernel) per Plan §2 (S05-D1) and Architecture Decision D019 (D006 amendment — per-family proportional atom sizing).

## Zoning (v12) — region/zone layer

Source: User external development, dated 2026-05-08. Originally in author's dev env as `12_zoning_clean.py` + `zoning_documentation.md`.

| 파일 | 내용 |
|---|---|
| `zone_v12.py` | Algorithm implementation (~290 lines) — vertex-first hierarchical zoning. Deterministic, no scoring functions. |
| `zone_v12.md` | Self-contained algorithm documentation (design rationale, evolution history, validation) |
| `zone_v12_evolution_g1.png` | v11 (점수 기반) → v12 (clean deterministic) 진화 시각 비교, group 1 |
| `zone_v12_evolution_g2.png` | 진화 비교 group 2 |
| `zone_v12_evolution_g3.png` | 진화 비교 group 3 |
| `zone_v12_showcase.png` | v12 final 33 cases showcase — 한국 아파트, 단순 직사각, 회전, multi-axis, 곡면, 복잡 모두. 평균 quality 0.96, 33/33 0% gap. |

**Planned integration**: Step 07 (Region/Atom Decomposition). v12 produces zone polygons that map onto proto3 `Region` candidates (D006 architectural territory layer; label assigned later in Step 09 via spine candidate). Cell layer (v3.2) is consumed indirectly through `GeometricPiece` → family info.

---

## Conventions

- **이 디렉토리는 origin 보존용**입니다. 직접 수정하지 마세요. 알고리즘 변경은 `src/proto3/geometry/` 또는 미래 `src/proto3/zoning/` 쪽에서 처리합니다.
- 파일명 prefix: `cell_*` = atom-layer artifacts, `zone_*` = region-layer artifacts.
- 외부 author dev env에서 인용된 다른 파일들 (`02e_improved.py`, `02h_progressive.py`, `02L_final.py`, `03_cell_graph.py` 등)은 proto3에 포함하지 않음 — algorithm 본질은 `cell_v3_2.{py,md}` + `zone_v12.{py,md}`에 self-contained.
- `12_compare.py`는 v11 vs v12 plotting helper로 v11 모듈 의존성 때문에 proto3 환경에서 실행 불가 → 삭제 완료. 시각 결과만 `zone_v12_evolution_g{1,2,3}.png`로 보존.
