# 002 Step 02 — Core Schema Port Tracker

Status: Active
Type: Step tracker
Branch: `step02-coreschema`
Last updated: 2026-05-25

Mirrors Plan §4 work items 1:1 in §1 checklist (per `proto3:D016`).

---

## 1. Plan §4 work items

- [ ] **4.1** Plan + Tracker land + `git mv` Step 01 docs to `legacy/step01/`
- [ ] **4.2** Schema subpackage scaffold (`schema/__init__.py` + 6 empty modules)
- [ ] **4.3** Geometry types (`ShapeInput` / `FloorShape` / `ShapePart` / `VerticalAnchor` + `Ring`, `Point`)
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

_Populated as Step proceeds. Per-work-item notes go here when a choice
made during execution differs from or refines Plan §2._

---

## 4. Close summary

_Populated at Step close (work item 4.9). One-paragraph retro: what
was actually built, any surprises, any items pushed forward to a later
Step._
