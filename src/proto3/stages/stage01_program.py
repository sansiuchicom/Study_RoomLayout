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
          - None / unknown role (`program_space_role_invalid`)
          - duplicate name (`program_space_name_duplicate`)
          - cardinality under-supply (`program_cardinality_insufficient`,
            D004 / DH-004 regression rule).
    """
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

        filled_units.append(SpaceUnitSpec(
            name=u.name,
            role=u.role,
            required=u.required,
            min_area_m2=filled_min_area,
            max_area_m2=u.max_area_m2,
            preferred_area_m2=u.preferred_area_m2,
            min_dimension_mm=u.min_dimension_mm,
        ))

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
