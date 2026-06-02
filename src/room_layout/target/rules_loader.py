"""TargetRules JSON loader + validation (Step 06 §4.3, S06-D4).

`load_target_rules(path)` parses a target-rules JSON file into a validated
`TargetRules`, raising `ValueError` (with the offending path) on any defect.

Validation split (S06-D2 option 가 — single source of truth):

- **JSON-boundary concerns live here**: file readable, valid JSON, an object,
  and every numeric value is **finite** (NaN / ±inf rejected — JSON parses
  `1e999` to `inf` and can carry `NaN`; an external file is untrusted, unlike
  a hand-built dataclass — S06-D4).
- **Domain invariants are delegated** to `TargetRules.__post_init__` (via
  `from_dict`): required/extra/unknown keys, types, `Role` Literal keys,
  `density_factor ∈ (0,1]`, non-negative cardinality, full `default_min_area_m2`
  Role map. The loader does not re-implement these; it re-raises whatever
  `from_dict` / the constructor reports, prefixed with the path.

This keeps the loader thin: it adds only what `from_dict` cannot see (the
file/parse layer + the finite check) and forwards the rest.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from room_layout.schema import TargetRules, from_dict


def _reject_nonfinite(obj: Any, path: Path, *, where: str = "") -> None:
    """Recursively reject NaN / ±inf anywhere in the parsed JSON (S06-D4).

    `bool` is a subclass of `int` but is never non-finite, so it passes
    through untouched.
    """
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError(
            f"target_rules: non-finite number {obj!r} at {where or '<root>'} (path={path})"
        )
    if isinstance(obj, dict):
        for k, v in obj.items():
            _reject_nonfinite(v, path, where=f"{where}.{k}" if where else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _reject_nonfinite(v, path, where=f"{where}[{i}]")


def load_target_rules(path: Path | str) -> TargetRules:
    """Load + validate a target-rules JSON file into a `TargetRules`.

    Raises:
        ValueError: file unreadable / malformed JSON / non-object root /
            non-finite number, or any domain defect surfaced by `from_dict`
            + `TargetRules.__post_init__` (re-raised with the path).
    """
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        raise ValueError(f"target_rules file unreadable (path={p}): {e}") from e
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"target_rules JSON malformed (path={p}): {e}") from e
    if not isinstance(data, dict):
        raise ValueError(
            f"target_rules JSON must be an object, got {type(data).__name__} (path={p})"
        )

    # JSON-boundary concern the dataclass path can't see (S06-D4).
    _reject_nonfinite(data, p)

    # Delegate every domain invariant to from_dict + TargetRules.__post_init__
    # (S06-D2 option 가); re-raise with the path so the failure is locatable.
    try:
        return from_dict(TargetRules, data)
    except ValueError as e:
        raise ValueError(f"target_rules invalid (path={p}): {e}") from e
