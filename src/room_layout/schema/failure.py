"""Failure types — `FailureRecord` + `DomainGateFailure` exception hierarchy.

Placeholder. Populated in work item 4.5.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.5.

Will define:

- ``@dataclass FailureRecord`` — ``code: str`` (stable identifier),
  ``stage: str``, ``message: str``, ``data: dict``. Mutable (lists
  accumulate as failures surface during pipeline execution).
- ``class DomainGateFailure(Exception)`` — base; carries a
  ``FailureRecord``.
- Subclasses per ``proto3:D020``: ``AreaGateFailure``,
  ``DimGateFailure``, ``AccessSchemaFailure``. Additional subclasses
  added as Step 04 / Step 06 surface new failure modes.

Stable ``code`` strings (initial set, expanded in later Steps)::

    "ANCHOR_ID_NOT_FOUND"            (validators)
    "ANCHOR_HOST_ROLE_MISMATCH"      (validators)
    "PROGRAM_FLOOR_NOT_IN_SHAPE"     (validators)
    # area / dim / access gates land in Step 04+
"""
