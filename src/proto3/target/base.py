"""TargetAdapter Protocol — fixture load + target-specific rules (S04-D3)."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from proto3.schema.input import BuildingInput


class TargetAdapter(Protocol):
    """Per-Target fixture loader + rule provider (S04-D3).

    Implementations: ApartmentAdapter (Step 04). B/C/D/E adapters are added
    when each Target is concretely tackled.
    """

    def load_fixture(self, path: Path) -> BuildingInput: ...

    def target_rules(self) -> dict: ...
