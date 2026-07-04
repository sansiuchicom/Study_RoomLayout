"""Public entry point — ``run(shape, program, *, seed) -> LabeledRoomLayout``.

Plan reference: ``007_Step07_EntryPoint_Plan.md`` §4.6 (the join) + D001.

``run()`` joins the geometry half (Step 03/04: atomize → regionize →
region_graph → growth → corridor) and the program half (Step 05/06: admission
gates + ``program_to_fixture``), then runs the §3.8 labeling stage (§4.3),
re-inserts ``vertical_circulation`` anchor rooms (§4.4), and applies the
per-room post-growth check (§4.5). Pure function (no filesystem); per-floor
outer loop; the ``on_stage`` callback (default ``None`` = pure) is the only
side-effect channel (S07-D3 / D006) — its consumers (JSON / ``manifest.json``
writer §4.7; canonical renderer Step 08) live outside the core.

Failure handling (§4.6 decisions ②/③):

- the admission gates (``stage01`` cardinality, ``stage02`` area/dim,
  ``check_multi_floor_feasibility``) and ``polygonize`` (inside
  ``label_floor``) **raise** (``ProgramInstantiationFailure`` /
  ``DomainGateFailure`` / ``GeometryFailure``), each carrying a
  ``FailureRecord``; ``check_grown_rooms`` **collects** records;
- ``run()`` catches the raisers at stage boundaries and merges every record
  into one ``failure_records`` list, flipping ``valid=False`` on any failure.
  It never raises out (③): partial floors are preserved (Pipeline §2.4) and
  ``valid=False ⇒ failure_records`` is non-empty (proto3:D018).

``seed`` is accepted per the D001 contract (reproducibility) but the v1 growth
is fully deterministic (no RNG), so it is currently unused — reserved for the
deferred stochastic Search Orchestrator.

Two early-identified gaps are now **hardened**, not latent: growth
``K > seedable regions`` raises ``GROWTH_OVERSUBSCRIBED`` (a ``DomainGateFailure``
caught here → ``valid=False``, Step 07 §4.11), and an orphan corridor is bridged
into the hub network (``bridge_orphan_corridors``). The remaining xfail PoCs
(B5 / B6 / C10 latent geometry) are not reachable through the public ``run()``
on the shipped fixtures.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from shapely.ops import unary_union

from room_layout.constraints.gates import check_multi_floor_feasibility
from room_layout.constraints.multi_floor import check_vertical_continuity
from room_layout.constraints.room_gate import check_grown_rooms
from room_layout.schema import (
    WARN_PREFIX,
    CorridorTarget,
    DomainGateFailure,
    FailureRecord,
    FloorShape,
    GeometryFailure,
    LabeledFloorLayout,
    LabeledRoomLayout,
    ProgramInstantiationFailure,
    ProgramRequest,
    ShapeInput,
    StageOutput,
    TargetRules,
    validate_input,
)
from room_layout.stages.anchors import anchors_on_floor, subtract_anchors
from room_layout.stages.atomize import atomize
from room_layout.stages.corridor import carve_corridors
from room_layout.stages.corridor_bridge import bridge_orphan_corridors
from room_layout.stages.growth_partition import region_partition_growth
from room_layout.stages.labeling import label_floor, vc_rooms
from room_layout.stages.polygonize import build_region_polygons
from room_layout.stages.program_adapter import _EXCLUDED_INPUT_ROLES, program_to_fixture
from room_layout.stages.region_graph import build_region_graph
from room_layout.stages.regionize import regionize
from room_layout.stages.room_split import split_oversized
from room_layout.stages.stage01_program import run as _cardinality_gate
from room_layout.stages.stage02_gate import run as _area_dim_gate
from room_layout.target.adapter import (
    DEFAULT_APARTMENT_RULES_PATH,
    DEFAULT_HOUSE_RULES_PATH,
)
from room_layout.target.rules_loader import load_target_rules

# Shipped typologies (S06-D5: a typology is a data-only `<t>.json` add). house
# is the first multi-floor typology (Step 10, S10-D3).
_RULES_PATH_BY_TYPE = {
    "apartment": DEFAULT_APARTMENT_RULES_PATH,
    "house": DEFAULT_HOUSE_RULES_PATH,
}


def _emit(
    on_stage: Callable[[StageOutput], None] | None,
    index: int,
    stage_id: str,
    payload: object,
    level: int | None = None,
) -> None:
    if on_stage is not None:
        on_stage(StageOutput(index=index, stage_id=stage_id, payload=payload, level=level))


# 현관(건물 출입구) region 예약 — ShapeInput.entry_floor 에서만. 건물 외주(exterior)에
# 충분히 닿는 ~현관 크기 region 하나를 seed 로 골라 growth 에서 제외(+corridor target).
# 계단(subtract-first, 물리·수직)과 달리 현관은 단층 방이라 *이미 만든 region* 을 빼는
# 게 맞음 — 격자 정렬이라 인접 방 notch 0 (PlanBIM 145 §13 Option 1).
_ENTRY_WALL_MIN = 1.2  # 외주 공유 최소 길이(m) — 외부문 자리
_ENTRY_AREA = (2.0, 5.0)  # 현관 region 면적 범위(㎡)


def _pick_entry_region(regions: tuple, seed: int):
    """외주(건물 외벽)에 닿는 ~현관 크기 region 1개 (seed 변이). 없으면 None.

    floor 의 외주 = region 폴리곤 합집합의 exterior(계단 hole 은 interior 라 제외됨).
    가장 긴 변 편향 없음(유효 후보 중 seed-uniform). 단층 방이라 안전 — 모양 이상해도
    계단처럼 못 만드는 게 아님.
    """
    polys = build_region_polygons(regions)
    floor_poly = unary_union(list(polys.values()))
    if floor_poly.geom_type != "Polygon":  # 분리된 floor (드묾) → 예약 포기
        return None
    ext = floor_poly.exterior
    lo, hi = _ENTRY_AREA
    cands = [
        r
        for r in regions
        if lo <= polys[r.region_id].area <= hi
        and polys[r.region_id].boundary.intersection(ext).length >= _ENTRY_WALL_MIN
    ]
    if not cands:
        return None
    return cands[seed % len(cands)]


def _run_floor(
    floor: FloorShape,
    *,
    shape: ShapeInput,
    program: ProgramRequest,
    rules: TargetRules,
    building_cardinality: bool,
    seed: int,
    on_stage: Callable[[StageOutput], None] | None,
    extra_corridor_targets: tuple = (),
    enforce_connectivity: bool = True,
    carve: bool = True,
) -> tuple[LabeledFloorLayout, list[FailureRecord]]:
    """Lay out one floor — the per-floor body of ``run()`` (S10-D2 extraction).

    Returns ``(layout, failures)``: the floor's ``LabeledFloorLayout`` (a partial
    / empty one on a caught failure — Pipeline §2.4) plus the ``FailureRecord``s
    it produced (raisers caught at stage boundaries; ``check_grown_rooms``
    collected). The cross-floor passes (building cardinality / vc continuity)
    stay in ``run()``; this is purely per-floor — there is no cross-floor state.
    """
    specs = program.floor_programs.get(floor.level, [])

    # ── admission (pre-growth; raise → catch) ──
    # cardinality is per-floor only when scope == per_floor (S10-D5); the building
    # branch already checked it once in run(). area/dim stays per-floor.
    try:
        if not building_cardinality:
            _cardinality_gate(specs, rules=rules)
        _area_dim_gate(floor, specs, rules=rules)
    except (ProgramInstantiationFailure, DomainGateFailure) as e:
        return LabeledFloorLayout(level=floor.level), [e.record]

    # ── vc-only / empty floor (S10-D12) ──
    # No growable rooms (a circulation-only / stair floor, or an empty program) →
    # nothing to grow: emit just the fixed vc rooms and skip the geometry block.
    # Never-crashes: closes the `program_to_fixture` no-growable-rooms ValueError
    # path that building cardinality (S10-D5) made reachable (prior review #10).
    # A genuinely unreachable floor is flagged separately by
    # `check_vertical_continuity` (S10-D6).
    if not any(s.role not in _EXCLUDED_INPUT_ROLES for s in specs):
        applicable = anchors_on_floor(shape.vertical_anchors, floor.level)
        fl = LabeledFloorLayout(level=floor.level, rooms=vc_rooms(specs, applicable))
        # emit the labeling stage so this floor still appears in the on_stage
        # trace + per-floor SVG (S10 review #1 — it was silently skipped).
        _emit(on_stage, 6, "labeling", fl, floor.level)
        return fl, []

    # ── geometry + labeling — wrapped so any feasibility / geometry failure
    #    becomes valid=False, never crashing out (③): subtract_anchors raises
    #    when an anchor consumes the whole floor; region_partition_growth raises
    #    GROWTH_OVERSUBSCRIBED when the program over-subscribes the floor's seeds;
    #    label_floor's polygonize raises GeometryFailure on a disconnected room.
    try:
        applicable = anchors_on_floor(shape.vertical_anchors, floor.level)
        holed = subtract_anchors(floor, shape.vertical_anchors)
        atoms = atomize(holed)
        _emit(on_stage, 1, "atomize", atoms, floor.level)
        regions = regionize(holed, atoms=atoms, enforce_connectivity=enforce_connectivity)
        _emit(on_stage, 2, "regionize", regions, floor.level)
        # 현관 예약 (entry_floor) — 외주 region 1개를 growth 에서 빼고 corridor target
        # 으로 access 보장(landing 과 동일 메커니즘). label_floor 가 고정 방으로 재삽입.
        # build_region_graph 는 빠진 region 의 atom→None 으로 우아하게 제외 (S03 graph).
        entry_poly = None
        # Entry reservation is part of the circulation subsystem — gated with
        # ``carve`` so the no-carve ablation grows a plain tiling (no reserved
        # entry region, no corridors).
        if carve and floor.level == shape.entry_floor:
            er = _pick_entry_region(regions, seed)
            if er is not None:
                entry_poly = build_region_polygons([er])[er.region_id]
                regions = tuple(r for r in regions if r.region_id != er.region_id)
                extra_corridor_targets = (*extra_corridor_targets, entry_poly)
        rg = build_region_graph(holed, atoms=atoms, regions=regions)
        _emit(on_stage, 3, "region_graph", rg, floor.level)
        fixture = program_to_fixture(holed, program)
        growth = region_partition_growth(holed, fixture, regions=regions, region_graph=rg)
        # §11 pre-corridor split: 큰 방을 role 상한 밑으로 → corridor 가 새 방 access 처리.
        growth = split_oversized(growth, regions)
        _emit(on_stage, 4, "growth", growth, floor.level)
        carved = carve_corridors(
            holed,
            growth,
            regions=regions,
            region_graph=rg,
            extra_targets=extra_corridor_targets,
            carve=carve,
        )
        # repo post-step (§4.11): bridge any orphan corridor into the hub network.
        carved = bridge_orphan_corridors(carved, regions, rg)
        _emit(on_stage, 5, "corridor", carved, floor.level)
        fl = label_floor(
            carved, regions, specs, level=floor.level, anchors=applicable, entry=entry_poly
        )
        _emit(on_stage, 6, "labeling", fl, floor.level)
    except (DomainGateFailure, GeometryFailure) as e:
        return LabeledFloorLayout(level=floor.level), [e.record]

    # ── per-room post-growth check (§4.5; collect) ──
    return fl, list(check_grown_rooms(fl.rooms, {s.id: s for s in specs}))


def run(
    shape: ShapeInput,
    program: ProgramRequest,
    *,
    seed: int,
    on_stage: Callable[[StageOutput], None] | None = None,
    corridor_targets: Sequence[CorridorTarget] | None = None,
    enforce_connectivity: bool = True,
    carve: bool = True,
) -> LabeledRoomLayout:
    """Lay out ``program`` on ``shape`` and return a ``LabeledRoomLayout`` (D001).

    ``corridor_targets``: optional geometric access goals — circulation must
    additionally reach each target's polygon on its floor (e.g., a walk-in
    anchor's landing, which the anchor-blind corridor stage would otherwise
    ignore). Best-effort; per-target outcome lands in stage diagnostics.
    """
    failures: list[FailureRecord] = []
    floors: list[LabeledFloorLayout] = []
    provenance = {"seed": seed, "target_type": program.target_type}

    _emit(on_stage, 0, "input", {"shape": shape, "program": program, "seed": seed})

    # Input cross-validation (anchor refs / floor refs / duplicates). WARN_*
    # records are advisory (→ provenance); hard errors short-circuit valid=False.
    input_records = validate_input(shape, program)
    hard = [r for r in input_records if not r.code.startswith(WARN_PREFIX)]
    warns = [r for r in input_records if r.code.startswith(WARN_PREFIX)]
    if warns:
        provenance["warnings"] = warns
    if hard:
        return LabeledRoomLayout(
            valid=False, floors=[], failure_records=hard, provenance=provenance
        )

    # Resolve typology rules (S07-D6). Shipped: apartment + house (Step 10).
    rules_path = _RULES_PATH_BY_TYPE.get(program.target_type)
    if rules_path is None:
        return LabeledRoomLayout(
            valid=False,
            floors=[],
            failure_records=[
                FailureRecord(
                    code="NO_TARGET_RULES",
                    stage="run",
                    message=(
                        f"no target_rules shipped for typology {program.target_type!r} "
                        f"(shipped: {sorted(_RULES_PATH_BY_TYPE)})"
                    ),
                    data={"target_type": program.target_type},
                )
            ],
            provenance=provenance,
        )
    rules = load_target_rules(rules_path)

    # Building-level gate (S05-D6) — fundamental, short-circuits the whole run.
    try:
        check_multi_floor_feasibility(
            n_floors=len(shape.floors),
            requires_single_floor=rules.requires_single_floor,
        )
    except DomainGateFailure as e:
        return LabeledRoomLayout(
            valid=False, floors=[], failure_records=[e.record], provenance=provenance
        )

    # ── building-level cardinality (S10-D5/D13) ──
    # When the typology counts `min_cardinality` over the WHOLE building (a house
    # needs its required rooms building-wide, not on every floor), check it ONCE
    # over all floors' specs. A shortfall is collected (partial floors still
    # render — never-crashes). `per_floor` typologies (apartment) skip this and
    # keep the in-loop per-floor check below — byte-identical.
    building_cardinality = rules.cardinality_scope == "building"
    if building_cardinality:
        all_specs = [s for fspecs in program.floor_programs.values() for s in fspecs]
        try:
            _cardinality_gate(all_specs, rules=rules)
        except (ProgramInstantiationFailure, DomainGateFailure) as e:
            failures.append(e.record)

    # ── vertical-circulation continuity (S10-D6) — multi-floor only ──
    # Every floor must be reachable through one connected vc network (defined on
    # emitted vc rooms — spec-gated). Vacuous for a single floor → apartment
    # untouched. Collected (partial floors still render — never-crashes).
    try:
        check_vertical_continuity(shape, program)
    except DomainGateFailure as e:
        failures.append(e.record)

    # Per-floor: the geometry/labeling body is `_run_floor` (S10-D2); the
    # cross-floor passes above are the only building-level concerns.
    targets_by_level: dict[int, list] = {}
    for t in corridor_targets or ():
        targets_by_level.setdefault(t.level, []).append(t.polygon)

    for floor in shape.floors:
        fl, floor_failures = _run_floor(
            floor,
            shape=shape,
            program=program,
            rules=rules,
            building_cardinality=building_cardinality,
            seed=seed,
            on_stage=on_stage,
            extra_corridor_targets=tuple(targets_by_level.get(floor.level, ())),
            enforce_connectivity=enforce_connectivity,
            carve=carve,
        )
        floors.append(fl)
        failures.extend(floor_failures)

    return LabeledRoomLayout(
        valid=not failures, floors=floors, failure_records=failures, provenance=provenance
    )
