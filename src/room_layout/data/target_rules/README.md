# Target rules — values, provenance, and extensibility

This directory holds **per-typology domain rule files** consumed by
`room_layout.target.rules_loader.load_target_rules` and surfaced through
`room_layout.target.TargetAdapter`. Each `<typology>.json` populates a
`room_layout.schema.TargetRules` instance.

JSON does not support comments, so this README is the canonical place for
**field-by-field rationale, source provenance, and the extensibility model**.

> **For the paper / academic use**: §2 (Provenance) is the citation-ready
> record. Sources are graded — see the **Source grade** column. Grade-A
> (primary statute/code) figures are defensible as-is; Grade-B/C (secondary,
> international-analogue, or estimate) figures are flagged as
> **verify-before-citing** and should be replaced with a primary source
> before publication. We deliberately do not present secondary-sourced
> numbers as if they were primary (honest-fix discipline).

---

## 0. File ↔ typology convention

The **filename is the typology identifier** (`apartment.json` → the apartment
typology). The JSON body carries **no `target_type` field** — it maps 1:1 onto
`TargetRules`'s fields (`density_factor`, `requires_single_floor`,
`default_min_area_m2`, `min_cardinality`). A `target_type` key in the JSON
would be rejected by `from_dict` as an extra key (S06-D6 — nothing downstream
reads `target_type` to branch, so `TargetRules` does not carry it; the caller
of `expand_program` stamps the typology onto the resulting `ProgramRequest`).

---

## 1. Fields (schema)

| Field | Type | Meaning |
|---|---|---|
| `density_factor` | float in (0, 1] | usable-area fraction of the gross footprint. The area gate's capacity is `footprint_area_m2 × density_factor`. |
| `requires_single_floor` | bool | typology forbids multi-floor layouts; the multi-floor gate fails when set and the building has ≠ 1 floor. |
| `default_min_area_m2` | dict[Role, float] | **full Role map** — per-role minimum-barrier area. The seed `expand_program` reads to fill `SpaceUnitSpec.area_min_m2`. Not a stage01 fill fallback (S05-D1). |
| `min_cardinality` | dict[Role, int] | minimum required count per Role for the typology to be valid. Required-only (proto3:D023). Sparse (unlisted roles = 0). |

---

## 2. Provenance — `apartment.json`

**Framing (critical).** `default_min_area_m2` values are **minimum
feasibility barriers**, *not* typical/realistic room sizes: "below this area
the space cannot function as that category at all." They are intentionally the
smallest defensible floor per role, used by the pre-growth admission gate
(`check_min_area`: Σ required role minimums ≤ footprint × density_factor), not
a design target. (The user-facing "preferred size" notion is the separate,
currently-unused `area_target_m2` field — S06-D2.)

### 2.1 `default_min_area_m2` (m²)

| Role | Value | Source grade | Basis | Caveat |
|---|---:|:---:|---|---|
| `private` (침실/방) | **7.0** | **A — primary statute** | 주택법 시행령 (Housing Act Enforcement Decree) §10①1 라목: each bedroom in a 도시형생활주택/소형주택 unit (전용 ≥ 30 m²) must be ≥ 7 m²; MOLIT describes it as "최소한의 주거여건" (minimum living condition). | Statutory 7 m² is scoped to 도시형생활주택/소형주택 bedrooms, **not** all apartment types — Korean code regulates the *unit as a whole* + bedroom *count*, not every room's area. Used here as the most defensible proxy for any enclosed `private` room. |
| `public` (거실) | **9.0** | C — international analogue | No Korean per-room minimum for 거실 exists. Cross-code floor: Italy MRS / India NBC habitable room ≥ 9–9.5 m²; Ontario OBC habitable room ≥ 9.5 m². | Grade-C: no Korean statutory anchor. Verify against a Korean source or domestic design guideline before citing. |
| `service` (주방/다용도) | **4.0** | C — international analogue | Ontario OBC kitchen ≥ 4.2 m²; Italy ≥ 4–5 m²; India NBC ≥ 4.5–5.5 m². Korean MRS 2011 requires a private kitchen for ≥ 2-person households but specifies **no area**. | Grade-C: physical floor (~1.8 m × 2.2 m counter + circulation), not Korean statute. Verify before citing. |
| `wet` (욕실/화장실) | **2.5** | C — fixture-clearance estimate | A functioning 욕실 (washbasin + toilet + shower) is minimally ~1.5 m × 1.6 m ≈ 2.4 m², rounded to 2.5; cf. India NBC combined WC+bath ≥ 2.8 m², toilet-only ≥ 1.1 m². | Grade-C: derived from fixture clearances, no Korean statutory per-WC area. Verify before citing. |
| `hub` | **2.0** | D — engine estimate | No code basis. A hub is a circulation node, not a habitable room; a small positive floor keeps it from collapsing. proto3 used 2.0. | Grade-D: internal heuristic. Not a building-code figure. |
| `corridor` | **0.0** | D — by definition | Corridors are produced by carving, not admitted as program rooms; a minimum barrier is meaningless. 0.0. | n/a |
| `vertical_circulation` | **2.0** | D — engine estimate | Stair/elevator core minimum footprint ≈ 2 m². Anchor-bound (S04-D4), not grown. | Grade-D: estimate; refine against 건축법 stair-core minimums if it ever drives a decision. |

### 2.2 `density_factor` = **0.85**

| Aspect | Detail |
|---|---|
| Value | 0.85 (85% of the footprint can become room area; 15% lost to internal walls + circulation) |
| Source grade | B — derived from industry efficiency ranges |
| Basis | Korean RC 벽식구조 unit interior efficiency (net room area ÷ 전용면적) ≈ 80–88%; international residential base-building efficiency 75–85%. 0.85 sits at the loose end. |
| Why loose | The admission gate should **err loose** (admit more, reject only the clearly impossible) so it does not wrongly reject viable programs. A higher density_factor = larger capacity = fewer false rejects. |
| **Framing flag** | 0.85 is **NOT** the Korean 전용률 (75–80%). 전용률 = 전용면적 ÷ 공급면적 (includes the unit's share of shared stairs/elevator) — one boundary coarser than ours. Our `density_factor` is *within-unit* (room area ÷ footprint). Do **not** substitute 전용률 figures for it. |
| Sensitivity | Conservative/accurate ≈ 0.80; admission-gate (err loose) = 0.85; max permissible ≈ 0.88. |

### 2.3 `min_cardinality` = `{public: 1, private: 1, wet: 1}`

A minimal valid apartment has at least one living space, one bedroom, and one
bathroom. Source grade B (conventional dwelling definition; matches proto3).
Required-only (proto3:D023): optional spaces don't satisfy it. Grade-B, not a
single statutory citation — the Korean MRS mandates a minimum *bedroom count*
by household size but not this exact triple.

### 2.4 `requires_single_floor` = `true`

v1 lays out one floor (D001); multi-floor orchestration is Step 10. For the
apartment-unit typology, single-floor is also the common physical case.

### 2.5 Internal consistency check

A minimal 3-person Korean apartment (~36 m² total, MRS 2011) as
1 bedroom (7) + living (9) + kitchen (4) + bath (2.5) = **22.5 m²** of room
area, leaving ~13.5 m² for walls/hallway/second bedroom — plausible, so the
barriers are not mutually contradictory at the smallest real unit size.

### 2.6 Validation against the 33 golden cases

With these values, the area gate (`check_min_area`) **admits all 33** Cell
showcase footprints (Σ required minimums ≪ footprint × 0.85 in every case —
the goldens are 100–160 m² footprints vs. ~25–35 m² minimum sums). The
`min_cardinality` triple would reject 2 of the 33 (`case_24`, `case_27`) for
lacking a `public` room — but those are **abstract geometry test shapes (2
rooms each), not apartment programs**, and the goldens are never run through
the cardinality gate (it applies to `expand_program` output, not to the raw
fixture inputs). So the values introduce no golden regression. (Verified
2026-06-02 during 4.5.)

---

## 3. 3-layer typology extensibility model (proto3:D022)

Typology knowledge is separated into three layers:

```
┌──────────────────────────────────────────────────────────────┐
│ L0 — Engine invariant  (Python core, typology-agnostic)       │
│   atomize / regionize / growth / corridor carving / gates.    │
│   Same code for every typology.                               │
├──────────────────────────────────────────────────────────────┤
│ L1 — Parameters        (this directory's JSON files)          │
│   density_factor, default_min_area_m2, min_cardinality,       │
│   requires_single_floor. New typology = a JSON file (+ a      │
│   default-path registry entry when one exists).               │
├──────────────────────────────────────────────────────────────┤
│ L2 — Strategy plugins  (future, Python — typology-agnostic)   │
│   When a typology needs a genuinely different algorithm       │
│   variant (e.g. hotel "explicit corridor"), it becomes a      │
│   strategy function selected by a JSON enum. Strategies are   │
│   typology-agnostic by design. Not present today; added when  │
│   first needed.                                               │
└──────────────────────────────────────────────────────────────┘
```

**Consequence**: a single concrete `TargetAdapter` drives all typologies
(no `ApartmentAdapter` / `HotelAdapter` subclasses — S06-D5). Adding a
typology that shares all algorithms is a **data-only** change: author
`<typology>.json` here.

**Mission scope** (deliberate discipline): this engine generates room layouts
inside enclosed building footprints (apartment / house / hotel / office /
warehouse). It does **not** extend to bridges, transit stations, or outdoor
master planning — different missions, different engines.
