"""Serialization — `to_dict` / `from_dict` / `to_json` / `from_json`.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.6 + proto3:D012
(no pydantic) / proto3:D017 (strict Literal at deserialization) /
S02-D4 (hand-written generic serializer) / S02-D5 (Polygon direct).

**Strict-by-default contract** (resolved in chat 2026-05-25):

- Extra keys in `from_dict`: **rejected** (`ValueError`). Forces typo
  catches in fixtures + explicit migration on field renames. If
  forward-compat with old saved data ever needed, add a `strict=False`
  kwarg here later.
- Missing required fields: **rejected**. Fields with `default` or
  `default_factory` may be omitted (caller relies on the default).
- Out-of-range `Literal`: **rejected** (proto3:D017).
- `dict[str, Any]` / `Any`-typed values: **pass-through**, no recursion
  on `from_dict`. JSON-safety is the caller's responsibility for these
  fields (e.g. `LabeledRoomLayout.provenance`, `FailureRecord.data`).

**Dispatch table** — `to_dict` (runtime-type) and `from_dict`
(annotation-type) handle:

- dataclass — `dataclasses.fields()` + `typing.get_type_hints()`
- `shapely.Polygon` — `{"exterior": [[x, y], ...], "holes": [[[x, y], ...], ...]}`
- primitives — `int`, `float`, `str`, `bool`, `None`
- `list[T]` — recurse on `T`
- `tuple[T, ...]` (variadic) — recurse on `T` per element
- `tuple[T1, T2, ...]` (fixed) — recurse positionally
- `dict[K, V]` — recurse on values; `K` parses str→int/float as needed
  (JSON normalizes object keys to str)
- `Literal[a, b, ...]` — must be in args
- `Union[...]` / `T | None` — try each arm; None routes to `NoneType`
- `Any` — pass-through

Anything outside this set raises `TypeError`. Adding a new supported
shape ⇒ add a branch here + a unit test in `test_schema_serialize.py`.
"""

import dataclasses
import json
import typing
from types import NoneType, UnionType
from typing import Any, Literal, Union, get_args, get_origin

from shapely.geometry import Polygon


def polygon_to_coords(p: Polygon) -> dict[str, Any]:
    """Polygon → `{"exterior": [[x, y], ...], "holes": [[[x, y], ...], ...]}`.

    Strips shapely's auto-closing duplicate end-point so the ring length
    matches the input convention used by `ShapePart`.
    """
    return {
        "exterior": [list(xy) for xy in p.exterior.coords[:-1]],
        "holes": [[list(xy) for xy in r.coords[:-1]] for r in p.interiors],
    }


def coords_to_polygon(d: dict[str, Any]) -> Polygon:
    """Inverse of `polygon_to_coords`. Missing `holes` defaults to empty."""
    if "exterior" not in d:
        raise ValueError("coords_to_polygon: missing 'exterior' key")
    return Polygon(d["exterior"], d.get("holes", []))


def to_dict(obj: Any) -> Any:
    """Convert a schema object to a JSON-safe Python value.

    Pure runtime-type dispatch; doesn't inspect annotations. Callers
    pass schema instances directly.
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Polygon):
        return polygon_to_coords(obj)
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        # Skip init=False fields: they are derived/cached state rebuilt in
        # __post_init__ (e.g. graph adjacency indexes), not part of the
        # serializable model — emitting them breaks round-trip and JSON
        # (e.g. tuple-keyed lookup dicts).
        return {f.name: to_dict(getattr(obj, f.name)) for f in dataclasses.fields(obj) if f.init}
    if isinstance(obj, (list, tuple)):
        return [to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    raise TypeError(f"to_dict: unsupported type {type(obj).__name__}")


def from_dict(cls: Any, data: Any) -> Any:
    """Convert a JSON-safe Python value back into a `cls` instance.

    `cls` may be a dataclass, a generic alias (`list[T]`, `dict[K, V]`,
    etc.), a `Literal[...]`, a `Union[...]`, `Polygon`, `Any`, or a
    primitive type. Strict (see module docstring).
    """
    if cls is Any:
        return data

    if cls is NoneType or cls is type(None):
        if data is not None:
            raise ValueError(f"from_dict: expected None, got {type(data).__name__}")
        return None

    origin = get_origin(cls)

    if origin is Literal:
        allowed = get_args(cls)
        if data not in allowed:
            raise ValueError(f"from_dict: value {data!r} not in Literal{list(allowed)}")
        return data

    if origin is Union or origin is UnionType:
        args = get_args(cls)
        if data is None:
            if type(None) in args:
                return None
            raise ValueError(f"from_dict: None not allowed for {cls}")
        errors: list[str] = []
        for arg in args:
            if arg is type(None):
                continue
            try:
                return from_dict(arg, data)
            except (ValueError, TypeError) as e:
                errors.append(f"{arg}: {e}")
        raise ValueError(f"from_dict: value {data!r} matches no arm of {cls}; tried: {errors}")

    if cls is Polygon:
        if not isinstance(data, dict):
            raise ValueError(f"from_dict: Polygon requires dict, got {type(data).__name__}")
        return coords_to_polygon(data)

    if origin is list:
        (elem_t,) = get_args(cls)
        if not isinstance(data, list):
            raise ValueError(f"from_dict: list[...] requires list, got {type(data).__name__}")
        return [from_dict(elem_t, x) for x in data]

    if origin is tuple:
        args = get_args(cls)
        if not isinstance(data, (list, tuple)):
            raise ValueError(
                f"from_dict: tuple[...] requires list/tuple, got {type(data).__name__}"
            )
        if len(args) == 2 and args[1] is Ellipsis:
            elem_t = args[0]
            return tuple(from_dict(elem_t, x) for x in data)
        if len(data) != len(args):
            raise ValueError(f"from_dict: tuple expects {len(args)} elements, got {len(data)}")
        return tuple(from_dict(t, x) for t, x in zip(args, data, strict=True))

    if origin is dict:
        key_t, val_t = get_args(cls)
        if not isinstance(data, dict):
            raise ValueError(f"from_dict: dict[...] requires dict, got {type(data).__name__}")
        # `Any`-typed values pass through (per contract — see module docstring).
        if val_t is Any:
            return {_coerce_key(key_t, k): v for k, v in data.items()}
        return {_coerce_key(key_t, k): from_dict(val_t, v) for k, v in data.items()}

    if cls is bool:
        if not isinstance(data, bool):
            raise ValueError(f"from_dict: expected bool, got {type(data).__name__}")
        return data
    if cls is int:
        # Reject bool (a subclass of int) — schema "int" fields must not
        # silently accept True/False.
        if isinstance(data, bool) or not isinstance(data, int):
            raise ValueError(f"from_dict: expected int, got {type(data).__name__}")
        return data
    if cls is float:
        # Accept int as float (JSON has no 0 vs 0.0 distinction).
        if isinstance(data, bool) or not isinstance(data, (int, float)):
            raise ValueError(f"from_dict: expected float, got {type(data).__name__}")
        return float(data)
    if cls is str:
        if not isinstance(data, str):
            raise ValueError(f"from_dict: expected str, got {type(data).__name__}")
        return data

    if dataclasses.is_dataclass(cls):
        if not isinstance(data, dict):
            raise ValueError(f"from_dict: {cls.__name__} requires dict, got {type(data).__name__}")
        hints = typing.get_type_hints(cls)
        field_names = {f.name for f in dataclasses.fields(cls)}
        extra = set(data.keys()) - field_names
        if extra:
            raise ValueError(f"from_dict: {cls.__name__} extra keys not in schema: {sorted(extra)}")
        kwargs: dict[str, Any] = {}
        for f in dataclasses.fields(cls):
            if not f.init:
                continue  # derived/cached field — rebuilt by __post_init__
            field_type = hints[f.name]
            if f.name in data:
                kwargs[f.name] = from_dict(field_type, data[f.name])
            elif (
                f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING
            ):
                continue  # use dataclass-supplied default
            else:
                raise ValueError(f"from_dict: {cls.__name__} missing required field {f.name!r}")
        return cls(**kwargs)

    raise TypeError(f"from_dict: unsupported target type {cls!r}")


def _coerce_key(key_t: Any, k: Any) -> Any:
    """JSON normalizes object keys to str — parse back to declared key type."""
    if key_t is str or key_t is Any:
        return k
    if key_t is int:
        return int(k) if isinstance(k, str) else k
    if key_t is float:
        return float(k) if isinstance(k, str) else k
    return k


def to_json(obj: Any) -> str:
    """`to_dict` + `json.dumps`. Compact wire format."""
    return json.dumps(to_dict(obj))


def from_json(cls: Any, s: str) -> Any:
    """`json.loads` + `from_dict`. Inverse of `to_json` modulo JSON
    normalizations handled inside `from_dict` (int↔float, tuple→list)."""
    return from_dict(cls, json.loads(s))
