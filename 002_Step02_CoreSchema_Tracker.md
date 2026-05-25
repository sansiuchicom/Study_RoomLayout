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
- [ ] **4.9** Step close + `git merge --no-ff step02-coreschema` to `main`

---

## 2. Definition of Done checklist

- [ ] All schema types importable from `room_layout.schema`
- [ ] Input dataclasses `frozen=True`; output dataclasses mutable
- [ ] `__post_init__` structural validation enforced (incl. orientation, kind↔host_role, anchor_id rule)
- [ ] `ShapePart` exterior CCW + holes CW enforced
- [ ] `SpaceUnitSpec.__post_init__` raises `ValueError` when `role == "corridor"` (S02-D9 single-Role design)
- [ ] `VerticalAnchor.kind` ↔ `host_role` consistency enforced
- [ ] `SpaceUnitSpec.anchor_id` required when `role == "vertical_circulation"`
- [ ] `from_dict` raises `ValueError` on out-of-range `Literal` (`proto3:D017`)
- [ ] `to_dict` / `from_dict` round-trip equality verified per dataclass
- [ ] `validate_input` returns `list[FailureRecord]` with stable `code` per failure mode
- [ ] `DomainGateFailure` + subclasses match `proto3:D020` pattern
- [ ] `python -m pytest` green
- [ ] `ruff check .` + `ruff format --check .` green
- [ ] CI green on `step02-coreschema` branch
- [ ] CI green on `main` after no-ff merge
- [ ] Viz status documented: Step 02 produces no viz output (schema only)
- [ ] `docs/000_Progress_Tracker.md` §1 / §2 / §3 updated to reflect close + Step 03 kickoff

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

_Populated at Step close (work item 4.9). One-paragraph retro: what
was actually built, any surprises, any items pushed forward to a later
Step._
