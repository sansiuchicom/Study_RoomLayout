# Target rules — defaults and provenance

Per-Target domain rule files consumed by `proto3.target.rules_loader`.
Loaded by each `*Adapter(rules_path=...)` constructor (Plan S06-D4, D5).

JSON does not support comments; this README is the canonical place for
field-by-field rationale + source citations + override policy.

---

## apartment.json (Target A)

Defaults used by `ApartmentAdapter` for Stage 02 Domain Feasibility Gate
(Step 06). Engine vs data separation: proto3 code reads this file, never
embeds the values inline (Plan S06-D17).

### Sources

- **Layer A — 인체공학 (anthropometric / ergonomic)**
  - Neufert, *Architects' Data* 4th ed. — bedroom 7–8 m², living 12–18 m²
  - Panero & Zelnik, *Human Dimension and Interior Space*
- **Layer B — 법규 / 규범 (legal / normative)**
  - 「최저주거기준」 (국토교통부, 「주거기본법」 §17)
  - 「주택건설기준 등에 관한 규정」 (대통령령)
  - 공동주택 설계 가이드라인 (LH / SH 표준 평면)
- **Layer D — proto3 invariants**
  - D005 "constraints-as-gates, fail loud"
  - Stage 02 = "obvious impossibility 만 차단" (Pipeline §9.10)

### Field-by-field rationale

| Field | Value | Rationale |
|---|---:|---|
| `density_factor` | 0.85 | proto3 footprint = 한 세대 외곽선이라 코어/공용복도는 footprint 밖. 한국 아파트 전용률 (0.7–0.75) 그대로 쓰면 over-discount. 세대 내부 효율 = 외벽 ~5% + 세대내 동선 ~10% ≈ 15% 깎음 → 0.85 |
| `requires_single_floor` | `true` | apartment unit = single floor (D003) |
| `min_cardinality.public` | 1 | living/거실 1개 이상 (D004) |
| `min_cardinality.private` | 1 | 침실 1개 이상 (D004) |
| `min_cardinality.wet` | 1 | 화장실 1개 이상 (D004 / DH-004 regression rule) |
| `default_min_area_m2.public` | 12.0 | Neufert 12–18; 한국 거실 통념 12 m² |
| `default_min_area_m2.service` | 5.0 | 「주택건설기준」 부엌 4–6 lower |
| `default_min_area_m2.private` | 7.0 | Neufert 7–8; 「최저주거기준」 single bedroom 7 m² |
| `default_min_area_m2.wet` | 3.0 | 공동주택 설계기준 욕실 2.4–3 m² |
| `default_min_area_m2.hub` | 2.0 | entry / foyer rule of thumb |
| `default_min_area_m2.corridor` | 0.0 | corridor area 는 spine generation (Stage 09) 책임 |

### External overrides

External callers (e.g., scan-to-BIM training pipeline) override by:

1. **Copy** this file as a base.
2. **Edit** fields as needed (whole-file swap; partial merge intentionally
   not supported — Plan S06-D17).
3. **Pass** the new path: `ApartmentAdapter(rules_path=external_path)`.

Subsequent runs use only the new file — the proto3 default is not consulted.
This guarantees external runs are self-contained: drift / hidden-fallback
problems do not exist.

### Future work (Plan §5 Def-1 ~ Def-3)

- Partial override merge — only when a concrete external pipeline use case
  demands it (currently: whole-file swap covers all needs).
- Maintenance against 「최저주거기준」 revisions / non-Korean typologies as
  Target B/C/D/E adapters are added.
- Sensitivity ablation (`density_factor`, `default_min_area_m2`) for the
  Automation in Construction paper supplementary.
