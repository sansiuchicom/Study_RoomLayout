"""Serialization helpers: to_dict, from_dict, to_json, from_json (S02-D3).

Free functions, not methods (SRP — dataclass = data, helper = policy).
Single place that handles custom types as they are introduced in later
Steps (Polygon/Enum/datetime/numpy etc.).

Backward-compat: from_dict treats missing keys as dataclass default
(S02-D4 RunConfig extension policy applies to all schemas).
"""
from __future__ import annotations

import json
import types
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints


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


def from_dict(cls: type, data: Any) -> Any:
    """Reverse of to_dict using type hints.

    Missing keys fall back to the dataclass default (S02-D4 extension policy)
    so older serialized files remain readable after schema additions.
    """
    if not is_dataclass(cls):
        return data
    try:
        hints = get_type_hints(cls)
    except Exception:
        hints = {f.name: f.type for f in fields(cls)}
    kwargs: dict[str, Any] = {}
    for f in fields(cls):
        if f.name in data:
            kwargs[f.name] = _reconstruct(hints.get(f.name, f.type), data[f.name])
        # else: dataclass default kicks in — backward-compat for new fields
    return cls(**kwargs)


def _reconstruct(type_hint: Any, value: Any) -> Any:
    """Reconstruct one value given its type hint."""
    if value is None:
        return None
    # nested dataclass
    if isinstance(type_hint, type) and is_dataclass(type_hint):
        return from_dict(type_hint, value)
    origin = get_origin(type_hint)
    args = get_args(type_hint)
    # list[T] — recurse into element type so list[tuple[...]] / list[Dataclass] both work
    if origin is list and isinstance(value, list):
        if args:
            return [_reconstruct(args[0], v) for v in value]
        return list(value)
    # tuple[T, ...] — JSON has no tuple; list incoming, recurse on element type
    if origin is tuple and isinstance(value, list):
        if args:
            return tuple(_reconstruct(args[0], v) for v in value)
        return tuple(value)
    # X | None / X | Y  (PEP 604 union)
    if origin is types.UnionType:
        for arg in args:
            if arg is type(None):
                continue
            return _reconstruct(arg, value)
    # primitive / dict / str / int / unknown
    return value


def to_json(obj: Any, path: Path | None = None, *, indent: int = 2) -> str:
    """Serialize to JSON string. If path given, also write (creates parents)."""
    s = json.dumps(to_dict(obj), indent=indent, ensure_ascii=False)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(s, encoding="utf-8")
    return s


def from_json(cls: type, source: str | Path) -> Any:
    """Deserialize from JSON string or file Path.

    Pass a Path to read from disk; pass a str for an in-memory JSON document.
    """
    text = source.read_text(encoding="utf-8") if isinstance(source, Path) else source
    return from_dict(cls, json.loads(text))
