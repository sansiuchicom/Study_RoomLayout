# 010 Step 10 — Multi-Floor Orchestrator Tracker

Status: Completed — **merged to `main`** (`382966c`, `--no-ff`, 2026-06-10) after external review response
Type: Step tracker
Branch: `step10-multifloor`
Last updated: 2026-06-08

Companion to `010_Step10_MultiFloor_Plan.md` (proto3:D016). §1 mirrors Plan §4
1:1, adding Status + Commit. §2 mirrors Plan §1 (DoD). §3 records drifts /
sub-decisions (S10-D11+) as work lands.

---

## 1. Plan §4 work items

| # | Work item | Status | Commit |
|---|---|---|---|
| **10.1** | Kickoff — Plan + Tracker (Step 08 docs archived → `legacy/step08/` in `9483640`) | ✅ | `30b68f0` |
| **10.2** | `house.json` typology — `requires_single_floor=false` + `cardinality_scope="building"` + role `min_cardinality`; register; 4-role fit | ✅ | `392fb60` |
| **10.3** | `TargetRules.cardinality_scope` (S10-D13) + building-level role cardinality (S10-D5/D11); apartment `per_floor` byte-identical | ✅ | `3558974` |
| **10.4** | vc vertical continuity (S10-D6) on **emitted vc rooms**; `VERTICAL_CIRCULATION_DISCONTINUOUS` | ✅ | `dda5a39` |
| **10.5** | `run()` restructure (S10-D2) — `_run_floor` + cross-floor **PRE** pass (no POST, #7) | ✅ | `aa8445e` |
| **10.6** | vc-only / growable-less floor **valid** (S10-D12) — `run()` skips growth (never-crashes; prior review #10) | ✅ | `380fb89` |
| **10.7** | Fixtures + goldens — current-RB 3-floor house + forward-compat courtyard + discontinuity; per-floor heights (#9/#10) | ✅ | `487bb04` |
| **10.8** | Viz — per-floor SVG/GIF for house floors (reuse) | ✅ | `81cc0c8` |
| **10.9** | Close — README + Progress + Pipeline sync; ruff + pytest green; `--no-ff` merge | ✅ | `ddfbc38` + merge `382966c` (after external review response) |

---

## 2. Definition of Done checklist (Plan §1)

- ✅ 1. `house.json` (`requires_single_floor=false` + `cardinality_scope="building"`) registered; 4-role fit (role-level, S10-D11) (`392fb60`)
- ✅ 2. `cardinality_scope` field (S10-D13) + building-level role cardinality; apartment `per_floor` byte-identical (`3558974`)
- ✅ 3. vc **vertical** continuity on **emitted vc rooms** (S10-D6, #5); `VERTICAL_CIRCULATION_DISCONTINUOUS`; containment reused (`dda5a39`)
- ✅ 4. `run()` restructured (`_run_floor` + cross-floor **PRE** pass, no POST #7); never-crashes preserved; apartment byte-identical (`aa8445e`)
- ✅ 5. vc-only / growable-less floor **valid** (S10-D12); `run()` skips growth before `program_to_fixture` (never-crashes, prior review #10) (`380fb89`)
- ✅ 6. Fixtures + goldens — current-RB 3F house + forward-compat courtyard + discontinuity; per-floor heights (#9/#10) (`487bb04`)
- ✅ 7. Viz — per-floor SVG/GIF reused for house floors (`81cc0c8`)
- ✅ 8. ruff (check + format) + full pytest green (1020 + 4 xfail, GEOS 3.14.1) + docs synced + apartment goldens byte-identical; **merged `--no-ff`** (`382966c`) after the external review + 12-finding response

---

## 3. Notes / decisions during execution

(Filled as work items land — drifts, surprises, sub-decisions S10-D11+.)

- **Pre-planning spikes (throwaway, `/tmp`):** ran via a **monkeypatch**
  (`_RULES_PATH_BY_TYPE["house"] = /tmp/house.json` with
  `requires_single_floor=false`) — the shipped `run()` only knows apartment and
  blocks multi-floor at the gate (that gap is what 10.2 lands). A 3-floor house →
  `valid=True`, 0 failures, shared stair on all 3 floors; a 3-floor house with a
  2nd-floor courtyard hole → also `valid=True`, rooms grew around the hole.
  Confirmed: geometry is already multi-floor-ready (per-floor loop + anchor
  filtering + all-floor containment); Step 10 = typology + building-level
  validation + fixtures, **not new geometry** (S10 §0).
- **Pre-build external review of the Plan (12 findings) → response:** 3 became
  decisions — **S10-D11** (cardinality role-level, no usage guarantee; #3),
  **S10-D12** (vc-only/growable-less floor valid + `program_to_fixture`
  never-crashes; #8 — closes the latent prior-review #10), **S10-D13**
  (`TargetRules.cardinality_scope` field, not `requires_single_floor`; #4). 7
  were doc fixes: spike conditions stated (#1); "last *capability* piece, live
  plug-in = Step 09" (#2); continuity redefined on **emitted vc rooms** +
  **vertical-only**, horizontal access deferred (#5/#6); PRE-only, no vague
  "completeness" POST (#7); fixtures split current-RB vs forward-compat (#9);
  per-floor height required when multi-floor (#10). Verified #5 (`vc_rooms` is
  spec-gated) + #8 (building cardinality makes the no-growable `ValueError`
  reachable) in code before accepting.
- **10.2 — house cardinality uses `public`, not `hub`.** The 33-case corpus +
  apartment.json use `public` for living rooms (`hub` appears 0× in the corpus —
  it is a growth-internal "first public room" concept, mapped from `public`).
  So `house.json` `min_cardinality` = `{public, private, wet}:1` (apartment's
  vocabulary, building-scope) — *not* the `hub` the throwaway spike used. house
  area map is house-tuned (public 12 / private 8 / wet 3) but **provisional**
  (a graded-provenance sourcing pass, like apartment's, is a later task).
- **Work-order evolution (10.3→10.6):** the S10-D2 cross-floor **PRE pass**
  landed *incrementally* — building cardinality (10.3) and vc continuity (10.4)
  were added inline to `run()` directly, so 10.5's remaining piece is only the
  `_run_floor` *extraction* (a pure readability refactor, no behavior change).
  10.6 was pulled **before** 10.5 because 10.3 made the `program_to_fixture`
  no-growable `ValueError` **reachable** (verified live: a vc-only floor crashed
  `run()` with `floor 2 has no growable rooms`) — a never-crashes regression
  that had to be closed immediately, not after a cosmetic refactor.
- **Post-implementation external review (12 findings) → response:** 2 code fixes
  — **#1** (real bug: a vc-only floor short-circuited growth but never emitted
  its `labeling` stage, so the debug JSON/SVG dropped it; now emits — `2444472`)
  + **#11** (stale `NO_TARGET_RULES` "apartment only" message — now lists shipped
  typologies). 1 test — **#7** (the area-digest golden can't see geometry, so a
  direct invariant test: vc==anchor, no overlaps, courtyard void — `eb12c99`).
  4 doc fixes — **#2** (`program_to_fixture` is **not** itself graceful; `run()`
  skips a growable-less floor before calling it — wording corrected across
  Plan/Tracker), **#8** (`cardinality_scope` added to the target-rules README
  field table; house values flagged provisional), **#9** (`expand_program`
  docstring: single-floor only, multi-floor allocation is the caller's job),
  **#10** (this DoD/§1 vs README/Progress consistency). 5 documented as
  deliberate / pre-existing in `docs/000_multifloor_access.md`: **#3**
  (role-level cardinality, already S10-D11), **#4** (continuity is a universal
  multi-floor invariant, not a typology rule), **#5** (no non-occupied-floor
  concept — ResearchBIM doesn't send one), **#6** (continuity is PRE on specs by
  design), **#12** (pre-existing loose anchor-aware area gate). That note also
  captures the **stair / entrance / public access-model** discussion (the
  access root differs by floor; the entrance is a future fixed-input like an
  anchor). The 70 full-suite fails the reviewer saw are the GEOS 3.13.1-vs-pinned
  golden mismatch (#1's env), not a regression (1018 pass at 3.14.1).

---

## 4. Close summary

Step 10 (Multi-floor orchestrator) complete on `step10-multifloor` — 9 work
items — the **house** target (first multi-floor typology). Post-v1 capability
(Pipeline §5.2); apartment (single-floor) stays **byte-identical** throughout.

**The key framing held (§0):** multi-floor is mostly *not new geometry* — the
per-floor pipeline already worked (verified by a 3-floor + courtyard spike). The
real work was the cross-floor / building-level concerns + the typology:

**Delivered:**
- `house.json` typology + `TargetRules.cardinality_scope` field (S10-D3/D13);
  registered. `public`/`private`/`wet` role cardinality (corpus vocabulary).
- **Building-level cardinality** (S10-D5): `run()` branches on `cardinality_scope`
  — a house counts `min_cardinality` over all floors, so living/kitchen on 1F +
  bedrooms above is valid. `per_floor` (apartment) unchanged.
- **vc vertical continuity** (`constraints/multi_floor.py`, S10-D6): union-find
  over occupied levels on **emitted** vc rooms (spec-gated, #5); vertical-only
  (#6). `VERTICAL_CIRCULATION_DISCONTINUOUS` on an isolated floor / partial-core
  gap.
- **vc-only / empty floor never-crashes** (S10-D12): a growable-less floor emits
  just its fixed vc rooms — closing the `program_to_fixture` `ValueError` path
  that building cardinality made reachable (prior review #10; verified live).
- **`run()` restructure** (S10-D2): per-floor body extracted to `_run_floor`;
  `run()` = cross-floor PRE pass (cardinality + continuity) → per-floor loop.
- **Multi-floor goldens** (`test_golden_house.py`): current-RB 3-floor +
  forward-compat courtyard + discontinuity injection. Multi-floor requires
  per-floor height (`MULTI_FLOOR_HEIGHT_REQUIRED`, #10).
- **Per-floor viz** reused as-is for the house floors (S10-D10).

**ResearchBIM alignment (S10-D8/D9):** the input model maps 1:1 from the
consumer's `Building`/`Storey`/`Footprint`/`Core` (same m/CCW/centerline);
fixtures are authored *as* Building translations. The **live adapter is Step 09**
(deferred until ResearchBIM's footprint passing lands).

**Decisions:** S10-D1..D10 (planning) + **S10-D11/D12/D13** (from a pre-build
external review of the Plan — role-level cardinality + usage caveat; vc-only
floor valid + never-crashes; `cardinality_scope` field). 7 further plan doc
fixes from the same review (§3 review-response note). Verified #5 + #8 in code
before accepting.

**Not done (deliberate):** the live ResearchBIM adapter (Step 09); auto program
allocation; hotel/office typologies; a stacked multi-floor SVG sheet; full
horizontal access topology (deferred v1-wide). Step 10 docs archive at the next
Step's kickoff (proto3:D016 H011).
