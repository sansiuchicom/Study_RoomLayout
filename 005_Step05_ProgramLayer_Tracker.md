# 005 Step 05 — Program Layer Port Tracker

Status: Active
Type: Step tracker
Branch: `step05-programlayer`
Last updated: 2026-05-30

Mirrors `005_Step05_ProgramLayer_Plan.md` §4 work items (proto3:D016).
Plan = the contract; Tracker = execution state + decisions-during-build.

---

## 1. Plan §4 work items

| # | Work item | Status | Commit |
|---|---|---|---|
| 4.1 | Plan + Tracker land + `git mv` Step 04 docs → `legacy/step04/` + Progress Tracker stale-text cleanup | Done | `31205d0` |
| 4.1b | Doc-drift fixes from external review (stale Step 11/14 refs, README, `__init__`) | Done | `59ed170` |
| 4.2 | `schema/program.py` area-field realignment (S05-D1) + schema/serialize tests | Done | `15fc806` |
| 4.3 | `schema/target.py` `TargetRules` (S05-D3) + `__init__` re-export + tests | Done | `79ced8d` |
| 4.4 | `schema/failure.py` `ProgramInstantiationFailure` (S05-D5) + tests | Done | `b7d6405` |
| 4.5 | `constraints/gates.py` 4 pure gates (S05-D4) + tests | Done | `06a2db3` |
| 4.6 | `stages/stage01_program.py` cardinality gate (S05-D5, **+S05-D8**) + tests | Done | `0a006a0` |
| 4.7 | `stages/stage02_gate.py` fail-only orchestration (S05-D6) + tests | Not started | — |
| 4.8 | Generator + 33 golden `input.json` regen (S05-D7); digests asserted unchanged | Not started | — |
| 4.9 | Step close — Progress Tracker + Plan/Tracker close + merge --no-ff → main | Not started | — |

---

## 2. Definition of Done checklist

(Plan §1 — checked at close.)

- [ ] `area_min_m2` required, `area_target_m2` optional + diffusion-priority docstring, minimal guards
- [ ] `schema/target.py` `TargetRules` (3 fields) + re-export + tests
- [ ] `ProgramInstantiationFailure` added + round-trips through FailureRecord
- [ ] `constraints/gates.py` — 4 gates (3 active + access stub), m units
- [ ] `stage01_program` validates + returns input unchanged (no ProgramInstance)
- [ ] `stage02_gate` fail-only, single-floor, 3 active gates
- [ ] gate / stage / failure unit tests pass
- [ ] 33 golden `input.json` regenerated; region-id digests verified unchanged
- [ ] no new viz (justified — non-geometric layer)
- [ ] ruff clean; full pytest green (conda IfcOpenHouse, GEOS 3.14.1)
- [ ] Plan/Tracker closed; S05-D1..D7 finalized; merged --no-ff

---

## 3. Notes / decisions during execution

(Filled as work items land — drift from Plan, surprises, sub-decisions.)

- 2026-05-30 — Kickoff. §1/§2 settled over chat (area-field realignment +
  Step05/06 type-value boundary). Scan confirmed all 33 golden inputs
  already carry valid `area_min_m2` → required promotion needs no backfill;
  the only golden change is `area_target_m2` 25.0-placeholder → null.
  Discovery: current `area_target` values are an honest fake
  (`footprint/num_rooms`, uniform per case) — regen drops them (S05-D1/D7).
- 2026-05-30 — External review triaged (chat). Real finds were all doc
  drift: Plan referenced non-existent Step 11/14 (map ends at 10) →
  reworded area-aware growth as a no-committed-Step future pass, multi-floor
  → Step 10; README + `__init__` staleness. Rest were time-of-review
  confusion (Step 05 not yet built) or intended defers (S04-D3/D4). One
  reasonable find folded into 4.2: empty-id / negative-dim guards.
- 2026-06-02 — 4.2 landed. area_min_m2 required, area_target_m2 optional +
  field reorder + 4 minimal guards. Field reorder is kwargs-safe (all
  construction sites use keywords; serialize is field-name based). Goldens
  still validate as-is (area_target present & ≥ min) — they only *change* at
  4.8 regen, they don't *break* now. 649 passed + 5 xfail; ruff clean.
- 2026-06-02 — 4.3 landed. schema/target.py TargetRules (3 fields). New
  file, zero ripple. Confirmed serialize already round-trips dict[Role,int]
  (no serialize change needed). Re-exported at both __init__ levels (note:
  top-level room_layout/__init__ has its OWN export list — must edit both,
  not just schema/__init__). 659 passed + 5 xfail; ruff clean.
- 2026-06-02 — 4.4 landed. ProgramInstantiationFailure as a sibling (가)
  of DomainGateFailure — pinned `not isinstance(_, DomainGateFailure)` so
  the feasibility-catch can't swallow an input-validation failure. 661
  passed + 5 xfail; ruff clean.
- 2026-06-02 — 4.5 landed. constraints/gates.py — 4 pure gates (3 active +
  access no-op stub), m units. Injection split confirmed in code: domain
  scalars as kwargs, list[SpaceUnitSpec] direct (가). FailureRecord mapped
  proto3's failure_type/evidence → our code/data. 14 tests cover pass +
  each fail branch + D023 required-only + None-skip. 675 passed + 5 xfail.
- 2026-06-02 — 4.6 landed (+ new decision S05-D8). Discovery: validate_input
  (Step 02) ALREADY checks duplicate spec id cross-floor + __post_init__
  guards empty/invalid id+role — so proto3's Stage 01 structural re-checks
  would duplicate existing layers. stage01_program.run owns ONLY the
  rules-based required-only cardinality gate, returns specs unchanged
  (S05-D5 identity). Dropped a speculative run_program() wrapper (no caller
  yet — YAGNI). 7 tests. 682 passed + 5 xfail; ruff clean.

---

## 4. Close summary

(Filled at 4.9.)
