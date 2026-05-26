"""Polygon-aware golden test comparator.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.4 + S03-D5
(per-stage JSON goldens + Polygon-aware tolerance) + S03-D10
(``pytest --update-goldens`` regeneration flag).

API:

    assert_layout_equal(actual, expected, *, tol=1e-6,
                        update_mode=False, golden_path=None)

- Deep-compares dataclass instances field-by-field, recursing through
  list / tuple / dict containers.
- ``shapely.Polygon`` fields use ``equals_exact(other, tol)``.
- ``float`` fields use ``math.isclose(abs_tol=tol, rel_tol=0)``.
- ``bool``, ``int``, ``str``, ``None`` use exact ``==``.
- Container types are strict: ``list`` ≠ ``tuple``.

When ``update_mode=True`` (driven by the ``--update-goldens`` pytest
flag via the ``tests/conftest.py`` hook):

- ``golden_path`` is required; the function serializes
  ``to_dict(actual)`` to that path as indented JSON and returns
  **silently** (no comparison performed).
- A loud "[GOLDEN UPDATE]" line is printed per write so accidental
  enables are visible (use ``pytest --update-goldens -s`` to see them
  uncaptured).

Mismatches raise ``AssertionError`` with a path like
``layout.floors[0].rooms[2].polygon`` to locate the diff fast.
"""

import dataclasses
import json
import math
from pathlib import Path
from typing import Any

from shapely.geometry import Polygon

from room_layout.schema import to_dict


def assert_layout_equal(
    actual: Any,
    expected: Any,
    *,
    tol: float = 1e-6,
    update_mode: bool = False,
    golden_path: Path | None = None,
) -> None:
    """Deep-equality assertion for layout outputs.

    See module docstring for full semantics.
    """
    if update_mode:
        if golden_path is None:
            raise ValueError("assert_layout_equal: update_mode=True requires golden_path")
        print(f"[GOLDEN UPDATE] rewriting {golden_path}")
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        with golden_path.open("w", encoding="utf-8") as f:
            json.dump(to_dict(actual), f, indent=2, ensure_ascii=False)
            f.write("\n")
        return

    _compare(actual, expected, tol=tol, path="")


def _compare(actual: Any, expected: Any, *, tol: float, path: str) -> None:
    """Recursive deep-compare. ``path`` accumulates the location for diagnostics."""

    # Polygon — equals_exact with tolerance. Check first because Polygon is
    # not a dataclass and would otherwise fall through to the bottom branches.
    if isinstance(actual, Polygon) or isinstance(expected, Polygon):
        if not (isinstance(actual, Polygon) and isinstance(expected, Polygon)):
            raise AssertionError(
                f"{path or '<root>'}: type mismatch — "
                f"actual={type(actual).__name__}, expected={type(expected).__name__}"
            )
        if not actual.equals_exact(expected, tol):
            raise AssertionError(
                f"{path or '<root>'}: Polygon differs beyond tol={tol}\n"
                f"  actual:   {actual.wkt[:200]}\n"
                f"  expected: {expected.wkt[:200]}"
            )
        return

    # Dataclass instance (not the class itself).
    if dataclasses.is_dataclass(actual) and not isinstance(actual, type):
        if not (dataclasses.is_dataclass(expected) and type(actual) is type(expected)):
            raise AssertionError(
                f"{path or '<root>'}: dataclass type mismatch — "
                f"actual={type(actual).__name__}, "
                f"expected={type(expected).__name__}"
            )
        for f in dataclasses.fields(actual):
            _compare(
                getattr(actual, f.name),
                getattr(expected, f.name),
                tol=tol,
                path=f"{path}.{f.name}" if path else f.name,
            )
        return

    # list / tuple — strict type match (list ≠ tuple).
    if isinstance(actual, (list, tuple)):
        if type(actual) is not type(expected):
            raise AssertionError(
                f"{path or '<root>'}: container type mismatch — "
                f"actual={type(actual).__name__}, "
                f"expected={type(expected).__name__}"
            )
        if len(actual) != len(expected):
            raise AssertionError(
                f"{path or '<root>'}: length mismatch — "
                f"actual={len(actual)}, expected={len(expected)}"
            )
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            _compare(a, e, tol=tol, path=f"{path}[{i}]")
        return

    # dict — key-by-key.
    if isinstance(actual, dict):
        if not isinstance(expected, dict):
            raise AssertionError(
                f"{path or '<root>'}: type mismatch — "
                f"actual=dict, expected={type(expected).__name__}"
            )
        actual_keys = set(actual.keys())
        expected_keys = set(expected.keys())
        if actual_keys != expected_keys:
            only_a = sorted(actual_keys - expected_keys, key=repr)
            only_e = sorted(expected_keys - actual_keys, key=repr)
            parts = []
            if only_a:
                parts.append(f"only in actual: {only_a}")
            if only_e:
                parts.append(f"only in expected: {only_e}")
            raise AssertionError(f"{path or '<root>'}: dict key mismatch — {'; '.join(parts)}")
        for k in actual_keys:
            _compare(actual[k], expected[k], tol=tol, path=f"{path}[{k!r}]")
        return

    # bool — strict identity. (bool is a subclass of int, so handle before float.)
    if isinstance(actual, bool) or isinstance(expected, bool):
        if actual is not expected:
            raise AssertionError(
                f"{path or '<root>'}: bool mismatch — actual={actual!r}, expected={expected!r}"
            )
        return

    # float — tolerance compare (accepts int promotion).
    if isinstance(actual, float) or isinstance(expected, float):
        if not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
            raise AssertionError(
                f"{path or '<root>'}: number type mismatch — "
                f"actual={type(actual).__name__}, "
                f"expected={type(expected).__name__}"
            )
        if not math.isclose(actual, expected, abs_tol=tol, rel_tol=0):
            raise AssertionError(
                f"{path or '<root>'}: float differs beyond tol={tol} — "
                f"actual={actual!r}, expected={expected!r}"
            )
        return

    # Everything else (int / str / None / etc.) — exact compare.
    if actual != expected:
        raise AssertionError(
            f"{path or '<root>'}: value mismatch — actual={actual!r}, expected={expected!r}"
        )
