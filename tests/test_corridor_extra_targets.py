"""Corridor extra targets — caller-specified geometric access goals (§4.13 ext).

Motivation (synthetic-bim integration, PlanBIM 142 ③-2): a walk-in anchor's
landing must be reachable from the circulation network, but anchors are
holes the corridor stage never sees (S04-D4 anchor-blind). ``CorridorTarget``
lets the caller say "circulation must also reach this polygon" — the corridor
routes to the regions adjacent to it, reusing Stage 1's hub-radial machinery
(damage-guarded A*).

Semantics difference vs room targets: the goal region IS carved (the corridor
must *touch* the target polygon, not stop one region short).
"""

from __future__ import annotations

import shapely.geometry as sg

from room_layout.stages.corridor import _route_extra_targets


def _grid_world(rows: int = 2, cols: int = 5):
    """rows×cols unit-square regions; id = r*cols + c (c: 0..cols-1)."""
    region_poly: dict[int, sg.Polygon] = {}
    region_adj: dict[int, set[int]] = {}
    for r in range(rows):
        for c in range(cols):
            rid = r * cols + c
            region_poly[rid] = sg.box(c, r, c + 1, r + 1)
            adj = set()
            if c > 0:
                adj.add(rid - 1)
            if c < cols - 1:
                adj.add(rid + 1)
            if r > 0:
                adj.add(rid - cols)
            if r < rows - 1:
                adj.add(rid + cols)
            region_adj[rid] = adj
    region_area = {rid: 1.0 for rid in region_poly}
    on_edge = {rid: True for rid in region_poly}
    return region_poly, region_adj, region_area, on_edge


def test_extra_target_routes_corridor_to_isolated_polygon():
    """hub 와 비인접한 target → A* 로 corridor 가 target 인접 region 까지 깎임."""
    region_poly, region_adj, region_area, on_edge = _grid_world()
    # rooms: hub(public) = col0, A(private) = cols1-2, B(private) = cols3-4
    room_region_ids = {
        0: {0, 5},
        1: {1, 2, 6, 7},
        2: {3, 4, 8, 9},
    }
    room_roles = {0: "public", 1: "private", 2: "private"}
    # target box east of col4, row0 — shares x=5 edge with region 4 only
    target = sg.box(5.0, 0.0, 5.9, 1.0)

    base_corridor: set[int] = set()
    unassigned: set[int] = set()
    log = _route_extra_targets(
        (target,),
        room_region_ids=room_region_ids,
        room_roles=room_roles,
        hub_regions=room_region_ids[0],
        base_corridor=base_corridor,
        unassigned_set=unassigned,
        region_poly=region_poly,
        region_area=region_area,
        region_adj=region_adj,
        on_footprint_edge=on_edge,
    )

    assert log[0]["result"] == "ok", log
    # corridor must now touch the target polygon (goal region carved)
    touched = any(
        region_poly[rid].boundary.intersection(target.boundary).length > 0.05
        for rid in base_corridor
    )
    assert touched, f"corridor {sorted(base_corridor)} does not touch target"
    # carved regions were removed from their owner rooms
    for rid in base_corridor:
        for owner_set in room_region_ids.values():
            assert rid not in owner_set
    # no room emptied or split (damage guard)
    assert all(room_region_ids.values()), room_region_ids


def test_extra_target_satisfied_by_public_adjacency_no_carving():
    """target 이 이미 public(hub) region 과 접하면 — 깎지 않고 satisfied."""
    region_poly, region_adj, region_area, on_edge = _grid_world()
    room_region_ids = {0: {4, 9}, 1: {0, 1, 2, 3, 5, 6, 7, 8}}
    room_roles = {0: "public", 1: "private"}
    target = sg.box(5.0, 0.0, 5.9, 1.0)  # region 4 (public) 와 접함

    base_corridor: set[int] = set()
    log = _route_extra_targets(
        (target,),
        room_region_ids=room_region_ids,
        room_roles=room_roles,
        hub_regions=room_region_ids[0],
        base_corridor=base_corridor,
        unassigned_set=set(),
        region_poly=region_poly,
        region_area=region_area,
        region_adj=region_adj,
        on_footprint_edge=on_edge,
    )
    assert log[0]["result"] == "satisfied"
    assert not base_corridor  # 깎인 것 없음


def test_extra_target_no_goal_regions_logs_unreachable():
    """target 이 어느 region 과도 안 접함 → unreachable 로그, 무손상."""
    region_poly, region_adj, region_area, on_edge = _grid_world()
    room_region_ids = {0: {0, 5}, 1: {1, 2, 3, 4, 6, 7, 8, 9}}
    room_roles = {0: "public", 1: "private"}
    target = sg.box(20.0, 20.0, 21.0, 21.0)  # 멀리 떨어짐

    base_corridor: set[int] = set()
    log = _route_extra_targets(
        (target,),
        room_region_ids=room_region_ids,
        room_roles=room_roles,
        hub_regions=room_region_ids[0],
        base_corridor=base_corridor,
        unassigned_set=set(),
        region_poly=region_poly,
        region_area=region_area,
        region_adj=region_adj,
        on_footprint_edge=on_edge,
    )
    assert log[0]["result"] == "no-goal-regions"
    assert not base_corridor


def test_run_accepts_corridor_targets_and_connects():
    """run() 통합 — corridor_targets 를 받고, 산출에서 순환(공용 방 ∪ corridor)
    이 target 폴리곤과 접한다 (메커니즘 무관 post-condition)."""
    from room_layout.run import run
    from room_layout.schema import (
        CorridorTarget,
        FloorShape,
        ProgramRequest,
        ShapeInput,
        ShapePart,
        SpaceUnitSpec,
        VerticalAnchor,
    )

    stair = sg.box(0.0, 3.0, 1.2, 6.6)
    landing = sg.box(1.2, 3.0, 2.1, 6.6)  # 계단 동쪽 면 앞
    floor = FloorShape(
        level=1,
        parts=[ShapePart(exterior=((0.0, 0.0), (12.0, 0.0), (12.0, 9.0), (0.0, 9.0)))],
        floor_to_floor_height=None,
    )
    shape = ShapeInput(
        name="extra-target-test",
        floors=[floor],
        vertical_anchors=[
            VerticalAnchor(
                id="stair",
                kind="stair_core",
                footprint_polygon=stair,
                floor_range=(1, 1),
                host_role="vertical_circulation",
            ),
            VerticalAnchor(
                id="landing",
                kind="stair_core",
                footprint_polygon=landing,
                floor_range=(1, 1),
                host_role="vertical_circulation",
            ),
        ],
    )
    specs = [
        SpaceUnitSpec(
            id="living",
            role="public",
            usage="living",
            area_min_m2=10.0,
            required=True,
        ),
        SpaceUnitSpec(
            id="bed1",
            role="private",
            usage="bedroom",
            area_min_m2=7.5,
            required=True,
        ),
        SpaceUnitSpec(
            id="bed2",
            role="private",
            usage="bedroom",
            area_min_m2=7.5,
            required=True,
        ),
        SpaceUnitSpec(
            id="bath",
            role="wet",
            usage="bathroom",
            area_min_m2=2.5,
            required=True,
        ),
        SpaceUnitSpec(
            id="stair_spec",
            role="vertical_circulation",
            usage="stair",
            area_min_m2=stair.area,
            required=True,
            anchor_id="stair",
        ),
        SpaceUnitSpec(
            id="landing_spec",
            role="vertical_circulation",
            usage="entry",
            area_min_m2=landing.area,
            required=True,
            anchor_id="landing",
        ),
    ]
    program = ProgramRequest(target_type="house", floor_programs={1: specs})

    layout = run(
        shape,
        program,
        seed=7,
        corridor_targets=[CorridorTarget(level=1, polygon=landing)],
    )
    assert layout.valid, layout.failure_records
    fl = layout.floors[0]
    circulation = [r.polygon for r in fl.rooms if r.role == "public"] + list(fl.corridor_polygons)
    touch = max(
        (landing.boundary.intersection(p.boundary).length for p in circulation),
        default=0.0,
    )
    assert touch > 0.05, f"순환이 landing 과 접하지 않음 (touch={touch})"


def test_run_corridor_targets_default_none_is_noop():
    """corridor_targets 미지정 = 기존 동작 (파라미터 추가의 하위호환)."""
    from room_layout.run import run
    from room_layout.schema import (
        FloorShape,
        ProgramRequest,
        ShapeInput,
        ShapePart,
        SpaceUnitSpec,
    )

    floor = FloorShape(
        level=1,
        parts=[ShapePart(exterior=((0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)))],
        floor_to_floor_height=None,
    )
    shape = ShapeInput(name="noop", floors=[floor])
    specs = [
        SpaceUnitSpec(
            id="living",
            role="public",
            usage="living",
            area_min_m2=10.0,
            required=True,
        ),
        SpaceUnitSpec(
            id="bed1",
            role="private",
            usage="bedroom",
            area_min_m2=7.5,
            required=True,
        ),
        SpaceUnitSpec(
            id="bath",
            role="wet",
            usage="bathroom",
            area_min_m2=2.5,
            required=True,
        ),
    ]
    program = ProgramRequest(target_type="house", floor_programs={1: specs})
    a = run(shape, program, seed=3)
    b = run(shape, program, seed=3, corridor_targets=None)
    assert a.valid and b.valid
    assert [r.polygon.wkt for r in a.floors[0].rooms] == [r.polygon.wkt for r in b.floors[0].rooms]
