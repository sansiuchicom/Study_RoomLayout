"""Stage 01 — program instantiation + cardinality gate (S06-D7, D10, D023).

Step 06 §4.5 본격화. Step 04 frame (cardinality + name/role only) 가 다음으로
교체:

- ProgramRequest type guard: BuildingInput.program_request 가 ProgramRequest
  가 아니면 ProgramInstantiationFailure. typed schema (S06-D8) 강제.
- Per-space invariants (S06-D10):
  * `role` is in Role Literal and not None
  * no duplicate `name` across spaces
- All SpaceUnitSpec fields preserved (`required`, `min_area_m2`,
  `min_dimension_mm`, `max_area_m2`, `preferred_area_m2`). Step 04 frame
  dropped everything except `name`/`role`.
- Role-default fill (S06-D7): if `min_area_m2 is None`, use
  `TargetRules.default_min_area_m2[role]`. rules_loader guarantees a
  FULL Role-keyed map (D023 cross-link), so KeyError cannot occur here.
- Required-only cardinality (D023): optional spaces (`required=False`)
  don't satisfy `min_cardinality`. Optional repair (drop) is a Stage 12
  concern (D020 fail-only).

ProgramInstance produced by this stage is **concrete** — every required
space has a numeric `min_area_m2`, downstream stages don't need to handle
None.
"""
from __future__ import annotations

from collections import Counter
from typing import get_args

from proto3.schema.input import BuildingInput
from proto3.schema.program import (
    ProgramInstance,
    ProgramRequest,
    Role,
    SpaceUnitSpec,
)
from proto3.schema.validation import FailureRecord, ProgramInstantiationFailure
from proto3.target import TargetAdapter

_ALLOWED_ROLES: frozenset[str] = frozenset(get_args(Role))


def run(building: BuildingInput, *, adapter: TargetAdapter) -> ProgramInstance:
    """Resolve `building.program_request` into a concrete `ProgramInstance`.

    Raises:
        ProgramInstantiationFailure: on any of —
          - non-ProgramRequest input (`program_request_type_invalid`)
          - empty space name (`program_space_name_empty`)
          - None / unknown role (`program_space_role_invalid`)
          - duplicate name (`program_space_name_duplicate`)
          - role-default-fill creates an invariant-violating SpaceUnitSpec
            (`program_space_post_fill_invalid`, e.g. filled_min > declared max)
          - cardinality under-supply (`program_cardinality_insufficient`,
            D004 / DH-004 regression rule).
    """
    # Defense in depth (merge-prep, third external review #2). Adapter
    # already validates target_type at load_fixture time, but Stage 01 can
    # be called directly without going through Stage 00 — guard explicitly
    # so adapter/building mismatch fails loud at every entry.
    if building.target_type != adapter.target_type:
        raise ValueError(
            f"Stage 01: building.target_type={building.target_type!r} "
            f"does not match adapter.target_type={adapter.target_type!r}"
        )

    pr = building.program_request
    if not isinstance(pr, ProgramRequest):
        raise ProgramInstantiationFailure(FailureRecord(
            failure_type="program_request_type_invalid",
            detected_stage="01",
            evidence={
                "got_type": type(pr).__name__,
                "expected": "ProgramRequest",
            },
            diagnosis={
                "likely_layer": "program_request",
                "reason": "BuildingInput.program_request must be a ProgramRequest dataclass",
            },
        ))

    rules = adapter.target_rules()
    seen_names: set[str] = set()
    filled_units: list[SpaceUnitSpec] = []

    for i, u in enumerate(pr.spaces):
        # empty name reject (merge-prep, third external review #1). Duplicate
        # check below would catch two-empty case but not single-empty.
        if not u.name:
            raise ProgramInstantiationFailure(FailureRecord(
                failure_type="program_space_name_empty",
                detected_stage="01",
                evidence={"index": i, "name": u.name},
                diagnosis={
                    "likely_layer": "program_request",
                    "reason": "space name must be a non-empty identifier",
                },
            ))

        # role: must be a known Role Literal (S06-D10).
        # ProgramRequest.__post_init__ guarantees `u` is SpaceUnitSpec; from_dict
        # enforces Role Literal at deserialize time. This guard catches the
        # remaining path: callers constructing SpaceUnitSpec directly with an
        # invalid role string or leaving role=None (the dataclass default).
        if u.role is None or u.role not in _ALLOWED_ROLES:
            raise ProgramInstantiationFailure(FailureRecord(
                failure_type="program_space_role_invalid",
                affected_space=u.name,
                detected_stage="01",
                evidence={
                    "index": i,
                    "name": u.name,
                    "role": u.role,
                    "allowed_roles": sorted(_ALLOWED_ROLES),
                },
                diagnosis={
                    "likely_layer": "program_request",
                    "reason": "role must be one of the canonical Role values",
                },
            ))

        # name: no duplicates (S06-D7).
        if u.name in seen_names:
            raise ProgramInstantiationFailure(FailureRecord(
                failure_type="program_space_name_duplicate",
                affected_space=u.name,
                detected_stage="01",
                evidence={"index": i, "name": u.name},
                diagnosis={
                    "likely_layer": "program_request",
                    "reason": "space names must be unique within a ProgramRequest",
                },
            ))
        seen_names.add(u.name)

        # min_area_m2 fill (S06-D7): None → role default. rules_loader
        # guarantees default_min_area_m2 is a FULL map over Role.
        filled_min_area = (
            u.min_area_m2 if u.min_area_m2 is not None
            else rules.default_min_area_m2[u.role]
        )

        # SpaceUnitSpec.__post_init__ enforces invariants (e.g. max_area_m2
        # ≥ min_area_m2 when both set). Default fill can flip an originally-
        # valid spec (min=None, max=5, role=private) into an invariant
        # violation (filled_min=7, max=5). Surface that as a structured
        # ProgramInstantiationFailure rather than a raw ValueError so the
        # Search Orchestrator / Stage 12 catch paths stay consistent with
        # the rest of Stage 01 (D004 / D005 fail-loud).
        try:
            filled = SpaceUnitSpec(
                name=u.name,
                role=u.role,
                required=u.required,
                min_area_m2=filled_min_area,
                max_area_m2=u.max_area_m2,
                preferred_area_m2=u.preferred_area_m2,
                min_dimension_mm=u.min_dimension_mm,
            )
        except ValueError as e:
            raise ProgramInstantiationFailure(FailureRecord(
                failure_type="program_space_post_fill_invalid",
                affected_space=u.name,
                detected_stage="01",
                evidence={
                    "index": i,
                    "name": u.name,
                    "role": u.role,
                    "original_min_area_m2": u.min_area_m2,
                    "filled_min_area_m2": filled_min_area,
                    "max_area_m2": u.max_area_m2,
                    "preferred_area_m2": u.preferred_area_m2,
                    "min_dimension_mm": u.min_dimension_mm,
                    "error": str(e),
                },
                diagnosis={
                    "likely_layer": "program_request",
                    "reason": (
                        f"role default fill produced an invalid SpaceUnitSpec "
                        f"for {u.name!r}: {e}"
                    ),
                },
            )) from e
        filled_units.append(filled)

    instance = ProgramInstance(space_units=filled_units)

    # D023: required-only cardinality. Optional spaces don't satisfy
    # min_cardinality (silent-bug hardening from second external review).
    actual = Counter(u.role for u in filled_units if u.required)

    for role, min_required in rules.min_cardinality.items():
        if actual[role] < min_required:
            raise ProgramInstantiationFailure(FailureRecord(
                failure_type="program_cardinality_insufficient",
                affected_space=role,
                detected_stage="01",
                evidence={
                    "role": role,
                    "required": min_required,
                    "actual": actual[role],
                },
                diagnosis={
                    "likely_layer": "program_request",
                    "reason": f"role {role!r} count {actual[role]} < min {min_required}",
                },
            ))

    return instance
