"""Dimension policy + quantum helpers.

Placeholder. Populated in work item 4.6.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.6 + S03-D8.

Will define:

- ``@dataclass DimensionPolicy`` — quantum grid parameters consumed by
  ``atomize`` / ``regionize`` / ``shape_gate``. ``__post_init__``
  enforces positive quanta and a sensible min-dimension.
- ``is_quantum_aligned(value, q)`` — float-tolerant alignment check.
- ``split_interval(...)`` — interval subdivision against the quantum.

Internal — not re-exported from ``room_layout`` per S03-D6 (algorithmic
parameter, not part of the D001 public contract). Stages import from
here directly.
"""
