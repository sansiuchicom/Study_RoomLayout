# 000 Area-Aware Growth — deferred design note

Status: Deferred design note (post-v1) — captures a Step 07 §4.10 finding
Scope: why realistic programs can grow *invalid* under target-agnostic growth,
the solution space, and the sub-problems any fix must handle
Last updated: 2026-06-03

---

## 0. Purpose

Records a design tension surfaced while building the run() test corpus
(Step 07 §4.10). **Nothing here is implemented in v1** — v1 keeps growth
target-agnostic (S04-D3) and the per-room gate as-is (§4.5). This note exists
so the finding, the solution space, and the sub-problems are not re-discovered
later, and so the eventual fix has a starting point.

Cross-references: `000_Pipeline_Overview.md` §3.6 (growth), §3.8 (labeling);
S04-D3 (growth is target-agnostic); S06-D2 (`area_target_m2` meaning reserved,
no consumer yet); Step 07 §4.5 (per-room gate) / §4.10 (the finding).

---

## 1. The finding

Growth is **target-agnostic** (S04-D3): it fills the floor greedily by per-role
priority and *ignores* `area_target_m2` / `area_min_m2` / `min_dimension_m`.
The per-room gate (§4.5) then rejects any grown room below its own `area_min`.

So a **realistic** program can grow **invalid**. Evidence —
`tests/golden/apt_undersized_room/run.json` (a 9×7 apartment, realistic mins):

```text
room       grew     min    verdict
  bath        7.66    3.0   ok
  living      8.76   12.0   ❌ < min   → ROOM_BELOW_MIN_AREA → valid=False
  bed2       14.27    8.0   ok
  kitchen    15.08    5.0   ok
  bed1       15.08    8.0   ok
```

The living room (public, should be the **largest**) grew to the **second
smallest** — smaller than the kitchen — because greedy growth never prioritised
it. The geometry is sound (a clean tiling); the *proportions* are implausible,
and the area shortfall flips the result invalid. For BIM training data,
implausible proportions (kitchen > living) are themselves a quality problem,
independent of the validity flag.

---

## 2. Root cause

`area_min_m2` conflates **two** concepts, and growth honours **neither**:

| Concept | Meaning | Should be |
|---|---|---|
| absolute usability floor | "below this a room can't serve its function" (≈1.5 m²) | **hard** gate (reject) |
| caller's preferred size | "a living room should be ≥12 m²" | **soft** (preference / growth target) |

The §4.5 gate treats the *preference* as a *hard* reject, while growth (S04-D3)
treats it as nothing. The mismatch is the bug-shaped part: a preference is being
enforced as a constraint the algorithm was never asked to satisfy.

---

## 3. Solution space

| | Approach | Assessment |
|---|---|---|
| **A** | **Area-aware growth** — growth grows rooms *toward* their targets (cap the hub's greed; ensure each room reaches its min) | **The real fix.** BIM training data needs plausible proportions. A substantial change to the validated Cell growth (would re-baseline the goldens) → its own **post-v1 Step**. This is where `area_target_m2` (S06-D2, reserved) finally gets a consumer. |
| **B** | **Two-tier area** — `area_min` becomes soft (a provenance warning); a separate absolute floor (≈1.5 m²) is the only hard reject | Cheap (no growth change) and makes realistic programs valid *now* — but it lets implausible proportions through, so it degrades training-data quality. A **stopgap**, not a fix. |
| **C** | **v1: do nothing** — gate as-is; callers use lenient mins (corpus A uses 0.5) or accept `valid=False` on tight realistic programs | **Current stance.** Keeps Step 07 scope honest — v1's job is "is the geometry correct," not "are proportions plausible." |

Recommendation: **C** for v1; **A** when plausible proportions become a product
requirement. **B** only if a fast unblock is needed before A is scoped.

---

## 4. Sub-problems area-aware growth (A) must handle

Two were raised during the §4.10 discussion — both are open:

### 4.1 Public / living ↔ circulation boundary

In apartments the **living room often doubles as circulation** — there is no
separate hallway; you cross the living room to reach the bedrooms. So a
separately-carved `corridor` polygon adjacent to the hub may be *artificial*:
that area arguably belongs to the living/public space.

In `apt_undersized_room` a corridor was carved **while** the living room fell
below its min. Attributing hub-adjacent circulation to the living room (hub)
— rather than carving it out as a standalone corridor — might **both** improve
realism (no phantom hallway) **and** resolve the area shortfall (the living
room meets its min once its circulation counts toward it). So the corridor-carve
(§3.7) and the per-room area accounting (§4.5) are coupled to this fix, not
independent of it.

### 4.2 Growth priority by area-min risk

A concrete sub-strategy for A: **grow the rooms most at risk of missing their
`area_min` first**, so a constrained room secures its floor before greedy
neighbours absorb the surrounding regions. Today growth orders by role
(hub-first); an area-min-risk-aware order is an additive refinement that could
land before a full area-target growth rewrite.

---

## 5. Why this is deferred (and safe to defer)

- v1 ships **valid geometry**, not plausible proportions — the per-room gate +
  target-agnostic growth are internally consistent for that goal.
- The finding is **golden-locked**: `apt_undersized_room` pins the current
  (invalid) behaviour, so when A lands the golden flips to `valid=True` — a
  visible "fixed it" signal, with no silent drift in between.
- A touches the validated Cell growth algorithm; doing it well needs the
  product requirement (which proportions matter, how much) to be concrete.
  Premature tuning would re-baseline the 33 goldens for a need we cannot yet
  specify (honest-fix / YAGNI).
