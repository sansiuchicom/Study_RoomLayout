# 000 Architecture Decisions

Status: Canonical decision record
Scope: accepted decisions for `Study_RoomLayout`, invariant vs replaceable choices, and the inherited-decision audit from the two predecessor repos
Last updated: 2026-05-24

---

## 0. Purpose

This document records accepted decisions for `Study_RoomLayout`.

Use this file to answer:

- What has already been decided?
- What is an architecture invariant?
- What is only a first-pass implementation choice?
- Why was the decision made?
- What should be changed only with deliberate review?

Canonical framework and pipeline definitions live in `000_Pipeline_Overview.md`.
Current implementation status lives in `000_Progress_Tracker.md`.

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

To be defined as decisions land. Predecessor invariants (proto3 D006 / D007 / D011)
are explicitly under audit — see §4.

---

# 3. Accepted decisions

_To be written._ First three decisions inherited from the predecessor reconciliation:

- D001 — Input contract: `ShapeInput` (parts preserved) over unioned footprint.
- D002 — Drop spine-first invariant; adopt seed-first growth + corridor carving.
- D003 — `Region` is a geometric primitive (~3 m² atom cluster); architectural
  role (`public` / `private` / ...) lives on the room layer, not the region.

Full text pending in next pass.

---

# 4. Inherited-decision audit (proto3 D001–D023)

_To be written._ For each proto3 decision: **Carry / Modify / Drop** + rationale.
Known drops: D006 (region/atom dual layer as defined), D007 (spine-first),
D011 (access-preserving growth).

---

# 5. Decision history appendix

| Date | Decision | Change |
|---|---|---|
| 2026-05-24 | repo init | scaffold only — no decisions yet committed |
