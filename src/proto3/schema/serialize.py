"""Serialization helpers: to_dict, from_dict, to_json, from_json (S02-D3).

Free functions, not methods (SRP — dataclass = data, helper = policy).
Single place that handles custom types as they are introduced in later
Steps (Polygon/Enum/datetime/numpy etc.).

from_dict input policy (S02-D13):
  - non-dict `data` for a dataclass `cls` -> TypeError
  - unknown keys in `data` -> ValueError (set strict_unknown=False to allow)
  - missing keys (cls field absent in data) -> dataclass default kicks in
    (S02-D4 backward-compat path; the only silent-fallback case)
"""
from __future__ import annotations

import json
import types
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Literal, get_args, get_origin, get_type_hints


def to_dict(obj: Any) -> Any:
    """dataclass → dict, list/tuple → list, dict → dict, primitives unchanged.

    Custom types (Enum, Polygon, datetime, numpy) are added here as they
    enter the schema in later Steps.
    """
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_dict(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, (list, tuple)):
        return [to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    return obj


def from_dict(cls: type, data: Any, *, strict_unknown: bool = True) -> Any:
    """Reverse of to_dict using type hints. See module docstring for input policy.

    strict_unknown=False is the escape hatch for the rare case where a field
    was *removed* from the schema and old serialized files must still load.
    Backward-compat for *added* fields needs no opt-out — that is the
    missing-key default path.
    """
    if not is_dataclass(cls):
        return data
    if not isinstance(data, dict):
        raise TypeError(
            f"{cls.__name__} expects dict for from_dict, got {type(data).__name__}"
        )
    known = {f.name for f in fields(cls)}
    if strict_unknown:
        unknown = set(data) - known
        if unknown:
            raise ValueError(
                f"unknown keys for {cls.__name__}: {sorted(unknown)}"
            )
    try:
        hints = get_type_hints(cls)
    except Exception:
        hints = {f.name: f.type for f in fields(cls)}
    kwargs: dict[str, Any] = {}
    for f in fields(cls):
        if f.name in data:
            kwargs[f.name] = _reconstruct(
                hints.get(f.name, f.type), data[f.name], strict_unknown=strict_unknown
            )
        # else: dataclass default kicks in — backward-compat for new fields
    return cls(**kwargs)


def _reconstruct(type_hint: Any, value: Any, *, strict_unknown: bool = True) -> Any:
    """Reconstruct one value given its type hint."""
    if value is None:
        return None
    # nested dataclass
    if isinstance(type_hint, type) and is_dataclass(type_hint):
        return from_dict(type_hint, value, strict_unknown=strict_unknown)
    origin = get_origin(type_hint)
    args = get_args(type_hint)
    # list[T] — recurse into element type so list[tuple[...]] / list[Dataclass] both work
    if origin is list and isinstance(value, list):
        if args:
            return [_reconstruct(args[0], v, strict_unknown=strict_unknown) for v in value]
        return list(value)
    # tuple[T, ...] — JSON has no tuple; list incoming, recurse on element type
    if origin is tuple and isinstance(value, list):
        if args:
            return tuple(_reconstruct(args[0], v, strict_unknown=strict_unknown) for v in value)
        return tuple(value)
    # X | None / X | Y  (PEP 604 union)
    if origin is types.UnionType:
        for arg in args:
            if arg is type(None):
                continue
            return _reconstruct(arg, value, strict_unknown=strict_unknown)
    # Literal[...] — strict allowed-values check (D017)
    if origin is Literal:
        if value not in args:
            raise ValueError(
                f"value {value!r} not in allowed Literal values {list(args)!r}"
            )
        return value
    # primitive / dict / str / int / unknown
    return value


def to_json(obj: Any, path: Path | None = None, *, indent: int = 2) -> str:
    """Serialize to JSON string. If path given, also write (creates parents)."""
    s = json.dumps(to_dict(obj), indent=indent, ensure_ascii=False)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(s, encoding="utf-8")
    return s


def from_json(cls: type, source: str | Path, *, strict_unknown: bool = True) -> Any:
    """Deserialize from JSON string or file Path.

    Pass a Path to read from disk; pass a str for an in-memory JSON document.
    """
    text = source.read_text(encoding="utf-8") if isinstance(source, Path) else source
    return from_dict(cls, json.loads(text), strict_unknown=strict_unknown)
