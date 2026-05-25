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
- [ ] **4.4** Program types (`ProgramRequest` / `SpaceUnitSpec` / `Role`)
- [ ] **4.5** Output + Failure types (`LabeledRoomLayout` / `LabeledFloorLayout` / `LabeledRoom` / `Door` / `FailureRecord` + exception hierarchy)
- [ ] **4.6** Serialization helpers (`to_dict` / `from_dict` + strict `Literal` validation per `proto3:D017`)
- [ ] **4.7** Cross-reference validators (`validate_input(shape, program)`)
- [ ] **4.8** Schema unit tests (6 `test_schema_*.py` files)
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

---

## 4. Close summary

_Populated at Step close (work item 4.9). One-paragraph retro: what
was actually built, any surprises, any items pushed forward to a later
Step._
