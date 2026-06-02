# 006 Step 06 — Target Rules System Tracker

Status: Completed (on `main`, no merge needed — D005 solo-mode)
Type: Step tracker
Branch: `main` (D005 — triggers weak; see Plan header)
Last updated: 2026-06-02

Mirrors `006_Step06_TargetRules_Plan.md` §4 work items (proto3:D016).
Plan = the contract; Tracker = execution state + decisions-during-build.

---

## 1. Plan §4 work items

| # | Work item | Status | Commit |
|---|---|---|---|
| 4.1 | Kickoff — Plan/Tracker + `git mv` Step 05 → `legacy/step05/` + canonical fixes (DoD role↔usage + anchor slot; Arch L90-91) + Progress Tracker | Done | `0126714` |
| 4.2 | `schema/target.py` + `default_min_area_m2` (S06-D1) + tests | Done | `21a2a52` |
| 4.3 | `target/rules_loader.py` (NEW) — `load_target_rules` + strict validation (S06-D4) + tests | Done | `20c1ba7` |
| 4.4 | `target/adapter.py` (NEW) — `TargetAdapter` single generic (S06-D5, **+S06-D6**) + `__init__` + tests | Done | `ddc4e9a` |
| 4.5 | `data/target_rules/apartment.json` + `README.md` (NEW) | Done | `d419655` |
| 4.6 | `target/expand_program.py` (NEW) — `expand_program` (S06-D1/D2/D3) + tests | Done | `619130a` |
| 4.7 | `pyproject.toml` package-data ships `data/target_rules/*` | Done | `4f55e4e` |
| 4.8 | Close — Plan/Tracker + Progress Tracker + S06-D1..D6 finalize (on `main`) | Done | (this) |

---

## 2. Definition of Done checklist

(Plan §1 — checked at close.)

- [x] `TargetRules.default_min_area_m2` added (full Role map) + loader validates
- [x] `rules_loader.load_target_rules` strict validation incl. finite (S06-D4)
- [x] `TargetAdapter` single generic class (S06-D5; no target_type — S06-D6)
- [x] `apartment.json` real values + README 3-layer model + citation-ready provenance
- [x] `expand_program` — area_min from rules, area_target=None, usage=None
- [x] expand output passes stage01_program + stage02_gate (DoD test)
- [x] pyproject ships data/target_rules/* (wheel verified; default path resolves)
- [x] loader / adapter / expand / schema tests pass
- [x] no new viz (justified — non-geometric rules/config layer)
- [x] ruff (check AND format) clean; full pytest green (conda IfcOpenHouse, GEOS 3.14.1) — 730 + 5 xfail
- [ ] Plan/Tracker closed; S06-D1..D6 finalized  ← in progress (4.8)

---

## 3. Notes / decisions during execution

(Filled as work items land — drift from Plan, surprises, sub-decisions.)

- 2026-06-02 — Kickoff. §1/§2 settled over chat (S06-D1..D5). Key chain of
  reasoning: area_min is typology-owned (building standard, not per-call) →
  default_min_area_m2 returns to TargetRules as expand's SEED, NOT a stage01
  fill (S05-D1 intact). area_target meaning stays open (B — no consumer yet).
  role↔usage auto-mapping NOT built (usage=None; field stays for BIM, but
  guessing is harmful). finite checks at JSON loader boundary (resolves S05
  review #7). Confirmed: proto3 target system never touched anchors, and
  host_role is fully wired in Step 02 schema + used in Step 07 — so the DoD
  "anchor host_role slot" line is a kickoff doc-fix, not a work item.
  Staying on `main` (D005 — weak triggers: mostly new files, no golden regen,
  TargetRules field add is non-breaking).
- 2026-06-02 — 4.2 landed. default_min_area_m2 added as a REQUIRED full Role
  map (placed before defaulted min_cardinality — no invalid default). Full-map
  enforced so expand[role] can't KeyError; corridor included (0.0 ok). 5 test
  helpers needed a full map (the field is now mandatory — confirms "no
  half-built TargetRules"). NaN/inf deferred to loader (S06-D4). 697 + 5 xfail.
- 2026-06-02 — 4.3 landed. rules_loader thin: from_dict already rejects
  extra/missing/bad-Role keys + __post_init__ owns domain invariants, so the
  loader adds only file+parse+recursive-finite-check (S06-D4) and re-raises
  domain errors with the path (S06-D2 가, no duplication). 12 tests. 709 + 5.
- 2026-06-02 — 4.4 landed (+ new S06-D6). Surprise: our TargetRules has NO
  target_type field (Step 05 slimmed it out); proto3 had it for load_fixture.
  Traced consumers → NOBODY reads ProgramRequest.target_type to branch (gates
  ignore it; program.py only Literal-checks). So a target_type cross-check is
  speculative → dropped both load_fixture (D5) and the field (D6). Adapter is
  just __init__(rules_path) + target_rules(). expand will stamp the caller's
  target_type onto ProgramRequest directly. 5 tests. 714 + 5 xfail.
- 2026-06-02 — 4.5 landed. apartment.json values sourced via a search-LLM
  (user-run), then VERIFIED against the 33 goldens before accepting: area gate
  admits all 33 (footprints 100-160 m² ≫ min sums ~25-35); cardinality would
  reject 2 abstract test shapes but goldens don't hit that gate → no
  regression. Values are MIN BARRIERS not realistic sizes (user framing).
  private=7.0 Grade-A (Korean statute); public/service/wet Grade-C (intl
  analogue — no Korean per-room min); hub/vc Grade-D estimate. README §2 is
  citation-ready w/ graded sources + verify-before-citing flags + 전용률≠
  density_factor caveat (for the paper). density 0.85 kept (LLM: appropriate
  for an err-loose gate). 4 value-pinning tests. 718 + 5 xfail.
- 2026-06-02 — 4.6 landed. expand_program pure fn, rules injected (가). Field
  policy per D1/D2/D3; target_type stamped (D6, not validated). Invalid roles
  + empty programs NOT re-screened — delegated to SpaceUnitSpec.__post_init__
  / stage01 cardinality (single source of truth). DoD verified: expand output
  passes stage01+stage02 on a real footprint; fails stage01 w/o public. 12
  tests. 730 + 5 xfail. (Multi-typology/intl rules under separate LLM survey
  — house/hotel/office/warehouse may NOT fit the 4-role model; evaluate on
  return, likely data-only adds or deferred, not a 4.x item.)

---

## 4. Close summary

Step 06 (Target rules system) complete on `main` — 7 work items, ~13 commits
(stayed on main per D005, weak triggers). Builds the value+loading half of the
S05-D2 boundary.

**Delivered:**

- `schema/target.py` — `TargetRules` gains `default_min_area_m2` (full Role
  map, S06-D1) — the expand-program seed, NOT a stage01 fill (S05-D1 intact).
- `target/rules_loader.py` (NEW) — `load_target_rules`: thin JSON-boundary
  loader (file/parse/recursive-finite — S06-D4); domain invariants delegated
  to `from_dict` + `TargetRules.__post_init__`, re-raised with path (S06-D2가).
- `target/adapter.py` (NEW) — single generic `TargetAdapter` (S06-D5); no
  `target_type` field/property (S06-D6 — nothing branches on it);
  `DEFAULT_APARTMENT_RULES_PATH`.
- `data/target_rules/apartment.json` + `README.md` (NEW) — real apartment
  values + **citation-ready graded provenance** (private 7.0 = Grade-A Korean
  statute; public/service/wet = Grade-C intl analogue; hub/vc = Grade-D); the
  전용률≠density_factor framing flag; 3-layer extensibility model.
- `target/expand_program.py` (NEW) — `{role:count}` → `ProgramRequest`
  (area_min from rules, area_target/usage None, target_type stamped).
- `pyproject.toml` — package-data ships the JSON+README (wheel verified).

**Decisions:** S06-D1..D6 (Plan §2). New during build: S06-D6 (no `target_type`
on TargetRules/adapter — speculative cross-check dropped, traced no consumer).

**Verification:** 730 passed + 5 xfailed (conda `IfcOpenHouse`, GEOS 3.14.1);
ruff check + format clean. DoD test confirms `expand_program` output passes
`stage01_program` + `stage02_gate`. apartment.json admits all 33 goldens
(cardinality reject of 2 abstract shapes is moot — goldens skip that gate).

**Sourcing note (for the paper):** apartment values came via a search-LLM
survey (user-run), then verified against the 33 goldens before acceptance.
README §2 grades every source A–D and flags Grade-B/C/D as verify-before-
citing. A follow-up survey covers house/hotel/office/warehouse + US/EU/KR —
those typologies may NOT fit the 4-role model (office/warehouse are open-plan;
the binding minimum may be egress/occupancy, not per-room area), so they are
out of Step 06 scope and evaluated on return (likely data-only adds or a
deferred design, not retrofitted here).

**Deferred (Plan §5):** `run()` (Step 07); role↔usage auto-mapping (none —
S06-D3); area_target meaning (S06-D2); anchor/host_role (Step 02 schema +
Step 07 use); non-apartment typologies; L2 strategy plugins; override channel.
