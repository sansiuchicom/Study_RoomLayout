# 000 Typology ↔ Gate Applicability

Type: Design note (not a Step) + paper appendix
Status: Reference. v1 implements the apartment row only; everything else is a
documented future-extension input, deliberately not built.
Last updated: 2026-06-02

---

## 0. Purpose

This note records **why the v1 admission gate (a per-role minimum-area check)
is a residential instrument**, what the *real* binding feasibility constraint
is for each building typology, and which future extensions that implies. It
exists so that the apartment-shaped decisions in `data/target_rules/` are not
silently over-generalized to typologies they do not fit.

Evidence base: two search-LLM surveys (2026-06-02) grounded in building
codes/standards, plus a consolidation pass that audited their sources. The
**sources are graded** (§6) — several are secondary (blog/forum/video) and are
flagged *verify-before-citing*. This note does **not** present heuristic or
secondary-sourced numbers as if they were primary law (honest-fix discipline).

What this note is **not**: a decision to build hotel/office/warehouse support.
v1's mission is the apartment unit (all 33 golden cases are apartments). House
shares the residential gate; the rest are future work (§4) with no committed
Step.

Cross-references: `data/target_rules/README.md` §2 (apartment value
provenance — the narrow "what value, what source" record; this note is the
wide "why the gate model itself"); `docs/000_Progress_Tracker.md` §5 (known
issues / accepted limitations); `docs/000_Architecture_Decisions.md` D004
(the 7-class `Role` taxonomy this note critiques).

---

## 1. The 4-role model is residential-biased

The pipeline classifies rooms by a coarse functional `Role`
(`public` / `private` / `wet` / `service` / `hub` / `corridor` /
`vertical_circulation`, D004). That taxonomy was designed around the
**apartment unit** — "living / bedrooms / bathroom / kitchen + circulation."
It maps cleanly onto dwellings and progressively worse onto non-dwellings:

| Typology | 4-role fit | Why |
|---|:---:|---|
| **apartment** | ✅ clean | The taxonomy was built for it. living=public, bedroom=private, bath=wet, kitchen=service. |
| **house** (detached) | ✅ clean | Same residential decomposition; only cardinality differs (an open-plan house may omit a dedicated `public` room). |
| **hotel** | ⚠️ remap | `private`=guestroom, `wet`=en-suite, `public`=lobby/common — but `service` is **back-of-house** (kitchen/laundry/plant) that guests never occupy and is sized as a % of total area, not a room minimum. |
| **office** | ❌ poor | An office is open work-floor + meeting rooms + shared WCs + pantry. "public/private" is a forced fit for open-area vs enclosed-room; shared WCs are not per-room. |
| **warehouse** | ❌ wrong | A warehouse is essentially one large storage hall (often > 85% of area) + a small ancillary office + a WC. The storage hall has no meaningful per-room *area minimum* at all. |

The deeper point: `Role` encodes a **dwelling's functional decomposition**.
Non-dwellings have different primitives (open work-floor, storage hall,
back-of-house) that the 7-class enum does not name. Forcing them into the
enum produces categories that exist syntactically but carry no real
feasibility meaning.

---

## 2. The real binding constraint per typology

The admission gate asks "can this program physically fit this floor?" For a
dwelling the binding answer is **per-room minimum area**. For other typologies
the binding constraint is something else entirely — and a per-room area gate
either does nothing useful or actively measures the wrong thing.

| Typology | v1 gate (area-min) | The *real* binding constraint | Is area-min the right tool? |
|---|---|---|---|
| **apartment / house** | Σ required role min ≤ footprint × density | per-room minimum area + total dwelling area (dwelling standards are dwelling-level first) | ✅ Yes — for dwellings, room area is genuinely the feasibility axis. |
| **hotel** | (forced) | guestroom gross area (incl. en-suite); public/BOH sized as **% of total GFA** (~10–20% public, ~15% BOH) | ⚠️ Partial — guestroom area is real; a universal "lobby ≥ X m²" or "BOH ≥ X m²" minimum is **not** statutory in the reviewed sources (program-dependent). |
| **office** | (forced) | **occupant load** — IBC ~14 m²/person (open office) drives egress width + toilet-fixture count (OSHA Table J-1, by employee count) | ❌ No — a 200 m² floor passes any room-area gate yet may violate egress for 40 occupants. The right gate is `usable_area / 14 m² ≥ headcount`, not room area. |
| **warehouse** | (forced) | **clear height** + **column/bay spacing** + **dock-door count** (~1 door / 930 m²) + floor-load rating; typology threshold itself (SCDF: a store > 100 m² *is* a warehouse) | ❌ No — the storage hall has no per-room area minimum; height/dock/load are the constraints. |

**Alternative gate formulas (for the future, not built):**
- office: `floor_usable_m2 / occupant_load_factor ≥ required_headcount`
  (occupant_load_factor ≈ 14 m²/person open office; tighter for dense plans).
- warehouse: `clear_height ≥ required` AND `dock_doors ≥ ceil(area / 930 m²)`.
- hotel: guestroom-area gate per room + public/BOH as a fraction of total GFA.

---

## 3. Wet rooms & toilets: area is the wrong axis

The `wet` role deserves a separate flag because its v1 area minimum (2.5 m²)
is the **weakest-grounded** of the four, and for non-dwellings it is measuring
the wrong quantity:

- **Accessibility is geometric, not area-based.** US ADA toilet-room guidance
  explicitly states the standards do **not specify a toilet-room area**;
  compliance is fixture clearances + a turning space (e.g. a 60-inch circle) +
  door-maneuvering clearance. A single "≥ 2.5 m²" threshold cannot express
  that — an accessible single-user WC needs ~4.6 m² *of the right shape*.
- **Workplace provision is headcount-based.** US OSHA (1910.141, Table J-1)
  sets the **number** of water closets by employee count (1 for 1–15, 2 for
  16–35, …), not a room area. Korean site standards similarly key toilet count
  to worker count.

**Implication for our value.** `wet = 2.5 m²` is defensible only as a
*non-accessible, residential* feasibility barrier (the smallest space that can
physically hold toilet + basin + shower entry). It is **not** a code minimum,
and it does not generalize to hotel/office/warehouse, where the binding rules
are accessibility geometry and fixture count. A future `strict_mode` should
swap the area check for a geometry/fixture-count check wherever accessibility
or workforce rules apply.

---

## 4. Future extension paths

All three are **deliberately not built** (YAGNI — v1 has no non-apartment test
input). Recorded here with their trigger so the future reader knows the shape.

### 4a. Gate polymorphism / `strict_mode`
Let the admission gate vary by typology instead of always being area-min:
office → occupancy gate, warehouse → clear-height/dock gate, accessible wet →
geometry gate. The current single `check_min_area` + `check_min_dim` becomes
one strategy among several (an L2 strategy plugin in the 3-layer model,
`data/target_rules/README.md` §3).
- **Why not now**: no office/warehouse input exists to validate against;
  building occupancy/egress modeling is a large subsystem.
- **Trigger**: first real non-residential target is scoped, OR accessibility
  (ADA-equivalent) becomes a requirement.

### 4b. Typology-specific role model
The 7-class `Role` is residential (§1). A real office/warehouse model needs
different primitives (`open_floor`, `storage_hall`, `back_of_house`, …). This
is a schema-level change (`Role` is the single source of truth for the whole
pipeline, D004), so it is expensive and pervasive.
- **Why not now**: changing `Role` ripples through every stage + all goldens;
  no demonstrated need (apartment/house fit the existing enum).
- **Trigger**: a typology whose primitives genuinely cannot be expressed as the
  7 roles is committed.

### 4c. Program presets (higher-level input templates)
Today the caller supplies room counts explicitly (`expand_program(counts)`).
A preset layer ("a 30-pyeong apartment ≈ 3 bedrooms + 2 baths + LDK") would
let a caller pick a template instead of enumerating counts. This is **purely
additive input sugar above `expand_program`** — it does not touch the gates.
- **Why not now**: explicit counts are more honest for v1; presets need real
  typical-program data to be meaningful (and that data is market survey, not
  code). The room *count* a user wants is already an input channel
  (`counts`); only the *preset templates* are missing.
- **Trigger**: a UX/integration need for "pick a template" emerges.

---

## 5. Korea-source honesty note (for the paper)

The apartment values lean on Korean framing but the **Korean statutory base is
thinner than a per-room table suggests** — important to state honestly in any
publication:

- **Korean minimum residential standards are dwelling-level, not per-room.**
  The 최저주거기준 (MRS) regime sets a minimum *total* dwelling area by
  household size (e.g. ~14 m² single, ~26–36 m² couple/family) + a minimum
  *bedroom count* + the requirement for self-contained kitchen/toilet — **not**
  a standalone minimum area for every living room / kitchen / bathroom.
- **`private = 7.0 m²` is narrowly scoped.** The 7 m² bedroom minimum
  (주택법 시행령 §10①1 라목) applies to **도시형생활주택 / 소형주택** bedroom
  sub-units (전용 ≥ 30 m²), **not** to all apartment types. It is the only
  per-room area minimum in the reviewed Korean law, so we use it as the most
  defensible *proxy* for an enclosed `private` room — but it is a proxy, and
  its grade is therefore **B**, not A (downgraded after the consolidation
  review; the README is amended to match).
- **`public` / `service` have no Korean per-room minimum at all.** Their values
  rest on international analogues (England NDSS, US IRC habitable-room, Ontario
  OBC, Italian municipal kitchen norms) — Grade C.
- **Primary Korean statute text was not fully retrievable** in the surveys; the
  Korean regime is anchored here through an official Legislative-Council
  comparative research note + secondary Korean legal summaries. Before citing
  in the paper, replace these with the primary 주택법 / 주택건설기준 /
  주거기본법 text.
- **`density_factor` is a modeling conversion, not a legal number.** It is the
  ratio of usable room area to the given footprint; no reviewed primary source
  defines exactly that ratio. Korean 전용률 (75–80%) is a *different* boundary
  (전용 ÷ 공급, includes shared core) and must not be substituted.

---

## 6. Citation-ready source table (graded)

Grades: **A** = primary law/regulation/official standard directly applicable;
**B** = official institutional guidance or original paper (authoritative but
not directly binding for the exact use-case); **C** = comparative official
source / strong analogue; **D** = reasoned estimate (no applicable primary
minimum verified). Only the strong, *actually-relied-on* sources are listed;
the surveys also cited many blog/forum/Scribd/YouTube items that are
**brainstorming-grade only — verify before citing**.

| Source | Grade | Supports | Limitation |
|---|:---:|---|---|
| GOV.UK — *Technical housing standards: nationally described space standard* (NDSS) | A | English dwelling minima (single bedroom 7.5 m², double 11.5 m²); whole-dwelling-first principle | English, not Korean; explicitly warns bedroom minima not be used in isolation. |
| 주택법 시행령 §10①1 라목 (Housing Act Enforcement Decree) | A (narrow) | `private` 7.0 m² proxy | Scoped to 도시형생활주택/소형주택 bedrooms, not all apartments. |
| 최저주거기준 (MRS) regime / Legislative-Council comparative note | A→via-secondary | Korea is dwelling-level (total area + bedroom count + facilities) | Primary statute text not fully retrieved; anchored via official research summary. |
| US Access Board — *Guide to the ADA Standards: Toilet Rooms* | A | Toilet rooms are **geometry**-governed, not area-governed | US accessibility; reframes `wet` away from a single area number. |
| US OSHA 1910.141 (Table J-1) | A | Workplace toilet **count** by employee number | US workplace sanitation; relevant to office/warehouse, not dwelling. |
| Hotelstars Union — *Classification Criteria* | A (industry-official) | Hotels regulated by services/amenities + per-room shower/WC; **no universal lobby-area minimum** | EU hotel classification, not a building code. |
| SCDF — *Appendix D, General Warehouses* | A (SG) | Warehouse typology threshold (store > 100 m² = warehouse); height/dock/compartment logic | Singapore fire code; typology recognition, not KR/US/UK planning. |
| US IRC §R304 (habitable room ≥ ~6.5 m²) | A | Floor for `public`/`private` cross-check | US residential model code; section text not fully extractable in survey. |
| Ontario OBC (kitchen ≥ 4.2 m², habitable ≥ 9.5 m²) | C | `service` / `public` analogue | Provincial Canadian; analogue only. |
| UNM *Building Efficiency Ratio Guidelines* / US DoD WBDG *Net-to-Gross* | B | `density_factor` framing (office 60–72%; net/gross is a modeling conversion) | Institutional benchmarks, not code; used to justify density as a parameter. |
| CTBUH — *Space Efficiency in Multi-Use Tall Buildings* | B | Hotel/stacked-core efficiency losses (→ lower hotel density_factor) | Research paper; tall-building context. |

**Numeric takeaways the strong sources support** (loose-barrier mode — smallest
defensible minimum across jurisdictions, since a barrier must not over-reject):
private 7.0–7.5 m², public 6.5–9 m², kitchen 4–5 m², wet has **no** code area
minimum (geometry/fixture-count instead). Office/warehouse: area-min is the
wrong gate.

---

## 7. Relationship to current code

- The code implements **only the apartment/house row of §2** — the per-role
  area-min gate (`constraints/gates.py`, `data/target_rules/apartment.json`).
- hotel/office/warehouse `<typology>.json` files are **deliberately not
  created**: filling a 4-role area table for them would manufacture a gate that
  *looks* authoritative but measures the wrong constraint (§2). That is exactly
  the kind of "looks-real, means-nothing" value the project removes elsewhere
  (cf. the dropped `area_target` placeholder, S05-D1). Honest-fix: no fake gate.
- house *could* be added as a data-only `house.json` (it fits the gate, S06-D5)
  but its values are near-identical to apartment and there is no house test
  case, so it is not added in v1.
- See `docs/000_Progress_Tracker.md` §5 for the running known-issues/limitations
  list this note backs.
