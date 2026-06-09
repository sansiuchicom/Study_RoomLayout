"""Cross-floor (building-level) checks — Step 10 (§4.4, S10-D6).

These validate concerns the per-floor pipeline cannot see. `run()` calls them
in its cross-floor PRE pass and *collects* any failure (never raises out —
proto3:D018); single-floor runs are unaffected (the checks are vacuous for one
floor, so the apartment path stays byte-identical).

`check_vertical_continuity` — **vertical** circulation must connect every floor.
It is defined on the **emitted** vc rooms (a floor emits a `vertical_circulation`
room only when *its* program carries a vc spec — `labeling.vc_rooms` is
spec-gated; S10-review #5), not on raw anchor `floor_range`s. It is vertical-only:
it does NOT assert horizontal reachability between two cores on the same floor —
that is the access-topology concern deferred v1-wide (`check_access_schema`
no-op, `LabeledRoom.doors=None`; S10-review #6).
"""

from __future__ import annotations

from collections import defaultdict

from room_layout.schema.failure import DomainGateFailure, FailureRecord
from room_layout.schema.geometry import ShapeInput
from room_layout.schema.program import ProgramRequest

_STAGE = "02"


def _vc_levels_by_anchor(program: ProgramRequest, occupied: set[int]) -> dict[str, set[int]]:
    """anchor_id -> the occupied levels that emit a vc room for it.

    A level emits a vc room iff its program carries a `vertical_circulation`
    spec (with the binding `anchor_id`). Levels outside `occupied` are ignored
    (a `PROGRAM_FLOOR_NOT_IN_SHAPE` concern handled by the schema validators).
    """
    by_anchor: dict[str, set[int]] = defaultdict(set)
    for level, specs in program.floor_programs.items():
        if level not in occupied:
            continue
        for spec in specs:
            if spec.role == "vertical_circulation" and spec.anchor_id is not None:
                by_anchor[spec.anchor_id].add(level)
    return by_anchor


def _connected_components(occupied: list[int], by_anchor: dict[str, set[int]]) -> list[list[int]]:
    """Union-find over `occupied` levels; each anchor connects the levels it
    serves (you can ride that stair between any of them). Returns the components
    as sorted level lists, sorted by their lowest level."""
    parent = {level: level for level in occupied}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for served in by_anchor.values():
        ls = sorted(served)
        for lo, hi in zip(ls, ls[1:], strict=False):
            union(lo, hi)

    groups: dict[int, list[int]] = defaultdict(list)
    for level in occupied:
        groups[find(level)].append(level)
    return sorted((sorted(g) for g in groups.values()), key=lambda g: g[0])


def check_vertical_continuity(shape: ShapeInput, program: ProgramRequest) -> None:
    """Every floor must be reachable through one connected vertical-circulation
    network (S10-D6). Raises `DomainGateFailure(VERTICAL_CIRCULATION_DISCONTINUOUS)`
    when a floor emits no vc room (isolated) or the vc network splits into more
    than one vertical group. Vacuous (returns) for a single-floor building.
    """
    occupied = sorted({f.level for f in shape.floors})
    if len(occupied) <= 1:
        return

    by_anchor = _vc_levels_by_anchor(program, set(occupied))
    components = _connected_components(occupied, by_anchor)
    if len(components) == 1:
        return

    served = {level for levels in by_anchor.values() for level in levels}
    isolated = [level for level in occupied if level not in served]
    if isolated:
        why = f"floor(s) {isolated} emit no vertical-circulation room (no vc spec)"
    else:
        why = f"vertical circulation splits into disconnected groups {components}"
    raise DomainGateFailure(
        FailureRecord(
            code="VERTICAL_CIRCULATION_DISCONTINUOUS",
            stage=_STAGE,
            message=(
                f"building floors are not all reachable through one vertical-"
                f"circulation network — {why}"
            ),
            data={
                "occupied_levels": occupied,
                "components": components,
                "isolated_levels": isolated,
            },
        )
    )
