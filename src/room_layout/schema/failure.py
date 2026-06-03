"""Failure types — `FailureRecord` + the raised-exception hierarchies.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.5 + proto3:D020
(exception hierarchy pattern) + proto3:D018 (failure_records on
output) + ``005_Step05_ProgramLayer_Plan.md`` S05-D5
(`ProgramInstantiationFailure`).

Two complementary mechanisms:

1. `FailureRecord` — data class accumulated in
   `LabeledRoomLayout.failure_records`. The algorithm appends one
   per failed gate check. Surfaces in `valid=False` results.

2. Three **sibling** raised-exception families (S05-D5 — kept distinct
   because they sit at different layers), each carrying a `FailureRecord`:

   - `ProgramInstantiationFailure` — raised by `stage01_program` when the
     program *itself* is malformed (empty/duplicate id, invalid role,
     insufficient required cardinality). Input-validation layer.
   - `DomainGateFailure` + subclasses — raised by the `stage02_gate`
     domain gates when a structurally-valid program *cannot physically be
     laid out* (area / dim / access / multi-floor). Feasibility layer.
   - `GeometryFailure` — raised at polygonization (Step 07 §4.2) when an
     output-geometry invariant is violated (a room's region union is
     disconnected or empty). Geometry-integrity layer.

   The Step 07 `run()` catches all three at stage boundaries, records the
   carried `FailureRecord`, and decides whether to short-circuit.

Stable failure `code` strings (expanded as gates land)::

    "ANCHOR_ID_NOT_FOUND"            (validators.py)
    "ANCHOR_HOST_ROLE_MISMATCH"      (validators.py)
    "PROGRAM_FLOOR_NOT_IN_SHAPE"     (validators.py)
    "ROOM_DISCONNECTED"              (polygonize.py — Step 07 §4.2)
    "ROOM_EMPTY"                     (polygonize.py — Step 07 §4.2)
    # program-instantiation + area / dim / access codes land in Step 05+
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FailureRecord:
    """One failed gate check — stable `code` + human `message` + data."""

    code: str
    stage: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)


class ProgramInstantiationFailure(Exception):
    """Raised by `stage01_program` when the program is malformed (S05-D5).

    Sibling of `DomainGateFailure`, not a subclass: this is the
    input-validation layer (the program request itself is wrong — empty or
    duplicate id, invalid role, insufficient required cardinality), distinct
    from the feasibility layer (`DomainGateFailure` — a valid program that
    cannot physically fit). Carries a `FailureRecord` like the gate failures.
    """

    def __init__(self, record: FailureRecord) -> None:
        super().__init__(record.message)
        self.record = record


class DomainGateFailure(Exception):
    """Base exception for any gate-check failure (proto3:D020).

    Carries a `FailureRecord` so the catch site can append it to
    `LabeledRoomLayout.failure_records` without re-deriving the
    code / stage / message.
    """

    def __init__(self, record: FailureRecord) -> None:
        super().__init__(record.message)
        self.record = record


class AreaGateFailure(DomainGateFailure):
    """Raised when an area-related gate (target / minimum) fails."""


class DimGateFailure(DomainGateFailure):
    """Raised when a dimensional gate (min_dimension) fails."""


class AccessSchemaFailure(DomainGateFailure):
    """Raised when access-graph / corridor schema requirements fail."""


class GeometryFailure(Exception):
    """Raised when an output-geometry invariant is violated (Step 07 §4.2).

    A third sibling family (alongside `ProgramInstantiationFailure` /
    `DomainGateFailure`): not a malformed program and not an infeasible one,
    but a geometry-integrity violation surfaced at polygonization — a room
    whose region union is disconnected (`ROOM_DISCONNECTED`) or has no
    regions (`ROOM_EMPTY`). Should-never-happen for well-grown rooms (0/137
    across the 33 goldens — growth only absorbs adjacent regions), so
    polygonization fails loud rather than silently repairing (S07-D5).
    Carries a `FailureRecord`; `run()` catches it → `valid=False`.
    """

    def __init__(self, record: FailureRecord) -> None:
        super().__init__(record.message)
        self.record = record
