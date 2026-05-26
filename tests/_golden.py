"""Polygon-aware golden test comparator (skeleton).

Placeholder. Populated in work item 4.4.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.4 + S03-D5.

Will provide:

- ``assert_layout_equal(actual, expected, *, tol=1e-6,
  update_mode=False)`` — deep-compare two dataclass instances (or
  collections of them). Float fields use ``math.isclose(rel_tol=0,
  abs_tol=tol)``; ``shapely.Polygon`` fields use
  ``equals_exact(other, tol)``. When ``update_mode=True``, rewrites
  the expected JSON file in place and returns silently — used by the
  ``pytest --update-goldens`` flag (S03-D10).

The ``--update-goldens`` pytest flag itself is wired in a sibling
``conftest.py`` hook (also work item 4.4); it sets ``update_mode=True``
on assertions via a pytest fixture.
"""

from typing import Any


def assert_layout_equal(
    actual: Any,
    expected: Any,
    *,
    tol: float = 1e-6,
    update_mode: bool = False,
) -> None:
    """Deep-equality assertion for layout outputs (skeleton).

    Implementation lands in work item 4.4. Raising here so any
    accidental use between 4.2–4.3 surfaces loudly rather than
    silently passing.
    """
    raise NotImplementedError("assert_layout_equal: populated in work item 4.4")
