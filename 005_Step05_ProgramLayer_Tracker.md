# 005 Step 05 — Program Layer Port Tracker

Status: Completed (pending no-ff merge to `main`)
Type: Step tracker
Branch: `step05-programlayer`
Last updated: 2026-06-02

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
| 4.7 | `stages/stage02_gate.py` floor-scoped gates (S05-D6 **revised 다**) + tests | Done | `8b75c3c` |
| 4.8 | Generator + 33 golden `input.json` regen (S05-D7); digests asserted unchanged | Done | `4214bb5` |
| 4.9 | Step close — Progress Tracker + Plan/Tracker close + merge --no-ff → main | Not started | — |

---

## 2. Definition of Done checklist

(Plan §1 — checked at close.)

- [x] `area_min_m2` required, `area_target_m2` optional + diffusion-priority docstring, minimal guards
- [x] `schema/target.py` `TargetRules` (3 fields) + re-export + tests
- [x] `ProgramInstantiationFailure` added + round-trips through FailureRecord
- [x] `constraints/gates.py` — 4 gates (3 active + access stub), m units
- [x] `stage01_program` cardinality gate over one floor's specs, returns them unchanged (S05-D8; no ProgramInstance)
- [x] `stage02_gate` fail-only, single-floor (area + dim; multi-floor hoisted to Step 07 — S05-D6 revised)
- [x] gate / stage / failure unit tests pass
- [x] 33 golden `input.json` regenerated; region-id digests verified unchanged
- [x] no new viz (justified — non-geometric admission layer; `src/room_layout/viz/` untouched)
- [x] ruff clean; full pytest green (conda IfcOpenHouse, GEOS 3.14.1) — 690 passed + 5 xfail
- [ ] Plan/Tracker closed; S05-D1..D8 finalized; merged --no-ff  ← in progress (4.9)

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
- 2026-06-02 — 4.7 landed (S05-D6 revised → 다). On reflection stage02 is
  FLOOR-scoped; check_multi_floor_feasibility is BUILDING-scoped (different
  altitude) → hoisted its CALL SITE to Step 07 run() (gate fn itself already
  built+tested in 4.5). stage02 takes one FloorShape, runs area+dim only.
  Tests pin hole-subtraction (net 64 m²) + multi-part union. 689 + 5 xfail.
- 2026-06-02 — Pre-4.8 adversarial review (subagent). Confirmed golden
  independence: per_stage reads input.json's SHAPE only; growth digests come
  from growth_fixture.json — so the 4.8 input regen cannot move digests
  (S05-D7 holds structurally). Review found NO gate-logic bugs; fixed 5
  items (commit c5c06a4): (1) Plan/code contract drift on stage01 [4 spots],
  (2) corridor cardinality trap → reject in TargetRules, (3) private import,
  (4) hardcoded multi-floor data, (5) dim-gate disconnected-bbox docstring.
  Logged-only (not fixed — intended): disconnected-floor dim optimism is the
  aggregate-admission stance (Step 07 does per-part). 690 + 5 xfail.
- 2026-06-02 — 4.8 landed. Regenerated 33 input.json. Order-independent diff
  confirms ONLY area_target_m2 → null (area_min/role/shape identical; key
  order also shifts cosmetically from the 4.2 reorder). S05-D7 guard PASSED:
  690 passed + 5 xfail, byte-identical to pre-regen — digests did not move,
  empirically proving growth is target-agnostic (changing area_target can't
  shift output). PNG sidecars untouched (area-independent). ruff clean.

---

## 4. Close summary

Step 05 (Program layer port) complete on `step05-programlayer` — 18 commits
(8 work items + interleaved tracker/doc + 1 review-response + 1 doc-drift).
Pending no-ff merge to `main` (proto3:D015).

**Delivered:**

- `schema/program.py` — area-field realignment (S05-D1): `area_min_m2`
  required, `area_target_m2` optional (diffusion-priority hook), + minimal
  value guards. Field reorder (defaults last).
- `schema/target.py` (NEW) — `TargetRules` value bundle (S05-D3): 3 fields,
  `corridor` rejected as a cardinality key (review fix).
- `schema/failure.py` — `ProgramInstantiationFailure` (S05-D5), sibling of
  `DomainGateFailure` (not a subclass — pinned by test).
- `constraints/gates.py` (NEW) — 4 pure gates, m units (S05-D4): area / dim /
  multi-floor active + access no-op stub. Injection split: domain scalars as
  kwargs, `list[SpaceUnitSpec]` direct (option 가).
- `stages/stage01_program.py` (NEW) — required-only cardinality gate only
  (S05-D8: structural/cross-ref already owned by `__post_init__` +
  `validate_input`); returns specs unchanged (S05-D5).
- `stages/stage02_gate.py` (NEW) — floor-scoped area + dim orchestration
  (S05-D6 revised → 다: multi-floor gate is building-level, hoisted to
  Step 07). Holes subtracted, m units.
- 33 golden `input.json` regenerated (S05-D7): `area_target` honest-fake →
  null. **Region-id digests unchanged** — the empirical S04-D3
  target-agnostic regression guard passed.

**Decisions:** S05-D1..D8 (Plan §2). New during build: S05-D8 (Stage 01 =
cardinality only), S05-D6 revised (stage02 floor-scoped, multi-floor hoisted).

**Verification:** 690 passed + 5 xfailed under the canonical runtime (conda
`IfcOpenHouse`, GEOS 3.14.1); ruff clean. Pre-4.8 adversarial review (subagent)
found no gate-logic bugs; 5 items fixed (`c5c06a4`). Golden regen verified
order-independent (only `area_target` → null; shape/area_min/role identical).

**Deferred (per Plan §5):** `check_multi_floor_feasibility` call site → Step 07;
per-room post-growth area/dim check (1.5 m² rejection — distinct from this
Step's aggregate admission) → Step 07; `check_access_schema` activation →
Step 09-10; TargetRules JSON loader / adapter / typology values → Step 06;
area-aware growth (consuming `area_target`) → no committed Step.
