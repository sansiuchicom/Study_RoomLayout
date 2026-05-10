# 000 Architecture Decisions

Status: Canonical decision record  
Scope: accepted proto3 architecture decisions, invariant vs replaceable choices, and decision history appendix  
Last updated: 2026-05-08

---

## 0. Purpose

This document records accepted decisions for proto3.

Use this file to answer:

- What has already been decided?
- What is an architecture invariant?
- What is only a first-pass implementation choice?
- Why was the decision made?
- What should be changed only with deliberate review?

Canonical framework and pipeline definitions live in `000_Pipeline_Overview.md`. Current implementation status lives in `000_Progress_Tracker.md`.

---

# 1. Decision status labels

| Status | Meaning |
|---|---|
| **Accepted** | Current working decision. Use unless explicitly revised. |
| **Replaceable** | Current first-pass choice, but not a framework invariant. |
| **Deferred** | Known issue or future decision, not required immediately. |
| **Rejected** | Decision considered and intentionally not used. |

---

# 2. Architecture invariants vs replaceable choices

This distinction matters.

Architecture invariants define proto3 itself. Replaceable choices are initial implementation defaults.

| Category | Examples |
|---|---|
| Architecture invariant | spine-first search schema, region/atom dual layer, floor-rooted access, domain constraints as gates, failure-to-pruning backtracking |
| Replaceable implementation choice | greedy multi-source growth, specific atom size defaults, reflex-cut decomposition first pass, SVG implementation library |

Changing an invariant changes the framework. Changing a replaceable choice should not require rewriting the framework.

---

# 3. Accepted decisions

## D001. Use separate Step, Stage, Search Orchestrator, Cross-cutting Infrastructure, and Target concepts

Status: Accepted  
Type: Architecture invariant

Definitions:

| Term | Meaning |
|---|---|
| Step | Development roadmap unit. |
| Stage | Runtime candidate pipeline unit. |
| Search Orchestrator | Control loop outside the Stage pipeline. |
| Cross-cutting Infrastructure | Shared systems such as provenance, visualization, debug output, no-good store. |
| Target | Typology/domain adapter. |

Decision:

- Step and Stage must not be treated as the same thing.
- Candidate Search is not a Stage.
- Provenance, visualization, debug output, run config, and no-good records are cross-cutting infrastructure.

Reason:

The old model blurred implementation order, runtime pipeline, and search orchestration. This made it unclear whether candidate search was a Stage or a system-level loop. The current distinction keeps the architecture implementable.

---

## D002. Use 000 global docs and 001–014 Step docs

Status: Accepted  
Type: Documentation / repo convention

Decision:

- `000_*` files are global docs.
- Step 00 does not exist.
- Implementation Step files use prefixes `001` through `014`.
- Step number in prose uses two digits, e.g. Step 05.
- File prefix uses three digits, e.g. `005_Step05_GeometryKernel_Plan.md`.

Root global docs:

```text
000_Pipeline_Overview.md
000_Architecture_Decisions.md
000_Progress_Tracker.md
000_User_Profile.md
```

Step-specific files are created only when actively working on that Step and may move to `legacy/stepXX/` after completion.

Reason:

The previous `010`, `020`, `140` style required mental mapping between file prefix and Step number. Direct `001`–`014` naming is simpler.

---

## D003. Use apartment-first implementation, but floor-rooted architecture

Status: Accepted  
Type: Architecture invariant

Decision:

- The first Target is Apartment Unit.
- Core architecture must remain floor-rooted, not apartment-core.
- Core schema must support `BuildingInput`, `FloorInput`, floor roots, and empty persistent anchor fields from the beginning.

Reason:

Apartment layouts are the best first implementation target, but the framework should later support multi-floor houses, hotel floors, warehouses, and offices without rewriting core types.

---

## D004. Treat ProgramInstance as the source of cardinality

Status: Accepted  
Type: Architecture invariant

Decision:

- `ProgramInstance` decides required space counts.
- `ClusterSpec` groups already-instantiated spaces.
- Cluster does not create or guarantee cardinality.

Reason:

Relying on clusters or usage fallback can recreate failures such as required bathrooms disappearing. Cardinality must be explicit before clustering, spine generation, seed placement, or growth.

Regression rule:

> A required apartment bathroom count of zero is a ProgramInstantiationFailure, not a growth failure.

---

## D005. Domain constraints are gates, not role scores

Status: Accepted  
Type: Architecture invariant

Decision:

- Domain constraints must be first-class gates and validations.
- Role scoring is preference only.

Hard domain gates include:

- required cardinality,
- minimum area,
- minimum dimension,
- required access validity,
- required door-capable boundary,
- no overlaps,
- inside footprint,
- persistent anchors preserved.

Soft domain constraints include:

- preferred area ratio,
- preferred aspect ratio,
- exterior contact preference,
- wet/service proximity,
- compactness / rectangularity.

Reason:

The previous BSP/R1 failures were not caused by weak vocabulary alone. They came from domain rules not being enforced as first-class constraints.

---

## D006. Use a region/atom dual layer

Status: Accepted  
Type: Architecture invariant
Amended by: [D019](#d019-per-family-proportional-atom-sizing-d006-amendment) (2026-05-08) — atom shape + sizing policy revised.

Decision:

- Region is the coarse architectural territory layer.
- Atom is the fine geometric growth layer.
- Both are required.

Reason:

Region-only is too rigid. Atom-only lacks architectural meaning and can turn the problem into unstructured pixel growth. The dual layer separates intent from growth mechanics.

Initial atom defaults are first-pass commitments, not universal laws:

| Item | Initial default |
|---|---:|
| Internal coordinate unit | millimeter |
| Default layout atom size | 600mm nominal side |
| Minimum atom side | 300mm |
| Tiny atom area threshold | 0.18㎡ |
| Door-capable shared boundary | 800mm minimum |
| Preferred door boundary | 900mm or more |

Step 05 Geometry Kernel must confirm or revise these defaults before serious decomposition and growth work.

---

## D007. Use floor-rooted spine-first candidate search

Status: Accepted  
Type: Architecture invariant

Decision:

The core search schema is spine-first:

```text
floor root
→ hub
→ trunk / branch / stub spine
→ branch slots
→ seeds
→ atom growth
```

The system should form access/spine hypotheses before growing rooms.

Reason:

Previous approaches pushed too many decisions into growth. The spine-first schema gives access, clustering, and attachment structure before atom assignment.

Important:

The spine is not necessarily a corridor. It may become hall, living access host, explicit corridor, stair landing, warehouse aisle, hotel corridor, or another Target-specific access carrier.

---

## D008. Candidate Search is not Stage 14

Status: Accepted  
Type: Architecture invariant

Decision:

Candidate Search is the Search Orchestrator around Stage 00–13.

It is responsible for:

- candidate pool,
- retry ladder,
- no-good records,
- search budget,
- penalties,
- deciding where to resume.

Reason:

A Stage transforms one candidate. Candidate Search manages many candidates and repeated execution of the Stage pipeline. Treating it as a Stage makes the model ambiguous.

Canonical sentence:

> Candidate Search is not a pipeline Stage. It is the control loop that repeatedly runs Stage 00–13, updates no-good records, and decides which earlier Stage to revisit.

---

## D009. Use pre-repair and post-repair validation

Status: Accepted  
Type: Architecture invariant

Decision:

The final runtime pipeline uses:

```text
Stage 10 Atom Growth
→ Stage 11 Pre-repair Validation / Defect Detection
→ Stage 12 Repair / Rectangularization
→ Stage 13 Post-repair Validation / Failure Diagnosis / Output Assembly
```

Reason:

Repair should be defect-directed. If validation only happens after repair, it becomes unclear what repair was supposed to fix and whether repair introduced new failures.

Required distinction:

- Pre-repair validation identifies defects and repairability.
- Repair modifies geometry using a defect report.
- Post-repair validation checks whether the candidate is valid and whether repair caused regressions.

Stage 13 must assemble both valid and invalid candidate outputs. Invalid outputs must still include FailureRecords, provenance, and debug artifacts.

---

## D010. Use failure-to-pruning backtracking

Status: Accepted  
Type: Architecture invariant

Decision:

Failure-directed retry must update future search.

Every meaningful failure should produce at least one of:

- rejected candidate,
- rejected pattern,
- soft penalty,
- required invariant update,
- retry-level escalation,
- no-good record.

Reason:

Retry labels such as “seed retry or spine retry” are too vague. A failure becomes useful only when evidence identifies what should be avoided or protected next.

---

## D011. Use access-preserving atom growth as the invariant

Status: Accepted  
Type: Architecture invariant with replaceable first-pass algorithm

Decision:

The framework requires **access-preserving atom growth**, not greedy growth specifically.

Growth must:

- assign atoms to SpaceUnits,
- preserve required access/parent boundary conditions,
- respect hard domain constraints,
- preserve provenance of growth decisions,
- produce validation evidence.

First-pass implementation choice:

> Use greedy multi-source priority growth initially.

Status of greedy growth:

- Replaceable.
- Suitable for first implementation and debugging.
- Not a framework invariant.

Possible replacements:

- beam search growth,
- staged growth by priority,
- min-cost assignment + repair,
- hybrid methods.

---

## D012. Start with dataclasses for schema

Status: Accepted  
Type: Replaceable implementation choice

Decision:

Start with Python dataclasses, type hints, and explicit serialization helpers.

Do not start with pydantic unless validation or JSON schema needs become painful.

Minimum schema stubs should include:

```text
BuildingInput
FloorInput
RunConfig
PersistentAnchor
ProgramInstance
SpaceUnitSpec
ClusterSpec
AccessPolicy
Region
RegionSet
Atom
AtomSet
ContactGraph
HubCandidate
TerminalCandidate
SpineCandidate
SlotCandidate
SeedCandidate
GrowthResult
LayoutCandidate
ValidationResult
FailureRecord
NoGoodRecord
DebugArtifact
```

Reason:

The data model needs shape immediately. Deferring this as “dataclass vs pydantic” would let later Steps define incompatible fields.

---

## D013. Use SVG-first visualization

Status: Accepted  
Type: Replaceable implementation choice

Decision:

Use an SVG-first renderer for debug visualization.

Reason:

Layout debugging needs polygon overlays, stable layer order, readable labels, and browser-friendly outputs. SVG is a better default than ad-hoc plots for this use case.

Initial visual requirements:

- one shared renderer,
- stable layer order,
- stable visual vocabulary,
- each major Stage can emit SVG overlays.

Initial layer order:

1. footprint boundary,
2. persistent anchors,
3. regions,
4. atoms,
5. graph edges,
6. role scores / heatmap,
7. spine / access tree,
8. slots,
9. seeds / patches,
10. grown spaces,
11. door candidates,
12. validation / failure overlay.

---

## D014. Keep debug outputs out of version control by default

Status: Accepted  
Type: Repo convention

Decision:

Generated debug outputs should not be committed by default.

Initial `.gitignore` policy:

```gitignore
__pycache__/
*.pyc
.venv/
.env

outputs/debug_runs/*
!outputs/debug_runs/.gitkeep

outputs/notebooks/*
!outputs/notebooks/.gitkeep

experiments/runs/*
!experiments/runs/.gitkeep

.cache/
.pytest_cache/
.mypy_cache/
.ruff_cache/

.DS_Store
```

Reason:

proto3 will generate many JSON/SVG debug artifacts. Keeping them tracked by default would quickly pollute the repo.

---

## D015. Per-Step branch + per-work-item commit + no-squash merge

Status: Accepted
Type: Repo / VCS convention

Decision:

For Step-level (or larger Stage-level) work:

- **Start**: checkout a new branch (e.g., `step02-core-schema`).
- **During**: commit each completed work item separately. Plan §4 work-item granularity defines commit granularity by default. Design commit boundaries during Plan-time, not after.
- **Judgment exception**: very simple/small work may stay on `main` directly.
- **Finish**: merge with `git merge --no-ff` (no squash). Then delete the branch (`git branch -d <branch>`).
- **Commit message**: prefix-style 1~2 lines, e.g. `git commit -m "feat: 제목, 간단한 내용"`. Common prefixes: `feat`, `fix`, `refactor`, `docs`, `chore`.

Reason:

- Squash discards per-commit history. Failure-to-pruning ([D010](000_Architecture_Decisions.md)) and provenance ([Pipeline Overview §12.1](000_Pipeline_Overview.md)) work better when each commit corresponds to a Plan §4 work item — diagnosing "when did this break" is easier with per-commit history aligned to plan items.
- Per-Step branch makes work-in-progress visible without cluttering main, while merge --no-ff preserves the Step's commit cluster as a reviewable unit.
- The Plan §4 ↔ commit mapping makes automated execution and code review easier.

Step 01 was an exception: this convention was decided mid-Step-01, so Step 01 was bundled into a single `feat: step01 project skeleton` commit on `main` (see Step 01 Plan / Tracker for details). Step 02 onward applies D015 from the start.

---

## D016. Per-Step companion docs: Plan + Tracker

Status: Accepted
Type: Documentation / repo convention

Decision:

Each implementation Step has two companion documents at the repo root:

- **`NNN_StepNN_<name>_Plan.md`** — living decision doc + work specification. Updated during discussion, frozen once decided. Detailed enough that an automated executor can run from it without consulting other files.
- **`NNN_StepNN_<name>_Tracker.md`** — progress log + checklist. Updated continuously while working.

Plan section structure (followed by Step 01):

- §0 Purpose (with cross-references)
- §1 Definition of Done (with verification commands)
- §2 결정 기록 (decision table; per-Step decision IDs prefixed with the step, e.g. `S01-D1`)
- §3 Directory structure (target state)
- §4 Work items (each with command + verification)
- §5 의도적으로 하지 않는 것 (explicit non-goals with "유예" reasoning)
- §6 Risks
- §7 Next-Step linkage
- (optional) §A Appendix — inline file contents for automation. **Single-use scaffolding**: stripped during Step-close cleanup. The first Step (Step 01) keeps it heavy while workflow is being established; later Steps may skip it from the start.

Tracker mirrors Plan §4 numbering 1:1 in its §1 checklist; automation depends on this.

Step-close cleanup sequence (at the **closing** Step's final commit):

1. Verify all Plan §4 items checked.
2. Verify all DoD items checked.
3. `git status` clean.
4. Update `000_Progress_Tracker.md` (current step status, active files, step status table).
5. Strip Plan §A.
6. git commit per [D015](000_Architecture_Decisions.md), then `git merge --no-ff` to main and delete branch.

Then at the **next** Step's kickoff §4.1 commit:

7. `git mv` previous Step files to `legacy/stepNN/` ([Pipeline Overview §16](000_Pipeline_Overview.md)) together with the next Step's module scaffold.

Reason:

- Separates *decisions* (Plan, slow-changing, frozen on completion) from *progress* (Tracker, fast-changing, archived on completion). Mixing them makes both worse.
- Plan §4 ↔ Tracker §1 numbering preserves traceability and enables automated execution.
- Single-use Appendix avoids the "huge inline scaffolding lives forever in the repo" failure mode.
- **Deferred archive (step 7)**: moving Plan/Tracker mid-cleanup creates a self-reference paradox — the cleanup checklist itself ends up under `legacy/`, and the closing Tracker would have to mark its own archival as "done" before the move. By archiving at the *next* Step's kickoff §4.1, the previous Step's docs stay accessible at repo root through the close, and the new Step's first commit naturally bundles "archive previous + scaffold current". Pattern validated across Step 01 → 02 → 03.

---

## D017. Strict Literal validation in schema deserialization

Status: Accepted  
Type: Replaceable implementation choice

Decision:

`from_dict` and `from_json` validate `Literal[...]`-typed fields against their allowed values at deserialization time. Out-of-range values raise `ValueError` immediately, not silently passing through to a later Stage gate.

Reason:

Python `typing.Literal` is a static-analysis hint with no runtime enforcement. `BuildingInput.target_type: TargetType = Literal["apartment", "house", "hotel", "warehouse", "office"]` was silently accepting `"apartmnt"` and any other string — a fixture typo would only surface much later at Stage 00. This violates the spirit of [S02-D13](legacy/step02/002_Step02_CoreSchema_Plan.md) ("strict input policy"). Validating Literal at deserialization fails fast, locally, with a clear error message.

Scope:

- Applies to all dataclass fields whose annotation is `Literal[...]` or `Literal[...] | None`.
- Validation runs regardless of `strict_unknown`. The two policies are independent: `strict_unknown` controls *unknown keys*, D017 controls *invalid values* of known Literal-typed keys.
- Does NOT introduce general schema runtime validation (no min/max, no regex, no required-field semantics beyond what S02-D13 already does). The framework remains schema-stub-first; Literal is the narrow case where the annotation already encodes the allowed set, so enforcing it costs nothing.

Discovered: Step 03 review followups #5 (2026-05-06).

---

## D018. Stage 13 output assembly: unified LayoutCandidate (valid=True/False)

Status: Accepted  
Type: Architecture invariant

Decision:

Stage 13 emits a single dataclass — `LayoutCandidate` — for both valid and invalid candidates. The `valid: bool` field discriminates the two cases. There is no separate `InvalidCandidateReport` class.

`LayoutCandidate` carries the union of fields needed by either case; failure-side fields default to empty/None and must be populated for `valid=False`:

| Field | Type | Required when |
|---|---|---|
| `validation_result` | `ValidationResult \| None` | Post-repair Stage 13 result; populated whether valid or invalid |
| `failure_records` | `list[FailureRecord]` | **Must be non-empty when `valid=False`** ([Pipeline Overview §9](000_Pipeline_Overview.md)) |
| `debug_artifact_refs` | `dict[str, str]` | `{kind: path}` for debug SVG/JSON references |
| `provenance` | `dict` | Search-path information (TBD typed) |
| `output_artifacts` | `dict` | Final JSON/SVG output paths (TBD typed) |

Reason:

- The schema already encoded the unified-model intent: `LayoutCandidate.valid: bool = False` had been on the dataclass since Step 02. A separate `InvalidCandidateReport` would have made that field meaningless.
- Consistency with [D009](000_Architecture_Decisions.md). Pre/post validation is unified in `ValidationResult.stage`. Splitting only the Stage 13 output across two classes would break the pattern.
- The Search Orchestrator pseudo-flow ([Pipeline Overview §10](000_Pipeline_Overview.md)) reads `result.valid` and `result.failure_records` directly. Unified model means no isinstance / discriminated-union dispatch.
- Valid candidates may legitimately carry partial failure information (e.g., resolved soft violations). Empty default `failure_records=[]` accommodates this without forcing the caller through Optional handling.
- Pipeline Overview §9 Stage 13 narrative ("LayoutCandidate if valid, InvalidCandidateReport if invalid") was a *narrative* split, not a *data model* split. Narrative is updated to reflect the unified data model.

Discovered: Step 03 review followups #6 (2026-05-06). The reviewer noted Pipeline §9 listed `InvalidCandidateReport` while the schema lacked any such class. Investigation showed the schema's `valid: bool` already implied unification; this decision codifies that alignment.

**Enforcement note** (added 2026-05-08 from Step 05 review): the `failure_records: list[FailureRecord]` field defaults to `[]` at the dataclass level so `valid=True` candidates can carry an empty list naturally. The "**must be non-empty when `valid=False`**" requirement is therefore an *architectural* contract, not a dataclass-level invariant. Stage 13 implementation (Step 12+) must enforce it through a factory function or a `validate_layout_candidate()` guard before emission; the Search Orchestrator should treat any `LayoutCandidate(valid=False, failure_records=[])` as a programming error.

---

## D019. Per-family proportional atom sizing (D006 amendment)

Status: Accepted (2026-05-08)  
Type: Architecture amendment (supersedes D006 numerical defaults)

Decision:

Step 05 imports the v3.2 cell-partition algorithm (`references/cell_v3_2.{py,md}`) into `src/proto3/geometry/`. This concretizes D006's "first-pass commitments, not universal laws" provision and revises the atom layer's numerical and shape policy.

**Atom size — per-family proportional**:

- `atom = "target cell size proportional to family main rect"` (was: fixed 600mm cube).
- Each *family* (same theta + phase chain) shares a single cell width / height computed by fitting the family's main rect to integer N×M cells nearest `target_cell_size`. This eliminates sliver inside the family.
- Different-theta families compute their own cell size from their own main rect — multi-axis footprints (mirror wings, rotated extensions) get correct atom alignment per family.

**Atom shape — interior grid + boundary polygon**:

- Interior atoms: full axis-aligned cells of size (cell_w × cell_h) within the family's rotated frame.
- Boundary atoms: simple polygons clipped by the region edge (single ring, no holes; v3.2 cells are always single-polygon).
- Atoms with intersection-area-fraction < `atom_inclusion_threshold` (default 0.5, "50% rule") are merged into the longest-shared-boundary neighbor.

**Numerical defaults (revises D006 "Initial atom defaults")**:

| Item | Initial (D006) | Revised (D019) | Notes |
|---|---:|---:|---|
| Internal coordinate unit | mm | **mm** | unchanged |
| Default layout atom size | 600mm | **300mm** | finer mission resolution |
| `atom_inclusion_threshold` | — | **0.5** | NEW — area-fraction (v3.2 50% rule) |
| Door-capable shared boundary | 800mm | **800mm** | unchanged |
| Preferred door boundary | 900mm | **900mm** | unchanged |

**Deprecated by this amendment** (concept superseded by `atom_inclusion_threshold`):

- `min_atom_side_mm` — was a `RunConfig` field with default 300 (D006). Sliver detection is now area-based, not side-based. Field retained in `RunConfig` for backward compatibility; no longer consulted by the algorithm.
- `tiny_atom_area_m2` — was a Pipeline §8 conceptual default (0.18㎡, never reified into `RunConfig`). Now formally retired; same area-fraction concept absorbed by `atom_inclusion_threshold`.

The deprecated `RunConfig.min_atom_side_mm` field will be removed in a future Step once external callers no longer rely on it.

**Retained from D006 (no change)**:

- region/atom dual-layer principle,
- atom layer purpose ("fine geometric growth unit"),
- mm internal coordinate unit,
- door-capability thresholds.

Reason:

- D006 explicitly invited revision: *"Step 05 Geometry Kernel must confirm or revise these defaults before serious decomposition and growth work."* This is that revision.
- The v3.2 algorithm is externally validated against 30 stress-test footprints (15 한글 자모/mirror/회전/multi-wing + 15 LIR-unfriendly edges: star/blob/swiss cheese/circle/ellipse/triangle); 29/30 cases reach 100% coverage, the remaining 1 is a 0.17% gap from a 45° floating-point edge case. This is far stronger than ad-hoc design speculation could have been.
- The proto3 mission (scan-to-BIM training-data generation, Target A apartment) requires sloped/curved footprint diversity. Per-family proportional sizing preserves sloped boundaries through boundary-polygon atoms, which fixed-grid 600mm sizing cannot do without staircasing.
- Korean residential modular grid commonly uses 300mm / 600mm / 900mm units (3M/6M/9M). 300mm default keeps the modular intuition while halving cell area for finer growth resolution.

References:

- Algorithm code (ported into proto3): `src/proto3/geometry/{lir,grid,recursive,decompose}.py`.
- External origin (preserved): `references/cell_v3_2.{py,md}`, `references/cell_v3_2_{stress,edges}.png`.
- Schema additions (Step 05 §4.5): `proto3.schema.geometry.GeometricPiece` + `proto3.schema.geometry.Decomposition`; `proto3.schema.region_atom.Atom` extended with `parent_piece_id`, `family_id`.
- Risk noted in Step 05: R-S05-7 unit mismatch (proto3 schema mm vs algorithm m). Stage 00 normalization layer in Step 07 (Plan §5 Def-14) will own the mm↔m conversion; Step 05 callers (tests, notebook) handle it inline.

Discovered:

Step 05 §4.6 (algorithm tests) revealed the unit-mismatch and the resulting LIR-mask blow-up (8000mm × 6000mm at 0.05m grid → 19 GB bool array). The amendment text was finalized once the v3.2 algorithm was fully imported and verified against all 6 fixtures (Step 05 §4.4–§4.8).

---

## D020. Stage 02 Domain Feasibility Gate design (Step 06)

Status: Placeholder (body finalized at Step 06 §4.9 close)
Type: Architecture decision

Decision summary:

- **Function module**: `proto3.constraints.gates` exposes 4 pure functions —
  `check_min_area`, `check_min_dim`, `check_access_schema`,
  `check_multi_floor_feasibility`.
- **Stage 02 invokes 3, not 4** (Step 06 scope clarification, 2026-05-09):
  area + min-dim + multi-floor placeholder. `check_access_schema` stays
  **dormant** through Step 06 — its function signature exists for unit
  testing only; Stage 02 does not call it because `ProgramRequest` is
  slim (`spaces` only, S06-D8) and carries no `access_policies`.
  Activation = Step 09-10 when Hub/Spine/Slot generation introduces
  AccessPolicy instances (Plan Def-9).
- **Failure hierarchy**: `DomainGateFailure(Exception)` parent +
  `AreaGateFailure` / `DimGateFailure` / `AccessSchemaFailure` children,
  each holding a `FailureRecord` (S04-D11 pattern).
- **Stage 02 is fail-only** (no repair output). The "repaired
  ProgramInstance" listed in Pipeline §9.10's original Outputs section is
  removed — repair belongs to Stage 12 (Repair) not Stage 02. Stage 02
  contract: `accepted ProgramInstance | DomainGateFailure`.
- **Cardinality lives in Stage 01 only** (D004 alignment). Pipeline §9.10
  Checks list previously included "required cardinality" as a Stage 02
  check; that line is removed. Stage 01 owns cardinality via
  `ProgramInstantiationFailure`; Stage 02 owns area/dim/access/multifloor
  via `DomainGateFailure`.
- **Area gate boundary**: `total_required_area ≤ gross_footprint_area ×
  density_factor` (first-pass). The gate uses **gross** footprint area —
  it does not subtract anchor / void / core regions because those arrive
  at Stage 03 (after Stage 02). Anchor-aware area accounting is post-
  growth (Step 12 / Stage 11).
- **Single-floor assumption**: Stage 02 area + dim gates assume `len(building.floors) == 1`
  (apartment shape). Multi-floor adapters (house/hotel) need per-floor
  program allocation before area/dim gates make sense; that work is
  deferred to Step 14 (Plan Def-8).
- **Required-only summation**: see D023 — both cardinality (Stage 01)
  and area sum (Stage 02) consider only `SpaceUnitSpec.required = True`
  spaces.

Cross-link: Plan [006_Step06_ProgramConstraintEngine_Plan.md](006_Step06_ProgramConstraintEngine_Plan.md) §2 S06-D6, D11–D14, D17, D23, D24.

---

## D021. TargetRules + external JSON config (Step 06)

Status: Placeholder (finalized at Step 06 §4.9 close)
Type: Architecture decision

Decision summary (full text lands at Step 06 close):

- proto3 domain rules (cardinality / area / density) live in `src/proto3/data/target_rules/<target>.json` (package data, not Python).
- `TargetRules` dataclass = typed in-memory contract; `proto3.target.rules_loader.load_target_rules(path)` parses + validates (target_type / density_factor range / unknown roles / negative values).
- `TargetAdapter(rules_path: Path)` requires explicit path (S06-D5); `DEFAULT_APARTMENT_RULES_PATH` constant exported for callers; `stage00_load._DEFAULT_ADAPTERS` is the **sole** site that uses default path implicitly.
- pyproject.toml `[tool.setuptools.package-data]` ships JSON + README in wheel/sdist.
- 4-layer separation (S06-D17): L1 invariant + L2 baseline = proto3, L3 project override = external pipeline (whole-file swap, no merge), L4 external metadata = out-of-scope.

Cross-link: Plan [006_Step06_ProgramConstraintEngine_Plan.md](006_Step06_ProgramConstraintEngine_Plan.md) §2 S06-D4, D5, D9, D17. Cross-references D006 (region/atom dual layer) — atom-based gate computation is Step 12 territory.

---

## D022. Generic TargetAdapter + 3-layer typology extensibility (Step 06)

Status: Placeholder (body finalized at Step 06 §4.9 close)
Type: Architecture decision

Decision summary:

- **Single concrete `TargetAdapter` class** drives every typology.
  Per-typology subclasses (`ApartmentAdapter`, `HotelAdapter`, ...)
  deliberately absent. Typology identity lives in the rules JSON's
  `target_type` field, not in a class name.
- **3-layer extensibility model** (documented in
  `src/proto3/data/target_rules/README.md`):
  - L0 — engine invariant (Python core, typology-agnostic)
  - L1 — parameters (this directory's JSON files)
  - L2 — strategy plugins (future Python; typology-agnostic functions
    selected by JSON enum). L2 not present today; introduced during
    Step 09 (Spine Generation) when first apartment strategy lands.
- **Typology-specific algorithm variants** (e.g., hotel "explicit
  corridor" pattern) — when introduced — go into a strategy registry,
  not into adapter subclasses. Strategies are typology-agnostic:
  a single explicit-corridor function can be used by hotel + large
  office. Selected by JSON enum, dispatched by Stage code (no
  `if target_type == "hotel"` branches).
- **"New typology = JSON + 1 line" — exact boundary** (clarified
  2026-05-09 after second external review): the data-only promise holds
  **only** within the existing 5 `TargetType` Literal values
  (`apartment`/`house`/`hotel`/`warehouse`/`office`) **and** the existing
  6 `Role` Literal values
  (`public`/`private`/`service`/`wet`/`hub`/`corridor`). A typology
  outside that Literal (e.g., `dormitory`) requires a Python schema diff
  to extend `TargetType`; a typology that requires new roles (e.g.,
  warehouse needing `storage`/`loading_dock`) requires a Python schema
  diff to extend `Role`. These extensions are 1-line each but are still
  Python changes — the "data-only" framing applies to typologies that
  fit the established 5×6 grid. Outside-grid typologies require a
  schema-diff PR alongside the JSON.
- **L2 strategy plugin scope**: a typology that shares all algorithms
  with apartment is JSON-only. A typology that needs a different
  algorithm variant adds one strategy function to the registry +
  references it from JSON. Either way, no per-typology adapter class.
- Rationale: proto3 is the engine component of an external scan-to-BIM
  training-data pipeline. Engines that ship data separately scale to new
  typologies without code-class proliferation. Per-typology adapter
  classes (~25-line boilerplate each, only string-different) violate DRY
  and force Stage code to do isinstance dispatch.
- Rejected alternatives: (a) per-typology Adapter classes — boilerplate
  + isinstance dispatch + code-level typology hardcoding; (b) free-string
  `target_type` (no Literal) — silent typo failure at fixture load.

Cross-link: Plan [006_Step06_ProgramConstraintEngine_Plan.md](006_Step06_ProgramConstraintEngine_Plan.md) §2 S06-D5, D17, D22. Cross-references D004 (ProgramInstance owns cardinality), D005 (constraints-as-gates), D012 (dataclass-first).

---

## D023. Required-only cardinality and area summation (Step 06)

Status: Accepted (2026-05-09)
Type: Architecture decision

Decision:

- Stage 01 cardinality gate compares `min_cardinality[role]` against
  `Counter(u.role for u in space_units if u.required)` — **only `required=True`
  spaces count toward cardinality**.
- Stage 02 area gate sums `min_area_m2` over `[u for u in space_units if
  u.required]` — **only required spaces contribute to the area total**.
- Optional spaces (`required=False`) are layout-best-effort: they may be
  attempted later (Search Orchestrator) or dropped if infeasible. They
  do not influence Stage 01/02 admission.

Reason:

Without this rule, an optional bedroom can satisfy a `min_cardinality.private:
1` requirement (silent bug; D004 spirit violated), and Stage 02 can
false-reject a feasible program because optional spaces inflated the
total `min_area` sum. Both failure modes are silent — exactly the
"silent fall-through" pattern that D004 / D005 / DH-004 trauma was
introduced to prevent.

Application:

- `proto3.stages.stage01_program.run` filters to `required=True` before
  cardinality counting (Step 06 §4.5).
- `proto3.constraints.gates.check_min_area` filters to `required=True`
  before summation (Step 06 §4.4).
- Stage 02 dim gate uses `required=True` spaces' `min_dimension_mm` only
  (Step 06 §4.4).

Repair / drop policy for optional spaces:

- Stage 02 does not auto-drop optional spaces (D020: fail-only).
- Repair (drop optional, retry) is a Stage 12 / Search Orchestrator
  concern. If a layout fails post-growth and the program contained
  optionals, Stage 12 may produce a repaired ProgramInstance with one or
  more optionals removed; that repaired instance re-enters Stage 02.

Cross-link: D004 (ProgramInstance owns cardinality). Plan
[006_Step06_ProgramConstraintEngine_Plan.md](006_Step06_ProgramConstraintEngine_Plan.md)
§2 S06-D7 (default fill at Stage 01 instantiation also filters to required).

---

# 4. Deferred decisions

These are intentionally not fully settled yet.

## Q001. Exact decomposition algorithm

Current direction:

```text
manual/semi-manual fixtures
→ reflex vertex extension
→ rectangle scoring helper
```

Deferred:

- when to add maximal rectangle search,
- whether to add medial-axis/skeleton hints,
- whether atom-first clustering is useful.

## Q002. Exact growth replacement path

Current first-pass:

```text
greedy multi-source priority growth
```

Deferred:

- beam growth,
- min-cost assignment + repair,
- hybrid approaches.

## Q003. Multi-floor orchestration details

Current decision:

- schema supports anchors early,
- Stage 03 is a no-op for apartment-first,
- Step 14 implements non-trivial persistent anchors and floor orchestration.

Deferred:

- floor allocation grammar,
- stair/core placement search,
- cross-floor wet stack scoring,
- multi-floor validation metrics.

---

# 5. Decision history appendix

This appendix is a chronological log of major changes. It is not a separate source of truth.

## H001. Narrowed the claim

The framing was narrowed from “innovative framework” to:

> spine-first + region/atom dual layer + failure-directed backtracking schema.

Reason: this is more honest, testable, and implementable.

## H002. Promoted region decomposition and atom growth from implementation details to core algorithm choices

Region decomposition and atom growth are not downstream details. They shape what the system can perceive and produce.

## H003. Added Program & Domain Constraint Layer

Cardinality, area, aspect ratio, min dimension, access policy, and required door boundary became first-class gates/validations.

## H004. Reframed failure-directed retry as failure-to-pruning

Retry is not useful unless a failure updates the search space through a reject, penalty, invariant, escalation, or no-good record.

## H005. Changed final framework reference from v1 roadmap to canonical framework

Implementation sequencing was separated from the final architecture reference.

## H006. Reorganized docs into three global files

Global docs are:

```text
000_Pipeline_Overview.md
000_Architecture_Decisions.md
000_Progress_Tracker.md
```

`000_User_Profile.md` is maintained separately by the user.

## H007. Removed Step 00 and adopted 001–014 implementation Steps

`000_*` is reserved for global docs. Actual implementation Steps start at Step 01.

## H008. Separated Candidate Search from Stage pipeline

Candidate Search became Search Orchestrator, not Stage 14.

## H009. Split validation into pre-repair and post-repair

Repair now consumes a defect report and is validated afterward.

## H010. Codified Step-level documentation and VCS workflow during Step 01

Step 01 set up the project skeleton. During execution, two workflow patterns emerged from collaboration and were promoted to accepted decisions:

- D016 (Per-Step Plan + Tracker companion docs) — decision/progress separation, Plan §A as single-use scaffolding, Step-close cleanup sequence.
- D015 (Per-Step branch + per-work-item commit + no-squash merge) — Step 01 itself was bundled into one `main` commit as an exception, since the convention was decided mid-Step-01.

These patterns proved their value during Step 01 and would otherwise live only in session memory, invisible to anyone reading the global docs. Promoted to D015/D016 to make them auditable and durable.

## H011. Deferred Plan/Tracker archive to next-Step kickoff (D016 amendment)

Original D016 step 6 said "Move both Step files to `legacy/stepNN/`" as part of Step-close cleanup. In practice, doing the `git mv` mid-cleanup creates a self-reference paradox: the cleanup checklist itself ends up under `legacy/`, and the closing Tracker would have to mark its own archival before the move. Across Step 01, 02, 03 the actual practice was to defer the move to the next Step's §4.1 kickoff commit, where it bundles cleanly with "scaffold next-Step modules". The user codified this deferral on 2026-05-03.

D016 wording was amended on 2026-05-06 (Step 03 review followups #4) to reflect the actual practice: cleanup steps 1–6 happen at Step-close; archive (step 7) happens at the *next* Step's kickoff §4.1. Documented after a reviewer flagged the inconsistency between D016 text and Progress Tracker statements.

## H012. Legacy doc relative links not maintained after archive (D016 amendment)

When Step docs are archived to `legacy/stepNN/` per D016 step 7, their relative links to root files (e.g., `[000_Architecture_Decisions.md](000_Architecture_Decisions.md)`) become broken because the relative path now requires `../../` prefix. Step 02 and Step 03 archived docs were both found to have this drift.

Policy: **`legacy/stepNN/*.md` is treated as a frozen historical record; relative links are not maintained after archive.** Rationale:

- legacy docs are append-only history; updating them post-move would imply they remain "live" docs.
- audit and traceability remain intact through the file content itself; the broken links are minor friction, not correctness loss.
- mechanical fix on archive is possible but adds churn for low value (legacy reference frequency is near zero in practice).

Codified on 2026-05-07 (Step 04 kickoff, review followup #8). Pipeline Overview §16 mirrors this policy.

## H013. Atom layer revised via D019 (per-family proportional sizing)

D006 had committed to "atom = 600mm cube" as the default and explicitly invited Step 05 to confirm/revise. Step 05 imported the externally-developed v3.2 cell-partition algorithm (`references/cell_v3_2.{py,md}`), validated against 30 stress-test footprints, and the algorithm's per-family proportional sizing replaces the fixed-grid default.

D019 was registered on 2026-05-08 with this revised atom shape + sizing policy. Three substantive changes:
1. atom default size lowered from 600mm to 300mm (Korean modular grid; finer mission resolution).
2. atom shape generalized: interior cells stay axis-aligned grid, but boundary cells become polygons clipped by the region edge — required for sloped/curved footprint preservation (mission diversity).
3. sliver detection moved from side-based (`min_atom_side_mm`) to area-fraction (`atom_inclusion_threshold = 0.5`); the v3.2 50% rule absorbs partial cells into the longest-shared-boundary neighbor.

Pipeline Overview §8 numerical-defaults table updated to mirror D019. `RunConfig` retains the deprecated `min_atom_side_mm` field for backward-compat (the algorithm no longer consults it). `tiny_atom_area_m2` was a Pipeline §8 conceptual default that was never reified into `RunConfig`, so no code change was needed — only documentation updates marking it deprecated.

---

# 6. Summary

Architecture invariants:

```text
- Step / Stage / Search Orchestrator / Cross-cutting Infrastructure / Target separation
- apartment-first but floor-rooted architecture
- ProgramInstance owns cardinality
- domain constraints are gates, not role scores
- region/atom dual layer
- floor-rooted spine-first candidate search
- Candidate Search is not a Stage
- pre-repair and post-repair validation
- failure-to-pruning backtracking
- access-preserving atom growth
```

Replaceable first-pass choices:

```text
- greedy multi-source priority growth
- SVG-first renderer implementation details
- dataclass-first schema
- initial atom resolution defaults
- reflex-cut decomposition first pass
```
