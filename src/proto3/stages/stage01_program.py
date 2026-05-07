"""Stage 01 — program resolution + cardinality gate (S04-D4, D11, D12).

Step 04 frame; Step 06 (Program & Domain Constraint Engine) will replace/extend
this module with full ProgramRequest dataclass, area gates, min-dimension
checks, and access-policy gates.
"""
from __future__ import annotations

from collections import Counter

from proto3.schema.input import BuildingInput
from proto3.schema.program import ProgramInstance, SpaceUnitSpec
from proto3.schema.validation import FailureRecord, ProgramInstantiationFailure
from proto3.target import TargetAdapter


def run(building: BuildingInput, *, adapter: TargetAdapter) -> ProgramInstance:
    """Resolve `program_request` into a `ProgramInstance` and check cardinality.

    Raises `ProgramInstantiationFailure` if any role required by
    `adapter.target_rules()['min_cardinality']` is under-supplied
    (D004 / DH-004 regression).
    """
    spaces = building.program_request.get("spaces", [])
    space_units = [SpaceUnitSpec(name=s["name"], role=s["role"]) for s in spaces]
    instance = ProgramInstance(space_units=space_units)

    min_card: dict = adapter.target_rules().get("min_cardinality", {})
    actual = Counter(unit.role for unit in space_units)

    for role, required in min_card.items():
        if actual[role] < required:
            failure = FailureRecord(
                failure_type="program_cardinality_insufficient",
                affected_space=role,
                detected_stage="01",
                evidence={"role": role, "required": required, "actual": actual[role]},
                diagnosis={
                    "likely_layer": "program_request",
                    "reason": f"role {role!r} count {actual[role]} < min {required}",
                },
            )
            raise ProgramInstantiationFailure(failure)

    return instance
