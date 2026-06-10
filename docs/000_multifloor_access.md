# Multi-floor access model — design note (post-Step 10)

Status: Deferred design note (not built). Captures the multi-floor **access**
discussion + the Step 10 review findings that resolve into "documented
limitation / future layer" rather than a v1 fix.

Context: Step 10 made `run()` multi-floor for the **house** target. It models
the *vertical* connection (vc continuity, S10-D6) but **not** the per-floor
*access topology* — which `run()` has never validated (`check_access_schema`
is a no-op, `LabeledRoom.doors=None`; Pipeline §2.4). Multi-floor makes that
gap visible, so it is written down here.

---

## 1. The question — stair / entrance / public are three different things

On a single floor (apartment), the "hub" = the first **public** room (D004);
corridor carving routes rooms back to it. That conflates two ideas that
multi-floor pulls apart:

| concept | what it is | where it is the access root |
|---|---|---|
| **entrance** (입구) | the *building* access point (an exterior door) | ground floor |
| **vertical_circulation** (stair / elevator) | *vertical* access between floors | every **upper** floor (you arrive from below) |
| **public** (living) | a *program* room | only coincidentally — it often sits at the ground-floor entrance |

So the **access root differs by floor**: ground = entrance, upper = stair. The
current "hub = first public room" has no answer for an upper bedroom floor (no
public room there) — today such floors simply tile without a routed corridor
(small programs) and access is never checked.

Observed: the Step 10 `house` goldens' upper floors carry **0 corridor
polygons** — the 2–3 rooms tile and touch the boundary / stair directly, so
nothing forces a routed access path. It "works" only because the programs are
small.

## 2. The model (proposed, not built)

1. **Per-floor access root, role-aware** (near-term, the smallest useful step):
   the circulation hub on a floor = the **public** room if present, else the
   **vertical_circulation** (stair). This lets a large upper floor route its
   corridor to the stair landing instead of having no hub. A `growth` / carve
   change (the `hub_room_index` selection), not new schema.
2. **`entrance` as a first-class concept** (mid-term): the building access root
   on the ground floor. room_layout has no `entrance` today; **ResearchBIM
   models it** (`Room(usage="entry")`). Cleanest fit: receive the entrance as a
   **fixed-position input like a `VerticalAnchor`** — the caller (ResearchBIM
   Stage 4) already places both the core (stair) and the entry, so room_layout
   would take both as fixed anchors and grow around them (extends the S04-D4
   anchor model; aligns with S10-D8/D9).
3. **Validated reachability** (the big layer): "every room reachable from this
   floor's access root", doors on the room↔room / room↔corridor graph. This is
   the deferred access topology (`check_access_schema` no-op, `doors=None`) —
   v1-wide deferral, not multi-floor-specific.

**Floor order:** floors are processed independently today; the shared stair
**anchor** gives cross-floor XY consistency, so order does not matter. A richer
model ("ground floor establishes the entrance/root → upper floors reference it")
would make ground-first matter — but only once the entrance/root is derived
rather than caller-supplied.

## 3. Step 10 review findings folded in here (documented, not fixed)

- **#4 — vc continuity is hard-coded in `run()`, not a target rule.** Deliberate:
  vertical continuity is a *universal* multi-floor invariant (a building whose
  floors don't connect is meaningless), so it is not typology-specific. It is
  vacuous for a single floor (apartment untouched). Revisit only if a real
  typology wants disconnected floors (none does).
- **#5 — every `shape.floors` level is treated as occupied + vc-requiring.**
  True. There is no "non-occupied floor" concept (roof / void / mechanical /
  pure structural slab), so such a floor with no vc spec reads as discontinuous.
  Not a blocker today: ResearchBIM models the roof as a `Storey` *attribute*
  (`roof_surfaces`), not a separate occupiable storey, so the consumer never
  sends one. A `non_occupied` floor flag is a future extension when a typology
  needs it.
- **#6 — continuity is computed from PRE-stage specs, not final emitted rooms.**
  Deliberate: continuity validates the *program's* vc topology before layout.
  If a floor's geometry then fails independently, that is reported by its own
  geometry `FailureRecord` (the run stays `valid=False`); continuity does not
  re-derive from output (which would re-introduce the POST pass dropped at the
  plan review #7). The precision cost is small and the verdict is still correct.
- **#12 — anchor-aware area admission is loose.** Pre-existing (Step 05): the
  per-floor area gate uses *gross* footprint capacity, but growth runs on the
  anchor-subtracted floor, so a small floor with a large core is admitted
  optimistically. Multi-floor / stairs surface it more. A fix (subtract anchor
  area from capacity) risks the `apt_anchored_core` golden — deferred as a
  separate area-gate refinement.
- **#3 — role-level cardinality can't force a specific usage** (a kitchen-less
  "house" passes `wet ≥ 1` on a bathroom alone): already the documented S10-D11
  decision (usage is a caller pass-through, S06-D3); usage-level cardinality is
  a separate future mechanism. Not re-opened here.

## 4. Recommendation

None of the above blocks the Step 10 merge (house works; apartment
byte-identical). The smallest *valuable* next step is **§2.1 (stair-as-hub on
hubless floors)** — relevant once a house floor is large enough to need a routed
corridor. The `entrance` concept + validated reachability ride with the broader
access-topology work (and the Step 09 ResearchBIM adapter, which supplies the
entrance). Recorded here so it is found, not re-discovered.

---

## 5. Cross-floor consistency vs directionality (what's shared, what's per-floor)

A stair is the one element that is **both vertical and horizontal**, and the two
split cleanly:

| property | scope | enforced today? |
|---|---|---|
| **footprint** (the XY box) | **shared** — a vertical shaft has the same XY on every floor | ✅ `_check_anchor_footprint_containment` (anchor ⊆ every floor in its `floor_range`) |
| **access / opening / door** (which edge connects to the floor; what it opens into — `public` on 1F, a `corridor` on 2F) | **per-floor** — free to differ | ❌ not modeled (`LabeledRoom.doors=None`) — so "the 1F and 2F entry directions differ" is *un-modeled, hence consistent*, not broken |

So a stair whose landing faces different sides on different floors (normal for
real buildings) is **fine** — the only cross-floor constraint room_layout
imposes (shared footprint) is satisfied, and the per-floor direction lives in the
deferred **door** layer. When doors land, each floor's vc room carries its own
door; the anchor stays shared.

The "direction" is therefore not a new concept to invent — it **is a door**. The
stair-opening = a door (vc room → landing); the entrance = a door (outside →
foyer). Both are the deferred access/door layer.

## 6. Feasibility for synthetic-BIM generation (objective)

The consumer (`ResearchBIM_synthetic-bim`) generates synthetic BIM for ML
training. Two facts make the access/stair layer tractable:

1. **Synthetic ≠ buildable.** The goal is *plausible* topology + geometry, not a
   constructible building. So the real-stair constraint "a switchback's landing
   side is fixed by its flights" does **not** have to be honored — a plausible
   door (facing the interior) is enough. room_layout never models stair
   internals (flights / treads / risers); it only places the **footprint**.
2. **Stair internals + doors are downstream (ResearchBIM), not room_layout.** The
   consumer's pipeline is S1 massing → S3 walls → **S4 room layout (= this repo)**
   → S6 doors → IfcStair. So the door/landing and the IfcStair geometry are
   ResearchBIM stages *after* room layout. room_layout's job ends at the 2D
   partition + footprints.

Two implementation paths for the per-floor stair door (when it is ever needed):
- **(A) caller-provided** — ResearchBIM (which owns the stair model) passes the
  landing edge per floor; room_layout does a lookup. Cleanest; needs the contract
  to carry it.
- **(B) heuristic** — room_layout picks the stair-footprint edge facing the most
  open / circulation space on that floor. Pure geometry, ignores stair type; fine
  for synthetic data.

**The one genuine tension — pipeline order.** "Carve corridors to the stair"
(§2.1) needs the stair door *before* layout, but ResearchBIM decides doors at S6
*after* layout. Resolve at the Step 09 contract: either decide the stair landing
earlier (path A, an input to room layout) **or** don't route corridors to the
stair in room_layout at all (path B / leave it to S6). Small floors never hit
this (rooms tile without a corridor); it only bites on large hubless floors.

## 7. Non-rectangular cores are free

room_layout never assumes a `VerticalAnchor.footprint_polygon` is a rectangle —
it is a shapely `Polygon` end to end (`subtract_anchors` = polygon difference;
`vc_rooms` = the polygon as-is; `area_m2 = polygon.area`). **Verified** by a
throwaway spike: an L-shaped (ㄱ자, non-convex, 5 m²) stair core ran a 2-floor
house `valid=True`, the vc room equalled the L exactly, growth tiled around the
L-hole with no overlap, and it rendered. So L / T / U / any simple-polygon core
costs **zero** work — the same reason footprint holes / donuts already work. A
pathological core that splits the floor degrades *gracefully* (a disconnected
room → `ROOM_DISCONNECTED` `GeometryFailure` → `valid=False`, never a crash). The
core's *door* is still the deferred access layer (an L has 6 edges, so "which
edge is the landing" is even more a door question — ResearchBIM's, §6).
