# Target rules — defaults, provenance, extensibility

This directory holds **per-typology domain rule files** consumed by
`proto3.target.rules_loader.load_target_rules`. Each file is loaded by
`TargetAdapter(rules_path=...)` at construction time.

JSON does not support comments; this README is the canonical place for
field-by-field rationale, source citations, override policy, and the
**extensibility model** that defines how new typologies enter proto3.

---

## proto3 mission scope (out-of-scope reminder)

proto3 generates **room layouts inside enclosed building footprints**. The
adapter pattern below extends the same mission across building typologies
— apartment, house, hotel, warehouse, office. It does **not** extend to:

- **Bridges, viaducts, retaining walls** — structural / civil engineering.
- **Subway platforms, train stations** — transit-oriented spatial planning
  with platform / track / egress / fire-safety constraints.
- **Outdoor master planning** — urban grid, parcels, landscape.

These are different missions and need different engines. This is a
deliberate scope discipline (Plan §0); over-generalization would dilute
the engine quality across the actual mission.

---

## 3-layer typology extensibility model

proto3 separates typology knowledge into **three layers**:

```
┌──────────────────────────────────────────────────────────────┐
│ L0 — Engine invariant  (Python core, typology-agnostic)      │
│   spine generation, region/atom decomposition, atom growth,  │
│   repair. Same code for every typology.                      │
├──────────────────────────────────────────────────────────────┤
│ L1 — Parameters        (this directory's JSON files)         │
│   density_factor, default_min_area_m2, min_cardinality,      │
│   single-floor flag, future enum strategy selectors.         │
│   New typology = JSON file + 1-line dispatch table entry.    │
├──────────────────────────────────────────────────────────────┤
│ L2 — Strategy plugins  (future, Python — typology-agnostic)  │
│   When a typology needs a genuinely different algorithm      │
│   variant (e.g., hotel "explicit corridor" pattern), it      │
│   becomes a strategy function in a registry. JSON enum       │
│   selects which one. Strategies are typology-agnostic by     │
│   design — a single explicit-corridor function can be used   │
│   by hotel + large office + any future typology that fits.   │
│   Not present today; introduced when first needed.           │
└──────────────────────────────────────────────────────────────┘
```

**Important consequence**: a single concrete `TargetAdapter` class drives
all typologies. Per-typology subclasses (`ApartmentAdapter`,
`HotelAdapter`, ...) are **deliberately absent**. The typology identity
lives in the JSON's `target_type` field, not in a class name.

### Why this design (rationale)

- proto3 is the *engine* component of an external scan-to-BIM training
  data generation pipeline. Engines that ship data separately scale to
  new typologies without code changes — like a game engine that loads
  level data, or a renderer that loads scene files.
- New-typology cost is bounded: data-only when algorithms match, plus
  one strategy function when they don't. Either way, no per-typology
  class boilerplate.
- Ablation / parameter sweep is data-level. The Automation in Construction
  paper supplementary can attach this directory verbatim.
- External pipelines override by passing their own `rules_path` — proto3
  code is not modified for project-specific tuning.

---

## Adding a new typology — workflow

### Case 1: parameter-only (algorithms unchanged)

Most additions of a typology that fits the apartment-style algorithm
(e.g., a `house` adapter that just has different cardinality / area
defaults) are **data-only**:

1. Author `<typology>.json` here, including the `target_type` field.
2. Register a default rules path in
   `proto3.stages.stage00_load._DEFAULT_ADAPTERS` (one line).
3. (Already done in schema if the typology is in `TargetType` Literal.)

No new class. No `target/<typology>.py` module. No `__init__.py` export.

### Case 2: logic-different (new algorithm needed)

If the typology genuinely needs a different algorithm variant — e.g., a
hotel needs an explicit-corridor + repeated-room layout that apartment's
host-absorbed spine cannot express — the workflow is:

1. Add a strategy function to the appropriate registry (e.g.,
   `proto3.strategy.spine.SPINE_STRATEGIES`). Strategy functions are
   typology-agnostic — name them by what they do, not by which typology
   uses them.
2. Add a new enum field on the typology's JSON selecting the strategy
   (e.g., `"spine_strategy": "explicit-corridor"`).
3. (Steps 1–2 from Case 1 if also new.)

The L2 strategy registry does not exist yet — it will be introduced
during Step 09 (Spine Generation) when apartment ships its first
strategy. Adding hotel later may or may not require new strategies; the
test will be whether `host-absorbed` covers it.

### External pipeline override

External callers (e.g., scan-to-BIM training pipeline) override by:

1. **Copy** an existing JSON as a base.
2. **Edit** fields as needed — whole-file swap; partial merge intentionally
   not supported (Plan S06-D17). External rules files are self-contained,
   so future proto3 default changes do not silently affect external runs.
3. **Pass** the new path: `TargetAdapter(rules_path=external_path)`.

Subsequent runs use only the new file — proto3 default is not consulted.

---

## apartment.json (Target A) — field-by-field rationale

Defaults used by `TargetAdapter(DEFAULT_APARTMENT_RULES_PATH)` for Stage 02
Domain Feasibility Gate (Step 06). Engine vs data separation: proto3 code
reads this file, never embeds the values inline (Plan S06-D17, D22).

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
| `target_type` | `"apartment"` | Self-describing: identifies which typology this rules file is for. Matched against fixture `target_type` at load time |
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

### Future work (Plan §5 Def-1 ~ Def-3)

- **Partial override merge** — only when a concrete external pipeline use
  case demands it (currently: whole-file swap covers all needs).
- **Maintenance** against 「최저주거기준」 revisions / non-Korean
  typologies as Target B/C/D/E adapters are added.
- **Sensitivity ablation** (`density_factor`, `default_min_area_m2`) for
  the Automation in Construction paper supplementary.
- **L2 strategy registry** — introduced during Step 09 (Spine Generation)
  when first-pass apartment strategy lands. Hotel/warehouse adapters
  added during Plan Def-10 reuse it for typology-specific algorithm
  variants.
