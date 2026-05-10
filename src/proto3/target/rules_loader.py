"""TargetRules JSON loader + validation (S06-D4).

`load_target_rules(path)` parses a target-rules JSON file into a typed
`TargetRules` instance, raising `ValueError` for any of:

- file unreadable / not valid JSON
- missing or extra top-level keys
- wrong type for any field
- unknown role keys (must be in `proto3.schema.program.Role`)
- out-of-range values (density_factor, negative areas, negative cardinality)

This is the single point of contact between proto3 and external rule
files; once validated, downstream code can trust the `TargetRules` shape.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, get_args

from proto3.schema.program import Role

from .base import TargetRules

_ALLOWED_ROLES: frozenset[str] = frozenset(get_args(Role))
_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {"min_cardinality", "default_min_area_m2", "density_factor", "requires_single_floor"}
)


def _is_real_number(x: Any) -> bool:
    # bool is a subclass of int — exclude it explicitly so True/False don't
    # masquerade as numeric values silently.
    return type(x) in (int, float)


def _is_real_int(x: Any) -> bool:
    return type(x) is int


def load_target_rules(path: Path) -> TargetRules:
    """Load + validate a target-rules JSON file. Raise ValueError on any defect."""
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

    keys = set(data.keys())
    missing = _REQUIRED_FIELDS - keys
    if missing:
        raise ValueError(f"target_rules missing required fields {sorted(missing)} (path={p})")
    extra = keys - _REQUIRED_FIELDS
    if extra:
        raise ValueError(f"target_rules has unknown fields {sorted(extra)} (path={p})")

    df = data["density_factor"]
    if not _is_real_number(df) or not (0 < df <= 1):
        raise ValueError(
            f"target_rules.density_factor must be a number in (0, 1], got {df!r} (path={p})"
        )

    rsf = data["requires_single_floor"]
    if not isinstance(rsf, bool):
        raise ValueError(
            f"target_rules.requires_single_floor must be bool, got {type(rsf).__name__} (path={p})"
        )

    mc = data["min_cardinality"]
    if not isinstance(mc, dict):
        raise ValueError(
            f"target_rules.min_cardinality must be object, got {type(mc).__name__} (path={p})"
        )
    for role, count in mc.items():
        if role not in _ALLOWED_ROLES:
            raise ValueError(
                f"target_rules.min_cardinality role {role!r} not in {sorted(_ALLOWED_ROLES)} (path={p})"
            )
        if not _is_real_int(count) or count < 0:
            raise ValueError(
                f"target_rules.min_cardinality[{role!r}] must be int ≥ 0, got {count!r} (path={p})"
            )

    da = data["default_min_area_m2"]
    if not isinstance(da, dict):
        raise ValueError(
            f"target_rules.default_min_area_m2 must be object, got {type(da).__name__} (path={p})"
        )
    for role, area in da.items():
        if role not in _ALLOWED_ROLES:
            raise ValueError(
                f"target_rules.default_min_area_m2 role {role!r} not in {sorted(_ALLOWED_ROLES)} (path={p})"
            )
        if not _is_real_number(area) or area < 0:
            raise ValueError(
                f"target_rules.default_min_area_m2[{role!r}] must be number ≥ 0, got {area!r} (path={p})"
            )

    return TargetRules(
        min_cardinality=dict(mc),
        default_min_area_m2={k: float(v) for k, v in da.items()},
        density_factor=float(df),
        requires_single_floor=rsf,
    )
