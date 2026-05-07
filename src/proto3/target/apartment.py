"""ApartmentAdapter — Target A fixture loader + rules (S04-D3, S04-D12)."""
from __future__ import annotations

from pathlib import Path

from proto3.schema.input import BuildingInput
from proto3.schema.serialize import from_json


class ApartmentAdapter:
    """Apartment fixture adapter conforming to TargetAdapter Protocol.

    target_rules() returns min_cardinality used by Stage 01 to detect
    ProgramInstantiationFailure (D004 / DH-004 regression).
    """

    def load_fixture(self, path: Path) -> BuildingInput:
        return from_json(BuildingInput, Path(path))

    def target_rules(self) -> dict:
        return {
            "min_cardinality": {"public": 1, "private": 1, "wet": 1},
        }
