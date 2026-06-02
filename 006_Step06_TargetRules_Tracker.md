# 006 Step 06 — Target Rules System Tracker

Status: Active
Type: Step tracker
Branch: `main` (D005 — triggers weak; see Plan header)
Last updated: 2026-06-02

Mirrors `006_Step06_TargetRules_Plan.md` §4 work items (proto3:D016).
Plan = the contract; Tracker = execution state + decisions-during-build.

---

## 1. Plan §4 work items

| # | Work item | Status | Commit |
|---|---|---|---|
| 4.1 | Kickoff — Plan/Tracker + `git mv` Step 05 → `legacy/step05/` + canonical fixes (DoD role↔usage + anchor slot; Arch L90-91) + Progress Tracker | In progress | — |
| 4.2 | `schema/target.py` + `default_min_area_m2` (S06-D1) + tests | Not started | — |
| 4.3 | `target/rules_loader.py` (NEW) — `load_target_rules` + strict validation (S06-D4) + tests | Not started | — |
| 4.4 | `target/adapter.py` (NEW) — `TargetAdapter` single generic (S06-D5) + `__init__` + tests | Not started | — |
| 4.5 | `data/target_rules/apartment.json` + `README.md` (NEW) | Not started | — |
| 4.6 | `target/expand_program.py` (NEW) — `expand_program` (S06-D1/D2/D3) + tests | Not started | — |
| 4.7 | `pyproject.toml` package-data ships `data/target_rules/*` | Not started | — |
| 4.8 | Close — Plan/Tracker + Progress Tracker + S06-D1..D5 finalize (on `main`) | Not started | — |

---

## 2. Definition of Done checklist

(Plan §1 — checked at close.)

- [ ] `TargetRules.default_min_area_m2` added (full Role map) + loader validates
- [ ] `rules_loader.load_target_rules` strict validation incl. finite (S06-D4)
- [ ] `TargetAdapter` single generic class (S06-D5)
- [ ] `apartment.json` real values + README 3-layer model
- [ ] `expand_program` — area_min from rules, area_target=None, usage=None
- [ ] expand output passes stage01_program + stage02_gate
- [ ] pyproject ships data/target_rules/* (default path resolves)
- [ ] loader / adapter / expand / schema tests pass
- [ ] no new viz (justified — non-geometric)
- [ ] ruff (check AND format) clean; full pytest green (conda IfcOpenHouse, GEOS 3.14.1)
- [ ] Plan/Tracker closed; S06-D1..D5 finalized

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

---

## 4. Close summary

(Filled at 4.8.)
