# 010 Step 10 — Multi-Floor Orchestrator Tracker

Status: In progress (on `step10-multifloor`)
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
| **10.5** | `run()` restructure (S10-D2) — `_run_floor` + cross-floor **PRE** pass (no POST, #7) | ☐ | — |
| **10.6** | vc-only / growable-less floor **valid** (S10-D12) — `program_to_fixture` graceful (never-crashes; prior review #10) | ☐ | — |
| **10.7** | Fixtures + goldens — current-RB 3-floor house + forward-compat courtyard + discontinuity; per-floor heights (#9/#10) | ☐ | — |
| **10.8** | Viz — per-floor SVG/GIF for house floors (reuse) | ☐ | — |
| **10.9** | Close — README + Progress + Pipeline sync; ruff + pytest green; `--no-ff` merge | ☐ | — |

---

## 2. Definition of Done checklist (Plan §1)

- ✅ 1. `house.json` (`requires_single_floor=false` + `cardinality_scope="building"`) registered; 4-role fit (role-level, S10-D11) (`392fb60`)
- ✅ 2. `cardinality_scope` field (S10-D13) + building-level role cardinality; apartment `per_floor` byte-identical (`3558974`)
- ✅ 3. vc **vertical** continuity on **emitted vc rooms** (S10-D6, #5); `VERTICAL_CIRCULATION_DISCONTINUOUS`; containment reused (`dda5a39`)
- ☐ 4. `run()` restructured (`_run_floor` + cross-floor **PRE** pass, no POST #7); never-crashes preserved; apartment byte-identical
- ☐ 5. vc-only / growable-less floor **valid** (S10-D12); `program_to_fixture` graceful (never-crashes, prior review #10)
- ☐ 6. Fixtures + goldens — current-RB 3F house + forward-compat courtyard + discontinuity; per-floor heights (#9/#10)
- ☐ 7. Viz — per-floor SVG/GIF reused for house floors
- ☐ 8. ruff (check + format) + full pytest green; apartment goldens byte-identical; merged `--no-ff`

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
- _(more as work lands)_
