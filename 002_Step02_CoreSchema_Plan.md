# 002 Step 02 — Core Schema Port Plan

Status: Active
Type: Step plan
Branch: `step02-coreschema` (D005 — regression risk + integration work triggers fire)
Last updated: 2026-05-25

---

## 0. Purpose

Step 02 lands the typed Python implementation of the D001 external
contract — every dataclass that `run()` reads as input, threads through
the pipeline, and returns as output. **No algorithm code in Step 02.**
Cell module ports happen in Step 03; this Step defines the *spec*
those ports will compile against.

Cross-references:

- `docs/000_Pipeline_Overview.md` §2 — typed contract sketches that
  drive this Step's implementation (the dataclass shapes in §2.1 / §2.2
  / §2.3 are the source of truth).
- `docs/000_Architecture_Decisions.md`:
  - **D001** — external contract (this Step is its implementation).
  - **D003** — triple-layer geometry (atom / region / room).
  - **D004** — 7-class `Role` taxonomy.
  - **D005** — solo-mode workflow (justifies branching).
  - **D006** — output directory convention (serialize.py is the basis
    for `manifest.json` + stage trace serialization).
  - **`proto3:D012`** carry — start with dataclasses, no pydantic.
  - **`proto3:D017`** carry — strict `Literal` validation at deserialization.
  - **`proto3:D018`** carry — unified `LabeledRoomLayout(valid=...)` output.
  - **`proto3:D020`** carry — `DomainGateFailure` exception hierarchy.
  - **`proto3:D023`** carry — required-only cardinality / area summation.
- `legacy/step01/001_Step01_Skeleton_Plan.md` — predecessor Step.
- `docs/000_Progress_Tracker.md` — current status.
- Companion: `002_Step02_CoreSchema_Tracker.md`.

---

## 1. Definition of Done

| Item | Verification |
|---|---|
| All schema types importable from `room_layout.schema` | `python -c "from room_layout.schema import ShapeInput, FloorShape, ShapePart, VerticalAnchor, ProgramRequest, SpaceUnitSpec, LabeledRoomLayout, LabeledFloorLayout, LabeledRoom, Door, FailureRecord, Role, InputRole"` |
| Input dataclasses are `frozen=True`; output dataclasses are mutable | code review + tests attempt mutation |
| `__post_init__` structural validation enforced | unit tests — invalid inputs raise `ValueError` |
| `ShapePart` orientation: exterior CCW + holes CW (right-hand rule) | unit test |
| `VerticalAnchor.kind` ↔ `host_role` consistency enforced | unit test — invalid combinations raise `ValueError` |
| `SpaceUnitSpec.role` cannot be `"corridor"` (uses `InputRole` Literal) | unit test — `role="corridor"` raises at construction (mypy / runtime) |
| `SpaceUnitSpec.anchor_id` required when `role == "vertical_circulation"` | unit test |
| Strict `Literal` validation per `proto3:D017` at deserialization | unit test — `from_dict` rejects out-of-range Literal |
| Serialization round-trip: `from_dict(cls, to_dict(obj)) == obj` for all dataclasses | unit tests, one per type |
| `validate_input(shape, program)` returns `list[FailureRecord]` (empty on success) | unit tests covering each cross-ref scenario |
| `DomainGateFailure` + subclasses (`Area`/`Dim`/`AccessSchema`) defined per `proto3:D020` shape | code present + smoke tests |
| `pytest` green locally (`python -m pytest`) and in CI | local + GitHub Actions |
| `ruff check .` + `ruff format --check .` green | local + CI |
| CI green on `step02-coreschema` branch | `gh run list --limit 1` |
| CI green on `main` after `git merge --no-ff step02-coreschema` | `gh run list` |
| Viz status documented (Step 02: no viz output — schema only) | Tracker §2 + close summary |
| `docs/000_Progress_Tracker.md` §1 + §2 + §3 updated to reflect Step 02 close + Step 03 kickoff | docs review |

---

## 2. 결정 기록

| ID | Title | Decision |
|---|---|---|
| **S02-D1** | Branch policy | `step02-coreschema` branch per D005 (two triggers fire — regression risk + integration work touching all downstream modules). Merge `--no-ff` to `main` at Step close. |
| **S02-D2** | Module structure | `src/room_layout/schema/` subpackage with files split by concern: `geometry.py`, `program.py`, `output.py`, `failure.py`, `serialize.py`, `validators.py`. `__init__.py` re-exports the public surface. (vs single `schema.py` — split scales better as types grow.) |
| **S02-D3** | Dataclass mutability | Input types `frozen=True` (`ShapeInput`, `FloorShape`, `ShapePart`, `VerticalAnchor`, `ProgramRequest`, `SpaceUnitSpec`). Output types mutable (`LabeledRoomLayout`, `LabeledFloorLayout`, `LabeledRoom`). `FailureRecord` is mutable (algorithm appends as failures discover). |
| **S02-D4** | Serialization approach | Hand-written generic `to_dict()` / `from_dict()` in `schema/serialize.py`. Uses `dataclasses.fields()` + `typing.get_type_hints()`. No external dep (`proto3:D012` carry — no pydantic). |
| **S02-D5** | Polygon type | `shapely.Polygon` direct, no wrapper. `serialize.py` provides `polygon_to_coords` / `coords_to_polygon` for JSON. |
| **S02-D6** | `__post_init__` scope | *Structural* validation only (single-object invariants): non-empty list, `Ring` ≥ 3 points, exterior CCW + holes CW, `VerticalAnchor.kind ↔ host_role`, `SpaceUnitSpec.role == "vertical_circulation"` ⇒ `anchor_id` set. Cross-references go to `validators.py`. |
| **S02-D7** | `ShapeInput.name` | Required `str` (matches Cell + proto3 precedent; forces debugging hygiene; one extra kwarg is cheap). |
| **S02-D8** | Migration character | Cell → new schema is a **semantic migration**, not a mechanical port. Cell `ShapeInput(name, parts)` lacks multi-floor + vertical anchors; new schema is a superset. Step 03 ports Cell modules to use this new schema (S01-Q1 "Refactor in-place"). |
| **S02-D9** | `corridor` role in input | `SpaceUnitSpec.role` typed as `InputRole = Literal["public", "private", "service", "wet", "hub", "vertical_circulation"]` — `"corridor"` excluded. Output `LabeledRoom.role: Role` (full 7-class). Type system rejects `SpaceUnitSpec(role="corridor")` at construction; runtime cannot bypass without explicit cast. (D004: `corridor` is *output of carve*, not pre-seeded.) |
| **S02-D10** | Anchor validation split | Structural validation in `VerticalAnchor.__post_init__` (`kind ↔ host_role` matrix). Cross-reference validation (`SpaceUnitSpec.anchor_id` resolves to an existing `VerticalAnchor.id` with matching `host_role`) in `validators.validate_input(shape, program)` — separate function called by Step 06's `run()`. |
| **S02-D11** | `LabeledRoomLayout.debug_artifacts` | **Removed** from the output dataclass (per the Pipeline §2.3 cleanup). Stage trace emission is entirely callback-based (Step 06 `on_stage`); `run()` is pure (no filesystem). `LabeledRoomLayout` carries only the in-memory result + `failure_records` + `provenance`. |
| **S02-D12** | `holes` orientation | Exterior CCW + interior holes CW (shapely right-hand rule, IFC `IfcArbitraryProfileDefWithVoids` convention). Enforced in `ShapePart.__post_init__`. |
| **S02-D13** | Viz status | **No viz output this Step** — schema only, nothing to visualize. Placeholder `room_layout.viz` package unchanged from Step 01. First renderers arrive Step 03 (matplotlib bridge). |

---

## 3. Directory structure (target state after Step 02)

```text
Study_RoomLayout/
├── 002_Step02_CoreSchema_Plan.md           (this file)
├── 002_Step02_CoreSchema_Tracker.md        (companion)
├── legacy/
│   ├── .gitkeep
│   └── step01/                              (new — D016 H011 archive)
│       ├── 001_Step01_Skeleton_Plan.md
│       └── 001_Step01_Skeleton_Tracker.md
├── src/
│   └── room_layout/
│       ├── __init__.py                      (existing — may re-export schema after Step 02 close)
│       ├── schema/                          (new package)
│       │   ├── __init__.py                  (public re-exports)
│       │   ├── geometry.py                  (ShapeInput, FloorShape, ShapePart,
│       │   │                                 VerticalAnchor, Ring, Point)
│       │   ├── program.py                   (ProgramRequest, SpaceUnitSpec,
│       │   │                                 Role, InputRole)
│       │   ├── output.py                    (LabeledRoomLayout, LabeledFloorLayout,
│       │   │                                 LabeledRoom, Door)
│       │   ├── failure.py                   (FailureRecord + DomainGateFailure
│       │   │                                 + Area/Dim/AccessSchema subclasses)
│       │   ├── serialize.py                 (to_dict / from_dict + strict Literal
│       │   │                                 + polygon_to_coords / coords_to_polygon)
│       │   └── validators.py                (validate_input(shape, program))
│       └── viz/                             (existing — unchanged)
│           └── __init__.py
└── tests/
    ├── golden/                              (existing — empty)
    │   └── .gitkeep
    ├── test_smoke.py                        (existing)
    ├── test_schema_geometry.py              (new)
    ├── test_schema_program.py               (new)
    ├── test_schema_output.py                (new)
    ├── test_schema_failure.py               (new)
    ├── test_schema_serialize.py             (new)
    └── test_schema_validators.py            (new)
```

---

## 4. Work items

Each = one atomic commit on `step02-coreschema`. Order designed so each
commit leaves the tree in a green-CI state.

### 4.1 Plan + Tracker land + Step 01 archive

Files:

- `002_Step02_CoreSchema_Plan.md` (this file).
- `002_Step02_CoreSchema_Tracker.md` (companion).
- `git mv 001_Step01_Skeleton_Plan.md legacy/step01/` (`proto3:D016` H011).
- `git mv 001_Step01_Skeleton_Tracker.md legacy/step01/`.

Commit: `docs(step02): plan + tracker + archive step01`.

Verification: both Step 02 docs at repo root; both Step 01 docs under
`legacy/step01/`; `git status` clean.

### 4.2 Schema subpackage scaffold

Files: `src/room_layout/schema/__init__.py` plus the 6 empty module
files (`geometry.py`, `program.py`, `output.py`, `failure.py`,
`serialize.py`, `validators.py`). `__init__.py` contains only a
docstring + `# Re-exports populated in subsequent work items.`

Commit: `feat(step02): scaffold schema subpackage`.

Verification: `python -c "import room_layout.schema"` succeeds.

### 4.3 Geometry types

Implement in `geometry.py`:

- Type aliases: `Point = tuple[float, float]`, `Ring = tuple[Point, ...]`.
- `@dataclass(frozen=True) ShapePart` — `exterior: Ring`, `holes: tuple[Ring, ...] = ()`. `__post_init__` enforces ≥ 3 points + exterior CCW + holes CW (using `shapely.geometry.polygon.LinearRing.is_ccw`).
- `@dataclass(frozen=True) VerticalAnchor` — `id`, `kind`, `footprint_polygon`, `floor_range`, `host_role`. `__post_init__` enforces `kind ↔ host_role` matrix per S02-D10.
- `@dataclass(frozen=True) FloorShape` — `level`, `parts`, `floor_to_floor_height`. `__post_init__` enforces non-empty `parts`.
- `@dataclass(frozen=True) ShapeInput` — `name: str` (required, S02-D7), `floors: list[FloorShape]`, `vertical_anchors: list[VerticalAnchor]`. `__post_init__` enforces non-empty `name` and `floors`.

Update `schema/__init__.py` to re-export.

Commit: `feat(step02): geometry types`.

Verification: unit-test stubs pass for each type's instantiation and `__post_init__` rejection paths.

### 4.4 Program types

Implement in `program.py`:

- `Role = Literal["public", "private", "service", "wet", "hub", "corridor", "vertical_circulation"]` (full 7-class per D004).
- `InputRole = Literal["public", "private", "service", "wet", "hub", "vertical_circulation"]` (`corridor` excluded, S02-D9).
- `@dataclass(frozen=True) SpaceUnitSpec` — `id`, `role: InputRole`, `usage: str | None`, `area_target_m2`, `area_min_m2`, `min_dimension_m`, `required: bool`, `anchor_id: str | None`. `__post_init__` enforces `role == "vertical_circulation"` ⇒ `anchor_id is not None`.
- `@dataclass(frozen=True) ProgramRequest` — `target_type`, `floor_programs: dict[int, list[SpaceUnitSpec]]`. `__post_init__` enforces non-empty `floor_programs`.

Update `schema/__init__.py`.

Commit: `feat(step02): program types`.

### 4.5 Output + Failure types

Implement in `output.py`:

- `@dataclass Door` — placeholder per S01-Q2 (v1 always `None`). Fields TBD; for now `kind: Literal["interior", "exterior"]` + `position` placeholder.
- `@dataclass LabeledRoom` — `id`, `polygon: shapely.Polygon`, `role: Role`, `usage: str | None`, `area_m2`, `doors: list[Door] | None = None`, `anchor_id: str | None = None`.
- `@dataclass LabeledFloorLayout` — `level`, `rooms`, `corridor_polygons`.
- `@dataclass LabeledRoomLayout` — `valid: bool`, `floors`, `failure_records`, `provenance` (`debug_artifacts` REMOVED per S02-D11).

Implement in `failure.py`:

- `@dataclass FailureRecord` — `code: str`, `stage: str`, `message: str`, `data: dict`. Mutable; lists accumulate.
- `class DomainGateFailure(Exception)` — carries a `FailureRecord`.
- Subclasses: `AreaGateFailure`, `DimGateFailure`, `AccessSchemaFailure` per `proto3:D020`.

Update `schema/__init__.py`.

Commit: `feat(step02): output + failure types`.

### 4.6 Serialization helpers + strict Literal validation

Implement in `serialize.py`:

- `to_dict(obj) -> Any` — recursive: dataclass → field dict; shapely `Polygon` → `{"exterior": [...], "holes": [...]}`; list / tuple / dict / Literal / primitive pass-through.
- `from_dict(cls: type, data: Any) -> Any` — recursive inverse. Resolves `typing.Literal` via `get_origin` / `get_args`. **Raises `ValueError` on out-of-range Literal** per `proto3:D017`.
- `to_json(obj) -> str`, `from_json(cls, s) -> Any` thin wrappers.
- Helpers: `polygon_to_coords(p)`, `coords_to_polygon(d)`.

Commit: `feat(step02): serialize + strict literal validation`.

### 4.7 Cross-reference validators

Implement in `validators.py`:

- `validate_input(shape: ShapeInput, program: ProgramRequest) -> list[FailureRecord]`. Empty list = ok. Checks:
  - every `SpaceUnitSpec.anchor_id` resolves to a `VerticalAnchor.id`.
  - every resolved anchor has `host_role == "vertical_circulation"`.
  - every `VerticalAnchor` with `host_role == "vertical_circulation"` has at least one matching `SpaceUnitSpec` in some floor program (else the anchor is unused — warn, not error).
  - every `FloorShape.level` referenced in `ProgramRequest.floor_programs.keys()` exists in `ShapeInput.floors`.
- Each failure is a `FailureRecord` with a stable `code: str` (e.g., `"ANCHOR_ID_NOT_FOUND"`, `"ANCHOR_HOST_ROLE_MISMATCH"`, `"PROGRAM_FLOOR_NOT_IN_SHAPE"`).

Commit: `feat(step02): cross-ref validators`.

### 4.8 Schema unit tests

Implement under `tests/`:

- `test_schema_geometry.py` — `ShapePart` orientation (CCW exterior + CW holes), `VerticalAnchor` kind↔host_role matrix, `FloorShape` non-empty parts, `ShapeInput` non-empty floors + name.
- `test_schema_program.py` — `Role` / `InputRole` separation, `SpaceUnitSpec` anchor_id rule for vertical_circulation, `ProgramRequest` non-empty floor_programs.
- `test_schema_output.py` — `LabeledRoomLayout` mutable / instantiation / `valid=False` carries non-empty `failure_records`.
- `test_schema_failure.py` — exception hierarchy + `FailureRecord` round-trip.
- `test_schema_serialize.py` — `to_dict`/`from_dict` round-trip for every dataclass + strict Literal rejection.
- `test_schema_validators.py` — each `validate_input` failure code with a fixture that triggers it; success case with valid input.

Commit: `test(step02): schema unit tests`.

### 4.9 Step close + merge to `main`

- Tracker §1 / §2 all checked.
- Tracker §4 close summary filled (built / surprises / deferred).
- `docs/000_Progress_Tracker.md` §1 / §2 / §3 updated (Step 02 closed; Step 03 next).
- `src/room_layout/__init__.py` optionally adds `from .schema import (...)` re-export if desired.
- Commit on branch: `chore(step02): close — update progress tracker`.
- Switch to `main`: `git switch main && git merge --no-ff step02-coreschema && git push`.
- CI green on `main` confirms merge.
- `git branch -d step02-coreschema` after merge.

---

## 5. 의도적으로 하지 않는 것

- **Algorithm code** — Cell Phase 3–8 port lands in Step 03.
- **Cell module schema refactor** — Step 03 changes Cell modules to import from `room_layout.schema` (this Step's output).
- **target_rules JSON loader + `TargetAdapter`** — Step 05.
- **`run()` entry point + `on_stage` callback + `StageOutput` + `manifest.json` writer** — Step 06.
- **`Door` field detail** — placeholder dataclass only; populated when Step 06's corridor carving produces door positions (or deferred further per S01-Q2).
- **Matplotlib renderers** — Step 03 development bridge.
- **Canonical SVG renderer + `pipeline.gif`** — Step 07.
- **`ResearchBIM_synthetic-bim` `Building` / `Storey` adapter** — Step 08, post-v1.
- **Multi-floor orchestrator** — Step 09, post-v1.
- **Viz output for Step 02** — schema only; nothing to render (S02-D13).
- **`src/room_layout/__init__.py` re-export decisions** — held until Step close (work item 4.9). v1 default: re-export the public surface so callers do `from room_layout import ShapeInput` *or* `from room_layout.schema import ShapeInput`.

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| 13 frozen decisions × ~12 dataclasses × validation rules = high churn during implementation | Plan §2 frozen on branch start. Deviations recorded in Tracker §3 with rationale; large deviation triggers re-discuss before continuing. |
| Strict `Literal` validation surfaces fixture / test mistakes late | Step 02 has no inherited fixtures; all fixture data is born under strict validation. Step 03 must coerce Cell fixtures through the new strict path. |
| Generic `to_dict` / `from_dict` edge cases (`Union[A, B]`, deeply nested generics, `Polygon` inside `dict`) | Implement most common cases first; add unit tests as each new pattern lands. Document limitations in `serialize.py` docstring. |
| Cross-ref validator misses a case → algorithm crashes downstream with confusing trace | Each `code` in `FailureRecord` has a fixture + test. Add new `code` only with a matching test. |
| `shapely.geometry.polygon.LinearRing.is_ccw` misbehaves on degenerate rings | Reject degenerate rings (< 3 points, zero area) before checking orientation. Document the check order in `ShapePart.__post_init__`. |
| `ruff format` rewrites docstring-only files in noisy ways | Step 01 already lint-clean; ruff exclude / format settings stable. New code matches the established style. |
| `dev` extras drift (matplotlib import in viz, but viz is empty) | `test_smoke.py::test_viz_subpackage_imports_without_matplotlib` continues catching the regression. Step 02 doesn't add to viz. |
| Branch lifetime > 1 day → drift from `main` | Rebase / merge `main` into branch every commit cycle. Step 02 is single-developer so realistic drift is small. |

---

## 7. Next-Step linkage

Step 02 close → **Step 03 (Geometry pipeline port)** kickoff.

At Step 03's §4.1 commit (per `proto3:D016` H011 deferred-archive pattern):

- `git mv 002_Step02_CoreSchema_Plan.md legacy/step02/`
- `git mv 002_Step02_CoreSchema_Tracker.md legacy/step02/`
- Write `003_Step03_GeometryPipeline_Plan.md` + Tracker.

Step 03 will:

- Move Cell Phase 3–8 modules from `archive/celllayout/algorithm/celllayout_tf/` into `src/room_layout/stages/` (or similar).
- Refactor each module's schema references from Cell's internal types to `from room_layout.schema import ShapeInput, ShapePart, ...` (S02-D8 semantic migration).
- Add per-stage matplotlib renderers under `src/room_layout/viz/` (the development bridge — Step 07 swaps in canonical SVG).
- Establish golden tests under `tests/golden/<fixture>/` using `validate_input` + semantic-equality comparison (per Pipeline §5.1 wording).

---

## A. (Reserved) Appendix — inline file contents

_Not used this Step._ All work items 4.2–4.8 produce code written
directly; no single-use scaffolding needed.
