"""TargetAdapter Protocol + TargetRules dataclass (S04-D3, S06-D9).

Protocol (S04-D3): every Target adapter must implement `load_fixture` and
`target_rules`.

TargetRules (S06-D9): typed contract returned by `target_rules()`. All
fields required (no dataclass-level defaults) — JSON loader populates them
explicitly. This keeps the engine ↔ data separation honest: silent
fallbacks would defeat S06-D5 fail-loud policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from proto3.schema.input import BuildingInput
from proto3.schema.program import Role


@dataclass
class TargetRules:
    """Per-Target domain rule contract used by Stage 01/02 (S06-D9).

    Populated from `config/target_rules/<target>.json` via
    `proto3.target.rules_loader.load_target_rules`. External pipelines
    swap the whole file (Plan S06-D17, no partial merge).
    """
    min_cardinality: dict[Role, int]            # Stage 01 cardinality gate
    default_min_area_m2: dict[Role, float]      # Stage 01 fill for None min_area_m2 (S06-D7)
    density_factor: float                        # Stage 02 area gate; 0 < x ≤ 1
    requires_single_floor: bool                  # Stage 02 multi-floor feasibility (apartment = True)


class TargetAdapter(Protocol):
    """Per-Target fixture loader + rule provider (S04-D3).

    Implementations: ApartmentAdapter (Target A). B/C/D/E adapters are added
    when each Target is concretely tackled (Plan Def-10).
    """

    def load_fixture(self, path: Path) -> BuildingInput: ...

    def target_rules(self) -> TargetRules: ...
