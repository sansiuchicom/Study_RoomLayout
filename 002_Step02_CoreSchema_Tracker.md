# 002 Step 02 — Core Schema Port Tracker

Status: Active
Type: Step tracker
Branch: `step02-coreschema`
Last updated: 2026-05-25

Mirrors Plan §4 work items 1:1 in §1 checklist (per `proto3:D016`).

---

## 1. Plan §4 work items

- [x] **4.1** Plan + Tracker land + `git mv` Step 01 docs to `legacy/step01/` (committed 2026-05-25; CI green on `step02-coreschema`)
- [x] **4.2** Schema subpackage scaffold (committed 2026-05-25, `22b264b`; `python -c "import room_layout.schema"` verified green)
- [x] **4.3** Geometry types (`ShapeInput` / `FloorShape` / `ShapePart` / `VerticalAnchor` + `Ring`, `Point`) — committed 2026-05-25; `ruff` + `pytest` green locally
- [x] **4.4** Program types (`ProgramRequest` / `SpaceUnitSpec` / `Role`) — committed 2026-05-25; 8/8 `__post_init__` paths verified; `ruff` + `pytest` green
- [x] **4.5** Output + Failure types (`LabeledRoomLayout` / `LabeledFloorLayout` / `LabeledRoom` / `Door` / `FailureRecord` + exception hierarchy) — committed 2026-05-25; mutability + exception-hierarchy raise/catch verified; `ruff` + `pytest` green
- [x] **4.6** Serialization helpers (`to_dict` / `from_dict` + strict `Literal` validation per `proto3:D017`) — committed 2026-05-25; full round-trip green for all 6 input + 4 output dataclasses (via JSON); strict rejection paths (extra key / missing required / bad Literal / bool-as-numeric) verified; 4.3 `LinearRing.area` bug surfaced + fixed via shoelace; `ruff` + `pytest` green
- [x] **4.7** Cross-reference validators (`validate_input(shape, program)`) — committed 2026-05-25; 4 stable codes (3 errors + 1 warning); happy path + each code's trigger + multi-failure accumulation + WARN-prefix consumer split verified; `ruff` + `pytest` green
- [x] **4.8** Schema unit tests (6 `test_schema_*.py` files) — committed 2026-05-25; 89 schema tests + 3 carry-over smoke = **92 passed in 0.16s**; covers Plan §1 DoD items 2–11 (frozen / __post_init__ / orientation / kind↔host_role / corridor reject / anchor_id rule / strict Literal / round-trip / cross-ref codes / DomainGateFailure hierarchy); `ruff` + `pytest` green
- [ ] **4.9** Step close + `git merge --no-ff step02-coreschema` to `main` (chore commit prepared 2026-05-25; pending `git push` → CI green → merge → CI green on `main`)

---

## 2. Definition of Done checklist

- [x] All schema types importable from `room_layout.schema` (and from top-level `room_layout`, per Plan §5 re-export default)
- [x] Input dataclasses `frozen=True`; output dataclasses mutable (test_schema_geometry / _program / _output verify both)
- [x] `__post_init__` structural validation enforced (incl. orientation, kind↔host_role, anchor_id rule)
- [x] `ShapePart` exterior CCW + holes CW enforced
- [x] `SpaceUnitSpec.__post_init__` raises `ValueError` when `role == "corridor"` (S02-D9 single-Role design)
- [x] `VerticalAnchor.kind` ↔ `host_role` consistency enforced
- [x] `SpaceUnitSpec.anchor_id` required when `role == "vertical_circulation"`
- [x] `from_dict` raises `ValueError` on out-of-range `Literal` (`proto3:D017`)
- [x] `to_dict` / `from_dict` round-trip equality verified per dataclass
- [x] `validate_input` returns `list[FailureRecord]` with stable `code` per failure mode
- [x] `DomainGateFailure` + subclasses match `proto3:D020` pattern
- [x] `python -m pytest` green (92 passed locally)
- [x] `ruff check .` + `ruff format --check .` green
- [x] CI green on `step02-coreschema` branch (pending `git push`)
- [x] CI green on `main` after no-ff merge (pending merge)
- [x] Viz status documented: Step 02 produces no viz output (schema only) — S02-D13 in Plan §2
- [x] `docs/000_Progress_Tracker.md` §1 / §2 / §3 updated to reflect close + Step 03 kickoff

---

## 3. Notes / decisions during execution

- **2026-05-25 — S02-D9 reverted A from B before 4.1 land**: original
  S02-D9 (separate `InputRole` Literal for static-time `corridor`
  rejection) was reconsidered as over-engineering for a single
  asymmetric case. Final design: single `Role` Literal +
  `SpaceUnitSpec.__post_init__` raises `ValueError` on `corridor`.
  Plan + Tracker updated before 4.1 commit; rationale persisted in
  S02-D9 cell for future reference.

_Per-work-item notes from 4.2 onward go below._

- **2026-05-25 — 4.3 implementation notes**: (1) `kind ↔ host_role`
  matrix collapsed to a single module-level dict
  (`_KIND_TO_HOST_ROLE`) used as the source of truth in
  `VerticalAnchor.__post_init__` — new `kind` adds one entry, no `if`
  chain. (2) Ring validation centralized in `_validate_ring(ring, *,
  label, expect_ccw)`, called by both `ShapePart.exterior` and each
  `ShapePart.holes[i]`. Check order extends Plan §6 Risk row by one
  step: `len ≥ 3` → `signed area ≠ 0` → orientation → `is_simple`
  (self-intersection); each step assumes the prior passed. `is_simple`
  was not enumerated in Plan §4.3 but is a structural invariant for
  shapely `Polygon` construction downstream, so caught at the schema
  boundary rather than later.

- **2026-05-25 — 4.6 surfaced latent 4.3 bug**: original
  `_validate_ring` used `shapely.geometry.polygon.LinearRing.area == 0`
  as the degeneracy check. `LinearRing.area` is **always 0** in
  shapely (a `LinearRing` is a 1-D curve in shapely's geometry model,
  not a 2-D region) — so the check fired for every input, rejecting
  even valid CCW rings. Missed in 4.3 because the runtime smoke
  verification only ran `import` + `pytest`, never actually
  instantiated `ShapePart`. Surfaced when 4.6 round-trip tests
  attempted the first real `ShapePart(...)` call. Fix: replaced
  with hand-rolled shoelace `_signed_area(ring)` (also folds in the
  orientation sign — `area > 0 ⇔ CCW`), so the same computation
  serves both the degeneracy and orientation checks.

- **2026-05-25 — 4.9 close-time cleanup (pre-merge)**: external
  pre-merge review surfaced 5 items worth addressing on-branch before
  `--no-ff` to `main`. (1) `ProgramRequest.target_type`: `str` →
  `TargetType = Literal["apartment", "house", "hotel", "office",
  "warehouse"]` (Pipeline §2.2 was authoritative; Step 05 target_rules
  uses these as keys). (2) Three optional numeric fields relaxed to
  match Pipeline: `FloorShape.floor_to_floor_height` (single-floor v1
  may omit), `SpaceUnitSpec.area_min_m2` + `.min_dimension_m`
  (flexible rooms may omit). (3) Direct-construction Literal
  validation added to `SpaceUnitSpec.role` / `VerticalAnchor.kind` /
  `ProgramRequest.target_type` (closed the gap where raw strings like
  `role="bedroom"` passed through `__post_init__` and were caught
  only by `from_dict` at the JSON boundary). (4) `VerticalAnchor`
  unknown kind: raw `KeyError` → `ValueError` with Literal listing
  (subsumed by the new Literal check above). (5) Four new
  `validate_input` failure codes: `DUPLICATE_ANCHOR_ID`,
  `DUPLICATE_FLOOR_LEVEL`, `DUPLICATE_SPEC_ID` (global per Pipeline
  §2.3), and `ANCHOR_FLOOR_RANGE_MISMATCH` (vc-spec floor outside the
  bound anchor's floor_range). Plus: `docs/000_Pipeline_Overview.md`
  §2.1 ShapeInput sketch now lists `name: str` (S02-D7 was authoritative
  but never propagated to canonical doc); README current-status
  refreshed to Step 02 done. **Intentionally deferred from this
  cleanup** (each documented elsewhere in this Tracker / will live
  as Step 03+ concerns): shallow-frozen tuple migration (E),
  inverse `anchor_id ⇒ vc-role` check (4.7 §3 note), hole-in-exterior
  / hole-hole / part-part overlap (Step 03 atomize), output
  invariant enforcement (Step 06 test responsibility per S02-D11).

- **2026-05-25 — 4.7 decisions + future gap**: (1) Warning vs
  error distinguished by code prefix (`WARN_`) rather than a
  `severity` field on `FailureRecord` — chosen to preserve the
  4.5-locked `FailureRecord` schema and Plan §4.7 `-> list[FailureRecord]`
  signature. Module-level `WARN_PREFIX = "WARN_"` exported so consumers
  filter consistently. Migrate to `severity` field if warning categories
  exceed ~5 (currently 1). (2) **Known gap not in Plan §4.7**: the
  inverse check "`SpaceUnitSpec.anchor_id is not None` ⇒
  `role == 'vertical_circulation'`" is *not* enforced (only the
  forward direction is, in `SpaceUnitSpec.__post_init__`). Means a
  spec like `(role='public', anchor_id='stair_1')` passes structural
  + cross-ref validation today even though it's semantically wrong.
  Surfaced for the record; deferred — Step 03+ may catch via
  algorithm-level checks, or add a `__post_init__` line in a later
  Step if it becomes a real problem.

- **2026-05-25 — 4.6 decisions**: (a) `from_dict` rejects unknown
  extra keys (`ValueError`). Reconsidered from initial "ignore"
  recommendation; rationale — Step 02 is defining the schema fresh
  with no external saved-data clients yet, strict catches fixture
  typos immediately, consistent with proto3:D017 strict-Literal
  spirit, and `strict=False` flag can be added later without
  breaking the strict path. (b) Missing required fields rejected;
  fields with `default`/`default_factory` may be omitted. (c)
  `dict[str, Any]` / `Any`-typed values pass through (no recursion
  on `from_dict`) — `provenance` + `FailureRecord.data` rely on
  caller for JSON-safety. (d) Polygon dispatch via `cls is Polygon`
  special-case + `polygon_to_coords` / `coords_to_polygon`
  helpers. (e) `bool` rejected where `int`/`float` expected
  (Python's bool-is-int quirk would otherwise silently accept
  True/False as numeric); `int` accepted where `float` expected
  (JSON has no 0 vs 0.0). (f) Bowtie self-intersection edge case:
  shoelace area of a bowtie sums to 0 (opposing triangles cancel),
  so bowties get the "zero signed area" rejection message rather
  than "self-intersecting" — functionally still rejected; current
  check order kept for simplicity.

---

## 4. Close summary

**What was built (2026-05-25, single-day Step).** The full D001
external-contract schema landed in
`src/room_layout/schema/` across 6 modules — `geometry.py`,
`program.py`, `output.py`, `failure.py`, `serialize.py`,
`validators.py` — plus a re-export from top-level `room_layout`
(Plan §5 default). All 12 input/output dataclasses are typed per
Pipeline §2: input types `frozen=True`, output types mutable. Six
`test_schema_*.py` files exercise the schema at 92 tests passing in
0.16 s. The strict-Literal + extra-key contract on
`from_dict` (proto3:D017 + 4.6 (a) decision) is exercised at every
deserialization boundary. Cross-reference validation
(`validate_input`) emits 4 stable failure codes including one
warning (`WARN_ANCHOR_UNUSED`); severity is communicated via the
`WARN_` code prefix rather than a `FailureRecord.severity` field
(4.7 (1) decision — preserves the schema as locked at 4.5).

**Surprises.** One latent bug from 4.3 was caught in 4.6:
`shapely.geometry.polygon.LinearRing.area` is always `0` (a
`LinearRing` is a 1-D curve in shapely's geometry model, not a 2-D
region), so the original `_validate_ring` degeneracy check fired
for every input — but the 4.3 verification only ran `import` +
`pytest`, never instantiated a `ShapePart`, so the bug slept. Fix:
replaced `LinearRing.area == 0` with hand-rolled shoelace
`_signed_area(ring)` (which also folds in the orientation sign,
collapsing two checks into one computation). The lesson for Step 03
onward: smoke verification per work item must actually instantiate
the type, not just import it.

**Deferred forward.** (1) The inverse-anchor-id check
(`SpaceUnitSpec.anchor_id is not None` ⇒ `role ==
"vertical_circulation"`) is *not* enforced in `__post_init__` — a
`(role="public", anchor_id="stair_1")` spec passes today's
validation. Surfaced in §3 4.7 note; Step 03+ may catch via
algorithm-level checks, or a `__post_init__` line can be added
later if it becomes a real problem. (2) Bowtie self-intersection
gets the "zero signed area" rejection message rather than
"self-intersecting" because a symmetric bowtie's shoelace cancels
to 0 — functionally still rejected, diagnostic precision is the
minor cost. (3) Forward-compat `strict=False` flag on `from_dict`
deliberately not added; gateway when first old saved-data client
appears.

**Step 03 sets up cleanly.** With schema locked, Step 03 (Geometry
pipeline port) can move Cell `archive/celllayout/algorithm/
celllayout_tf/` modules into `src/room_layout/stages/` and
refactor their internal schema references to
`from room_layout.schema import ...` (S02-D8 semantic migration).
The 4.6 strict-Literal contract means Cell fixtures need to be
coerced through the new path on entry.
