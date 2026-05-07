# 000 Pipeline Overview

Status: Canonical global reference  
Scope: proto3 framework, terminology, runtime pipeline, search orchestration, target model, and implementation Step map  
Last updated: 2026-05-02

---

## 0. Purpose

This document is the canonical overview for proto3.

It defines:

- the final framework concept,
- the distinction between **Step**, **Stage**, **Search Orchestrator**, **Cross-cutting Infrastructure**, and **Target**,
- the internal candidate pipeline,
- the Search Orchestrator loop,
- the core data flow,
- the 001–014 implementation Step map.

This file is not a daily tracker. Current work status belongs in `000_Progress_Tracker.md`. Accepted design decisions and their rationale belong in `000_Architecture_Decisions.md`.

---

# 1. One-line definition

proto3 is a **spine-first layout generation framework** that builds floor layouts by:

1. instantiating a valid program,
2. decomposing a floor footprint into coarse regions and fine atoms,
3. generating floor-rooted spine / access-tree hypotheses,
4. attaching space seeds to branch slots,
5. growing spaces over an atom graph while preserving access and domain constraints,
6. validating, repairing, diagnosing failures, and pruning bad hypotheses.

Short framing:

> **spine-first candidate search using a region/atom dual layer and failure-to-pruning backtracking.**

---

# 2. Structural terminology

These terms must stay separate.

| Term | Meaning | Example |
|---|---|---|
| **Step** | Development roadmap unit. This is the order in which the repo is implemented. | Step 05 Geometry Kernel, Step 11 Atom Growth |
| **Stage** | Runtime pipeline unit. This is one transformation a single layout candidate goes through. | Stage 04 Region / Atom Decomposition, Stage 10 Atom Growth |
| **Search Orchestrator** | Control loop outside the Stage pipeline. It runs stages repeatedly, manages candidates, retries, no-good records, and search budget. | rerun Stage 09–13 after seed failure |
| **Cross-cutting Infrastructure** | Systems used across many stages, not stages themselves. | provenance, debug output, visualization, run config, no-good store |
| **Target** | Building / spatial typology adapter. | Apartment Unit, Multi-floor House, Hotel Floor |

Important rules:

- **Step and Stage are not the same thing.**
- **Candidate Search is not a Stage.**
- **Provenance, visualization, debug output, and no-good records are cross-cutting infrastructure.**
- A Step may implement one Stage, multiple Stages, part of a Stage, cross-cutting infrastructure, or the Search Orchestrator.

---

# 3. What is a Stage?

A **Stage** is a deterministic or candidate-generating transformation inside the layout pipeline.

A Stage has:

- input artifacts,
- output artifacts,
- optional candidate alternatives,
- validation hooks,
- provenance links to earlier artifacts.

Example:

```text
Stage 04 Region / Atom Decomposition
Input:
  FloorInput, footprint, anchor projection
Output:
  RegionSet, AtomSet, decomposition candidates
```

Example:

```text
Stage 08 Spine / Access Tree Generation
Input:
  Graphs, root, hub candidates, terminal candidates
Output:
  SpineCandidate[]
```

A Stage transforms one candidate state into the next candidate state.

---

# 4. What is not a Stage?

The following are not pipeline Stages:

- Candidate Search,
- no-good record management,
- retry ladder execution,
- global provenance storage,
- debug artifact writing,
- visualization infrastructure,
- run configuration,
- experiment bookkeeping.

These are system-level or cross-cutting concerns.

---

# 5. Candidate Search is not a Stage

Candidate Search is the **control loop** that repeatedly runs the Stage pipeline, evaluates candidates, records failures, prunes the search space, and decides where to resume.

It is not Stage 14. It is the loop around Stage 00–13.

Canonical sentence:

> **Candidate Search is not a pipeline Stage. It is the control loop that repeatedly runs Stage 00–13, updates no-good records, and decides which earlier Stage to revisit.**

Why this matters:

- A Stage transforms one candidate.
- Candidate Search manages many candidates.
- A Stage should not own retry policy.
- The Search Orchestrator owns retry, pruning, candidate ranking, and search budget.

Example:

```text
Search Orchestrator
  ├─ run Stage 00–13 for candidate A
  ├─ candidate A fails post-repair validation
  ├─ convert failure into FailureRecord
  ├─ add NoGoodRecord or penalty
  ├─ decide retry level
  ├─ rerun Stage 09–13 for a new seed candidate
  ├─ if repeated failure, rerun Stage 08–13 for a new spine candidate
  └─ keep the best valid candidate(s)
```

Failure-directed retry only becomes meaningful when failed candidates change the future search space.

---

# 6. Core framework vocabulary

## 6.1 Floor and access terms

| Term | Meaning |
|---|---|
| `floor_root` | Primary access origin for a floor. Apartment: unit entry. Upper floor of house: stair landing. |
| `hub` | Primary access host or central distribution space. Apartment: living / living-kitchen / hall. |
| `spine` | Floor-rooted access skeleton. General term for root → hub → branch structure. |
| `trunk` | Main access segment from root to hub. |
| `branch` | Access segment from trunk/hub/current spine to a cluster terminal. |
| `stub` | Short local connection from branch to door / seed / attachment point. |
| `access_host` | A space that also acts as traversable access, e.g. living room or hall. |
| `explicit_access` | Dedicated access space, e.g. corridor or stair landing. |

## 6.2 Program and domain terms

| Term | Meaning |
|---|---|
| `ProgramSpec` | Typology-level rules for what may be generated. |
| `ProgramInstance` | Concrete required spaces for a candidate: e.g. living 1, bedroom 2, bathroom 1. |
| `SpaceUnitSpec` | One required or optional generated space and its constraints. |
| `ClusterSpec` | Functional/access grouping of already-instantiated spaces. Cluster does not create cardinality. |
| `AccessPolicy` | Primary/dependent access rules for a space. |
| `DomainConstraint` | Hard or soft rule such as bathroom count, area range, min dimension, aspect ratio, exterior contact. |

Important rule:

> **Cluster is not the source of cardinality. ProgramInstance is the source of cardinality.**

Clusters group existing SpaceUnits for access/spine/seed decisions. They do not decide whether a bathroom exists.

## 6.3 Region / atom terms

| Term | Meaning |
|---|---|
| `region` | Coarse architectural territory: lobe, bay, pocket, neck, public candidate, private candidate. |
| `atom` | Fine growth unit used for graph traversal, assignment, access preservation, and area adjustment. |
| `RegionSet` | Candidate set of regions for one decomposition. |
| `AtomSet` | Candidate set of atoms tied to parent regions. |
| `RegionGraph` | Contact graph between regions. |
| `AtomGraph` | Contact graph between atoms. |

Region and atom are both required.

- Region provides architectural meaning.
- Atom provides geometric resolution and growth mechanics.

## 6.4 Seed / slot terms

| Term | Meaning |
|---|---|
| `terminal` | Cluster target location. Not a final room polygon. |
| `slot` | Branch-adjacent attachment opportunity, usually with door/access boundary potential. |
| `seed` | Initial hypothesis for where a SpaceUnit starts growing. |
| `patch` | Seed represented as multiple atoms rather than one point. |
| `SeedSet` | A coordinated set of seeds for a candidate. |

## 6.5 Failure terms

| Term | Meaning |
|---|---|
| `ValidationResult` | Result of checking a candidate against hard/soft constraints. |
| `DefectReport` | Pre-repair record of what is wrong or low-quality before repair. |
| `FailureRecord` | Evidence-backed diagnosis of why a candidate failed. |
| `NoGoodRecord` | Search-space pruning record derived from repeated or clear failures. |
| `RetryLevel` | The level at which the Search Orchestrator should resume: growth, seed, spine, decomposition, etc. |

---

# 7. Domain constraints are first-class

Domain knowledge must not be hidden inside role scoring.

Role scoring answers:

```text
Where would this space prefer to be?
```

Domain constraints answer:

```text
Is this candidate allowed to exist?
```

Hard constraints include:

- required cardinality,
- minimum area,
- minimum dimension,
- primary/dependent access validity,
- required door-capable boundary,
- no overlaps,
- inside footprint,
- persistent anchors preserved.

Soft constraints include:

- preferred area ratio,
- preferred aspect ratio,
- exterior contact preference,
- wet/service proximity,
- compactness / rectangularity,
- region boundary alignment.

Regression rule:

> A required bathroom count of zero in an apartment program is a ProgramInstantiationFailure, not a growth failure.

---

# 8. Geometry and atom resolution commitments

The region/atom dual layer is not meaningful unless atoms have a shared resolution contract.

Initial geometry commitments:

| Item | Initial default | Notes |
|---|---:|---|
| Internal coordinate unit | millimeter | Avoid unit ambiguity. |
| Default layout atom size | 600mm nominal side | Replaceable but must be explicit. |
| Minimum atom side | 300mm | Below this is usually sliver/tiny geometry. |
| Tiny atom area threshold | 0.18㎡ | 300mm × 600mm equivalent. Configurable. |
| Door-capable shared boundary | 800mm minimum | Configurable by Target and local rules. |
| Preferred door boundary | 900mm or more | Used as a stronger positive score. |

These values are first-pass defaults. They are not universal architectural laws, but the implementation must commit to initial values so decomposition, graph construction, growth, validation, and visualization use the same assumptions.

Step 05 Geometry Kernel must confirm or revise these values before region/atom decomposition becomes serious.

**Open issue — door capability granularity (TBD).** The 800mm threshold above applies to a *contact segment*, not to individual cell-cell adjacencies. With atom_size = 600mm, a single cell-cell boundary is 600mm and would falsely reject doors that are physically installable across two or more contiguous cells along the same wall. Provisional operative definition: for each region pair, group their cell-cell adjacencies into maximal contiguous runs along a single axis-aligned wall; door-capable iff any such run has length ≥ door_min_boundary_mm. Disjoint segments between the same region pair (e.g., U-shaped wraparound) are *not* summed — the threshold applies per segment. Step 05/08 must confirm this definition once the first fixture is decomposed and inspected.

---

# 9. Canonical runtime pipeline Stages

The runtime pipeline is the ordered transformation applied to one candidate state. Candidate Search may run the whole pipeline or resume from a later Stage depending on failure diagnosis.

## Stage 00. Input Normalization

Purpose: Normalize raw input into canonical internal units and structures.

Inputs:

- footprint polygon,
- target type,
- floor count,
- entry/root information,
- raw program request,
- optional anchors.

Outputs:

- `BuildingInput`,
- `FloorInput[]`,
- normalized coordinates,
- canonical root/entry hints,
- empty anchor lists if none are provided.

Notes:

- Empty anchor fields are required from the beginning, even for apartment-first work.
- Apartment-first does not mean single-floor-only data types.

---

## Stage 01. Program Instantiation

Purpose: Convert typology/program request into concrete required and optional spaces.

Inputs:

- `TargetSpec`,
- program request,
- floor count,
- area budget.

Outputs:

- `ProgramInstance`,
- `SpaceUnitSpec[]`,
- `AccessPolicy[]`,
- initial required counts.

Rules:

- Cardinality is decided here.
- Required spaces must be explicit.
- Missing required spaces are program failures, not downstream layout failures.

---

## Stage 02. Domain Feasibility Gate

Purpose: Reject or repair impossible programs before geometry search.

Checks:

- required cardinality,
- total minimum area vs usable footprint area,
- obvious floor allocation impossibility,
- required access/dependency schema validity,
- target-specific constraints.

Outputs:

- accepted `ProgramInstance`,
- repaired `ProgramInstance`, or
- `ProgramInstantiationFailure`.

---

## Stage 03. Persistent Anchor Projection

Purpose: Project building-global anchors into each floor.

Examples:

- stair,
- elevator,
- wet shaft,
- structural core,
- void/opening.

Outputs:

- occupied/non-growable anchor geometry,
- anchor-derived root candidates,
- anchor adjacency requirements,
- anchor constraints for decomposition/growth.

Apartment-first behavior:

- If no anchors are provided, this Stage is a no-op.
- It must still produce an empty `AnchorProjectionResult`.

---

## Stage 04. Region / Atom Decomposition

Purpose: Decompose the floor footprint into coarse architectural regions and fine growth atoms.

Inputs:

- normalized footprint,
- anchor projection,
- atom resolution settings.

Outputs:

- `RegionSet[]`,
- `AtomSet[]`,
- decomposition scores,
- sliver/tiny geometry warnings.

Candidate algorithms:

1. manual or semi-manual cut lines,
2. reflex vertex extension,
3. maximal rectangle assisted decomposition,
4. skeleton/medial-axis assisted decomposition,
5. atom-first clustering.

Default first-pass direction:

```text
manual/semi-manual fixtures
→ reflex vertex extension
→ rectangle scoring as helper
```

---

## Stage 05. Graph Construction

Purpose: Build contact graphs over regions and atoms.

Outputs:

- `RegionGraph`,
- `AtomGraph`,
- shared boundary metadata,
- door-capable edge flags,
- access-capable edge flags.

Edge metadata should include:

- shared boundary segment,
- shared boundary length,
- orientation,
- door capability,
- access capability,
- parent region relationship.

---

## Stage 06. Static Features / Role Scoring

Purpose: Compute geometry and role features used by later candidate generation.

Outputs:

- region features,
- atom features,
- public/private/service/access role score fields,
- exterior contact measures,
- compactness / rectangularity proxies,
- root-conditioned features where available.

Important distinction:

- Role score is preference.
- Domain constraint is gate.

---

## Stage 07. Hub / Terminal Candidate Generation

Purpose: Generate candidate hub and cluster terminal locations.

Inputs:

- graphs,
- role scores,
- root,
- ProgramInstance,
- clusters.

Outputs:

- `HubCandidate[]`,
- `TerminalCandidate[]`,
- terminal capacity estimates,
- cluster-to-terminal compatibility scores.

---

## Stage 08. Spine / Access Tree Generation

Purpose: Generate floor-rooted spine candidates connecting root, hub, and cluster terminals.

Outputs:

- `SpineCandidate[]`,
- trunk/branch/stub structure,
- reserved access atoms,
- branch cost breakdown,
- attachment opportunity hints.

Canonical point:

> The spine is not necessarily an explicit corridor. It may become hall, living access host, corridor, aisle, landing, or another target-specific access carrier.

---

## Stage 09. Slot / Seed / Patch Generation

Purpose: Attach space growth hypotheses to spine branch slots or parent boundaries.

Outputs:

- `SlotCandidate[]`,
- `SeedCandidate[]`,
- `SeedSet[]`,
- required boundary evidence at seed time.

Rules:

- Primary spaces need access-adjacent or access-host boundary potential.
- Dependent spaces need parent-boundary potential.
- Seed candidates must preserve provenance: terminal, branch, slot, parent region, and initial boundary evidence.

**Open issue — seed clustering (TBD).** proto1/2 layouts showed seeds visually clustered, producing unrealistic-looking starts. Two likely causes: score-based top-K selection has no diversity term, and multi-source growth all initiates near the spine head. Provisional first-pass mitigation when this Stage is implemented: Poisson-disk-style rejection sampling over candidate seeds with a min-distance parameter (initial guess 4–5 × atom_size). Topology-aware quotas (one seed per spine branch) are deferred — they assume sufficiently branched spines and are a separate decision. Role-aware constraints (e.g., bedroom not adjacent to entry) belong to Stage 02 / Step 06 program/domain constraints, not the seed-spread mechanism.

---

## Stage 10. Atom Growth

Purpose: Grow SpaceUnits over the AtomGraph while preserving access and domain constraints.

Outputs:

- atom assignment,
- grown space patches,
- growth steps,
- access preservation evidence,
- boundary preservation evidence.

Framework invariant:

> proto3 requires **access-preserving atom growth**.

First-pass algorithm choice:

> The first implementation uses greedy multi-source priority growth, but greedy growth is replaceable.

Candidate algorithms:

1. greedy multi-source priority growth,
2. beam search growth,
3. staged growth by space priority,
4. min-cost assignment + repair.

---

## Stage 11. Pre-repair Validation / Defect Detection

Purpose: Validate the raw growth result before repair and identify what repair is allowed to fix.

Outputs:

- `PreRepairValidationResult`,
- `DefectReport`,
- hard failure flags,
- repairable defect flags,
- non-repairable defect flags.

Examples:

- jagged boundary: repairable,
- small notch: repairable,
- missing required bathroom: non-repairable program failure,
- primary door boundary absent since seed time: seed/slot/spine failure,
- primary door boundary lost during growth: growth failure,
- area slightly off target: potentially repairable,
- min area impossible: terminal/program failure.

---

## Stage 12. Repair / Rectangularization

Purpose: Apply defect-directed repair and geometry cleanup.

Inputs:

- growth result,
- pre-repair validation result,
- defect report.

Outputs:

- repaired layout candidate,
- repair operations,
- before/after geometry comparison,
- repair provenance.

Repair examples:

- gap fill,
- atom swap,
- boundary simplification,
- wall alignment,
- notch removal,
- rectangularization.

Important rule:

> Repair must be defect-directed. It should not be blind cleanup that makes it impossible to know what changed.

---

## Stage 13. Post-repair Validation / Failure Diagnosis / Output Assembly

Purpose: Validate the repaired candidate, diagnose failures, and assemble final or invalid candidate output.

Outputs:

- `LayoutCandidate` (single dataclass for both valid and invalid; `valid: bool` discriminates per [D018](000_Architecture_Decisions.md)),
- inside that `LayoutCandidate`:
  - `validation_result` — post-repair `ValidationResult` (stage="post_repair", per [D009](000_Architecture_Decisions.md)),
  - `failure_records: list[FailureRecord]` — must be non-empty when `valid=False`,
  - `debug_artifact_refs: dict[str, str]` — final debug artifact paths,
  - `output_artifacts: dict` — final JSON/SVG output references,
  - `provenance: dict` — search-path information.

Required behavior:

> Stage 13 assembles a single unified `LayoutCandidate` per candidate. Invalid candidates (`valid=False`) must still populate `failure_records`, `provenance`, and `debug_artifact_refs`. Valid candidates may carry empty defaults on the failure-side fields.

Failure diagnosis should distinguish:

- program/domain failure,
- decomposition failure,
- hub/terminal failure,
- spine/branch failure,
- slot/seed failure,
- growth failure,
- repair failure,
- post-repair regression.

---

# 10. Search Orchestrator

The Search Orchestrator is the system around the Stage pipeline.

Responsibilities:

- choose candidate hypotheses,
- execute Stage 00–13 or resume from a chosen Stage,
- maintain candidate pool,
- maintain no-good records,
- apply retry ladder,
- update penalties,
- decide where to resume the pipeline,
- select final candidate(s),
- preserve diversity if requested.

Pseudo-flow:

```text
initialize RunState
initialize candidate queue

while search_budget remains:
  candidate = choose_next_candidate()
  result = run_or_resume_pipeline(candidate)

  if result.valid:
    store_valid_candidate(result)
    continue_or_stop_based_on_budget()

  failure_records = result.failure_records
  update_no_good_records(failure_records)
  update_candidate_penalties(failure_records)
  retry_level = choose_retry_level(failure_records)
  enqueue_next_candidates(retry_level)
```

Retry levels:

| Retry level | Meaning | Rerun |
|---|---|---|
| Local repair | Try different repair operation | Stage 12–13 |
| Growth retry | Change growth order / score perturbation | Stage 10–13 |
| Seed retry | Shift seed / resize patch / choose different seed set | Stage 09–13 |
| Slot retry | Choose different slot on same branch | Stage 09–13 |
| Spine retry | Choose different branch path or topology | Stage 08–13 |
| Terminal / hub retry | Choose different hub or terminal | Stage 07–13 |
| Decomposition retry | Choose different decomposition | Stage 04–13 |
| Program repair/reject | Repair or reject ProgramInstance | Stage 01–02 |

---

# 11. Failure-to-pruning mechanism

Failure-directed retry means a failure must update the future search space.

Bad:

```text
layout failed
→ try again randomly
```

Good:

```text
layout failed
→ identify which invariant broke and when
→ diagnose likely layer
→ reject / penalize / preserve / escalate
→ retry from the smallest useful level
```

A `FailureRecord` should contain:

```yaml
failure_type: primary_door_boundary_missing
affected_space: bathroom_shared
detected_stage: post_repair_validation

evidence:
  seed_had_door_capable_boundary: true
  final_has_door_capable_boundary: false
  boundary_lost_during_growth: true

diagnosis:
  likely_layer: growth
  confidence: 0.8
  reason: required boundary existed after seed placement but was lost during growth

learned_constraint:
  type: preserve_required_boundary
  applies_to:
    space: bathroom_shared
    slot: slot_12

retry_policy:
  start_level: growth_retry
  escalation:
    - seed_retry
    - spine_retry
```

A `NoGoodRecord` can hard-reject, softly penalize, or conditionally reject a pattern.

Examples:

```yaml
no_good:
  reason: wet_terminal_capacity_insufficient
  pattern:
    terminal: wet_terminal_2
    cluster: wet_service
  action:
    reject_terminal_for_cluster: true
```

```yaml
no_good:
  reason: repeated_primary_door_failure
  pattern:
    hub: hub_1
    branch: private_branch_2
    slot: slot_23
    space: bedroom_2
  action:
    disallow_same_pattern: true
```

---

# 12. Cross-cutting infrastructure

These systems apply across multiple stages and must not be modeled as a single Stage.

## 12.1 Provenance

Every candidate artifact must remember where it came from.

Examples:

```text
RegionSet came from decomposition candidate D3.
SpineCandidate came from hub H2 + terminal T4 + path P1.
SeedCandidate came from slot S7 on branch B2.
Growth step consumed atom A42 at step 17.
```

Provenance enables failure diagnosis and no-good records.

## 12.2 Debug output

Every run should be able to emit structured debug artifacts.

Canonical debug run folder:

```text
outputs/debug_runs/<run_id>/
  input.json
  run_config.json
  program_instance.json
  regions.json
  atoms.json
  graphs.json
  spine_candidates.json
  seed_candidates.json
  growth_steps.json
  pre_repair_validation.json
  repair_operations.json
  post_repair_validation.json
  failure_records.json
  no_good_records.json
  final_or_invalid_layout.json
  stage_04_regions.svg
  stage_08_spine.svg
  stage_10_growth.svg
  stage_13_final.svg
```

Generated debug outputs are not intended to be committed by default.

## 12.3 Visualization

Visualization is mandatory for development, but it is infrastructure, not a Stage.

Initial visual commitment:

- SVG-first renderer,
- stable layer order,
- stable visual vocabulary,
- one renderer shared across stages.

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

Initial visual vocabulary:

| Concept | Suggested visual treatment |
|---|---|
| footprint | black outline |
| anchors | dark neutral fill / hatch |
| regions | light translucent fills |
| atoms | thin grid / light strokes |
| spine/access | blue stroke |
| public/hub | yellow/orange fill |
| private | green fill |
| wet/service | purple fill |
| invalid/failure | red outline or overlay |
| leftover/sliver | gray or red hatch |

---

# 13. Target model

A **Target** is a typology/domain adapter.

Core framework stays general:

- floor root,
- hub,
- spine,
- cluster,
- terminal,
- region,
- atom,
- seed,
- access policy,
- domain constraints.

Target adapter defines:

- available program elements,
- default floor root behavior,
- allowed access topologies,
- cluster rules,
- domain constraints,
- access/dependency policies,
- exterior/contact requirements.

Initial Targets:

| Target | Description | Initial status |
|---|---|---|
| Apartment Unit | Single-floor unit with entry root | primary implementation target |
| Multi-floor House | Floor roots from entry/stair landing; persistent anchors matter | schema-supported early, implemented later |
| Hotel Floor | Repeated rooms along corridor/lobby | future adapter |
| Warehouse | Aisle/loading/storage access model | future adapter |
| Office | Work zones, meeting rooms, service/support spaces | future adapter |

Apartment-first principle:

> Implement apartment first, but keep the core floor-rooted and anchor-compatible.

---

# 14. Multi-floor handling

Multi-floor is not a different room model. It is composition over floor-level layout with persistent anchors and floor-specific roots.

Core concepts:

| Concept | Meaning |
|---|---|
| `BuildingInput` | Multi-floor container. |
| `FloorInput` | Per-floor footprint, root hints, anchors, and floor program. |
| `PersistentAnchor` | Building-global object projected into one or more floors. |
| `FloorProgram` | Program assigned to one floor. |
| `FloorRoot` | Entry/landing/core point used as root for that floor. |

Examples:

```text
Apartment unit:
  floor_root = unit entry
```

```text
Two-floor house:
  floor 1 root = external entry
  floor 2 root = stair landing
```

```text
Hotel floor:
  floor_root = elevator/stair lobby
```

Implementation rule:

- Early apartment work may use empty anchors.
- Core schema must still include anchor fields from Step 02.
- Stage 03 remains a no-op until persistent anchors are implemented.
- Step 14 makes Stage 03 non-trivial for multi-floor cases.

---

# 15. Implementation Step map

Implementation Steps are development milestones. They are not the same as runtime Stages.

| Step | Name | Main responsibility | Related Stages / systems |
|---:|---|---|---|
| 01 | Project Skeleton / Global Docs | repo structure, root docs, naming rules, initial `.gitignore` | project setup |
| 02 | Core Schema / Run Config / Debug Output Contract | dataclass stubs, run config, debug output contract, empty anchor fields | Stage 00 foundation, cross-cutting |
| 03 | Visualization Renderer / Visual Vocabulary | SVG renderer, layer order, color/label convention | cross-cutting visualization |
| 04 | Apartment Fixtures / Target Adapter | apartment footprints, programs, initial target rules | Stage 00–02, Target model |
| 05 | Geometry Kernel / Atom Resolution Commitments | polygon utilities, units, atom size, door-edge thresholds | Stage 03–05 foundation |
| 06 | Program & Domain Constraint Engine | cardinality, area, min dimension, access policy gates | Stage 01–02, Stage 11/13 validation |
| 07 | Region / Atom Decomposition | decomposition candidates, atomization, sliver detection | Stage 04 |
| 08 | Graph Construction / Static Features / Role Scoring | contact graphs, feature fields, role scores | Stage 05–06 |
| 09 | Hub / Terminal / Spine Candidate Generation | hub/terminal candidates, spine paths, branch costs | Stage 07–08 |
| 10 | Slot / Seed / Patch Generation | slots, seeds, seed sets, boundary evidence | Stage 09 |
| 11 | Atom Growth | access-preserving atom growth | Stage 10 |
| 12 | Validation / Repair / FailureRecord | pre-repair validation, repair, post-repair validation, failure diagnosis | Stage 11–13 |
| 13 | Search Orchestrator / No-good Records | candidate pool, retry ladder, no-good store, search budget | orchestration outside Stage pipeline |
| 14 | Multi-floor Orchestration / Persistent Anchors | anchor projection, floor roots, multi-floor composition | Stage 03, multi-floor Target |

Step 12 should be planned internally as three subtasks:

```text
Step 12A. Pre-repair validation / defect report
Step 12B. Repair / rectangularization
Step 12C. Post-repair validation / FailureRecord
```

---

# 16. Repo file policy

Root global docs:

```text
000_Pipeline_Overview.md
000_Architecture_Decisions.md
000_Progress_Tracker.md
000_User_Profile.md      # maintained separately by the user
```

Step docs are created only while actively working on that Step.

Example:

```text
001_Step01_ProjectSkeleton_Plan.md
001_Step01_ProjectSkeleton_Tracker.md
```

When a Step is completed, its Step-specific files may move to:

```text
legacy/step01/
```

Legacy policy (H012, 2026-05-07): `legacy/stepNN/*.md` is treated as a frozen historical record. Relative links inside legacy docs are **not maintained** after archive — they may be broken (e.g., `000_Architecture_Decisions.md` would need `../../` prefix from `legacy/stepNN/`). This is intentional; legacy is for history, not live navigation.

Numbering rules:

- `000_*` = global docs,
- `001_*` to `014_*` = implementation Step files,
- Step 00 does not exist,
- Step number in prose uses two digits, e.g. Step 05,
- file prefix uses three digits, e.g. `005_Step05_GeometryKernel_Plan.md`,
- revisits use revision suffixes inside `legacy/stepXX/`, e.g. `_r02`.

---

# 17. Output and `.gitignore` policy

Generated outputs should not pollute version control.

Initial `.gitignore` policy:

```gitignore
__pycache__/
*.pyc
.venv/
.env

outputs/debug_runs/*
!outputs/debug_runs/.gitkeep

experiments/runs/*
!experiments/runs/.gitkeep

.cache/
.pytest_cache/
.mypy_cache/
.ruff_cache/

.DS_Store
```

Tracked by default:

- source code,
- fixtures,
- small hand-authored configs,
- global docs,
- active Step docs,
- selected tiny snapshots only when intentionally promoted.

Ignored by default:

- bulk debug JSON,
- generated SVGs,
- run outputs,
- caches,
- temporary experiment outputs.

---

# 18. Summary

proto3 uses separate structural concepts:

```text
Step
  development roadmap unit

Stage
  internal candidate pipeline unit

Search Orchestrator
  control loop outside the Stage pipeline

Cross-cutting Infrastructure
  provenance, visualization, debug output, no-good store, run config

Target
  typology/domain adapter
```

The canonical runtime pipeline is:

```text
Stage 00 Input Normalization
→ Stage 01 Program Instantiation
→ Stage 02 Domain Feasibility Gate
→ Stage 03 Persistent Anchor Projection
→ Stage 04 Region / Atom Decomposition
→ Stage 05 Graph Construction
→ Stage 06 Static Features / Role Scoring
→ Stage 07 Hub / Terminal Candidate Generation
→ Stage 08 Spine / Access Tree Generation
→ Stage 09 Slot / Seed / Patch Generation
→ Stage 10 Atom Growth
→ Stage 11 Pre-repair Validation / Defect Detection
→ Stage 12 Repair / Rectangularization
→ Stage 13 Post-repair Validation / Failure Diagnosis / Output Assembly
```

Candidate Search is not Stage 14. It is the Search Orchestrator that runs and reruns Stage 00–13.

The implementation roadmap is Step 01–14. Step 00 does not exist.
