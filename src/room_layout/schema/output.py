"""Output types — `Door`, `LabeledRoom`, `LabeledFloorLayout`, `LabeledRoomLayout`.

Plan reference: ``002_Step02_CoreSchema_Plan.md`` §4.5 + S02-D3
(mutable outputs) / S02-D11 (no `debug_artifacts`).

All dataclasses here are **mutable** — the algorithm populates them
incrementally across stages (rooms appended per floor, failures
accumulated per gate check) and finalizes with the
`LabeledRoomLayout(valid=True | False, ...)` discriminator
(proto3:D018).

`valid=False ⇒ non-empty failure_records` is an architectural contract
enforced by the algorithm + a 4.8 unit test, NOT by `__post_init__`,
since the algorithm's natural pattern is "construct with
`valid=True` + empty failures, then accumulate and flip on first
failure" — a construction-time check would force an awkward
two-step initialize.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from shapely.geometry import Polygon

from room_layout.schema.failure import FailureRecord
from room_layout.schema.program import Role

DoorKind = Literal["interior", "exterior"]


@dataclass
class Door:
    """Door on a room boundary — v1 placeholder per S01-Q2.

    `LabeledRoom.doors` is always `None` in v1; the field exists so the
    output shape is forward-compatible with Step 06 corridor carving
    (which will produce door positions on room↔corridor boundaries).
    """

    kind: DoorKind
    position: tuple[float, float] | None = None


@dataclass
class LabeledRoom:
    """One carved room — polygon + role + (optional) anchor link.

    `anchor_id` is set iff `role == "vertical_circulation"`, linking
    back to the input `VerticalAnchor` that hosts this room.
    """

    id: str
    polygon: Polygon
    role: Role
    usage: str | None
    area_m2: float
    doors: list[Door] | None = None
    anchor_id: str | None = None
    # 구성 region 폴리곤(거의 사각형 타일) — 다운스트림 region-aligned 후처리(욕실/주방
    # 쪼개기, PlanBIM 145 §8) 가 소비. ``init=False`` 라 ``to_dict`` 직렬화/골든 무영향
    # (S07-D6: 출력 기하는 ``polygon`` 단일 출처, region_polygons 는 보조 메타).
    region_polygons: tuple[Polygon, ...] = field(default=(), init=False)


@dataclass
class LabeledFloorLayout:
    """One floor's carved layout — rooms + corridor polygons."""

    level: int
    rooms: list[LabeledRoom] = field(default_factory=list)
    corridor_polygons: list[Polygon] = field(default_factory=list)


@dataclass
class LabeledRoomLayout:
    """The full result of `run()` — valid flag + per-floor layouts + provenance.

    No `debug_artifacts` field (S02-D11): stage trace emission is
    entirely callback-based at Step 06 (`run(..., on_stage=...)`).
    `run()` is pure (no filesystem) and `LabeledRoomLayout` carries
    only the in-memory result.
    """

    valid: bool
    floors: list[LabeledFloorLayout] = field(default_factory=list)
    failure_records: list[FailureRecord] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
