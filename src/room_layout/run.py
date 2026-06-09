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

Known latent gaps (NOT caught here — xfail PoCs, deferred to §4.11): growth
``K > seedable regions`` → ``IndexError``, and corridor single-component. The
33 goldens + apartment fixtures do not trigger them.
"""

from __future__ import annotations

from collections.abc import Callable

from room_layout.constraints.gates import check_multi_floor_feasibility
from room_layout.constraints.multi_floor import check_vertical_continuity
from room_layout.constraints.room_gate import check_grown_rooms
from room_layout.schema import (
    WARN_PREFIX,
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
from room_layout.stages.program_adapter import _EXCLUDED_INPUT_ROLES, program_to_fixture
from room_layout.stages.region_graph import build_region_graph
from room_layout.stages.regionize import regionize
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


def _run_floor(
    floor: FloorShape,
    *,
    shape: ShapeInput,
    program: ProgramRequest,
    rules: TargetRules,
    building_cardinality: bool,
    on_stage: Callable[[StageOutput], None] | None,
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
        return LabeledFloorLayout(level=floor.level, rooms=vc_rooms(specs, applicable)), []

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
        regions = regionize(holed, atoms=atoms)
        _emit(on_stage, 2, "regionize", regions, floor.level)
        rg = build_region_graph(holed, atoms=atoms, regions=regions)
        _emit(on_stage, 3, "region_graph", rg, floor.level)
        fixture = program_to_fixture(holed, program)
        growth = region_partition_growth(holed, fixture, regions=regions, region_graph=rg)
        _emit(on_stage, 4, "growth", growth, floor.level)
        carved = carve_corridors(holed, growth, regions=regions, region_graph=rg)
        # repo post-step (§4.11): bridge any orphan corridor into the hub network.
        carved = bridge_orphan_corridors(carved, regions, rg)
        _emit(on_stage, 5, "corridor", carved, floor.level)
        fl = label_floor(carved, regions, specs, level=floor.level, anchors=applicable)
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
) -> LabeledRoomLayout:
    """Lay out ``program`` on ``shape`` and return a ``LabeledRoomLayout`` (D001)."""
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

    # Resolve typology rules (S07-D6) — v1 ships apartment only.
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
                        "(v1 ships apartment only)"
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
    for floor in shape.floors:
        fl, floor_failures = _run_floor(
            floor,
            shape=shape,
            program=program,
            rules=rules,
            building_cardinality=building_cardinality,
            on_stage=on_stage,
        )
        floors.append(fl)
        failures.extend(floor_failures)

    return LabeledRoomLayout(
        valid=not failures, floors=floors, failure_records=failures, provenance=provenance
    )
