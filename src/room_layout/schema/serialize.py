"""Serialization helpers — generic `to_dict` / `from_dict` + strict `Literal` validation.

Placeholder. Populated in work item 4.6.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.6.

Will define:

- ``to_dict(obj) -> Any`` — recursive: dataclass → field dict; shapely
  ``Polygon`` → ``{"exterior": [...], "holes": [...]}``; list / tuple /
  dict / ``Literal`` / primitive pass-through.
- ``from_dict(cls: type, data: Any) -> Any`` — recursive inverse.
  Resolves ``typing.Literal`` via ``get_origin`` / ``get_args``;
  **raises ``ValueError`` on out-of-range Literal value** per
  ``proto3:D017`` carry.
- ``to_json(obj) -> str``, ``from_json(cls, s) -> Any`` — thin
  ``json.dumps`` / ``json.loads`` wrappers around the dict pair.
- ``polygon_to_coords(p: Polygon) -> dict``,
  ``coords_to_polygon(d: dict) -> Polygon`` — explicit shapely helpers
  (called by the generic functions when the type is ``Polygon``).

Design notes (S02-D4):

- Hand-written generic functions over ``dataclasses.fields()`` +
  ``typing.get_type_hints()``. No external dependency (``proto3:D012``
  carry — no pydantic).
- Edge cases (``Union[A, B]``, deeply nested generics) handled as they
  surface in real data; documented limitations live in this module's
  docstring after first encounter.
"""
