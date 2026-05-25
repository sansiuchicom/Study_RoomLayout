"""Failure types — `FailureRecord` + `DomainGateFailure` exception hierarchy.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.5 + proto3:D020
(exception hierarchy pattern) + proto3:D018 (failure_records on
output).

Two complementary mechanisms:

1. `FailureRecord` — data class accumulated in
   `LabeledRoomLayout.failure_records`. The algorithm appends one
   per failed gate check. Surfaces in `valid=False` results.

2. `DomainGateFailure` + subclasses — exception hierarchy raised by
   gate-check helpers when a stage cannot continue. The Step 06
   `run()` catches these at stage boundaries, records the carried
   `FailureRecord`, and decides whether to short-circuit or
   continue with the next stage.

Stable failure `code` strings (initial set, expanded as Step 04+
gates land)::

    "ANCHOR_ID_NOT_FOUND"            (validators.py)
    "ANCHOR_HOST_ROLE_MISMATCH"      (validators.py)
    "PROGRAM_FLOOR_NOT_IN_SHAPE"     (validators.py)
    # area / dim / access gates land in Step 04+
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
