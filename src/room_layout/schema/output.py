"""Output types — `LabeledRoomLayout`, `LabeledFloorLayout`, `LabeledRoom`, `Door`.

Placeholder. Populated in work item 4.5.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.5.

Will define (all *mutable* per S02-D3):

- ``@dataclass Door`` — v1 placeholder per S01-Q2 (``LabeledRoom.doors``
  is always ``None`` in v1);
- ``@dataclass LabeledRoom`` — ``polygon: shapely.Polygon``, ``role:
  Role``, ``usage: str | None``, ``area_m2``, ``doors: list[Door] |
  None = None``, ``anchor_id: str | None = None``;
- ``@dataclass LabeledFloorLayout`` — ``level``, ``rooms``,
  ``corridor_polygons``;
- ``@dataclass LabeledRoomLayout`` — ``valid: bool``, ``floors``,
  ``failure_records``, ``provenance``. NO ``debug_artifacts`` field
  (S02-D11) — stage trace emission is callback-based at Step 06,
  ``run()`` is pure.

proto3:D018 carry: ``valid: bool`` discriminates valid vs invalid;
``valid=False`` must carry non-empty ``failure_records`` (architectural
contract enforced by Stage 13 / Step 06 emitters, not by the dataclass
default).
"""
