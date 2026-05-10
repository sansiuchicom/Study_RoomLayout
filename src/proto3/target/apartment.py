"""ApartmentAdapter — Target A fixture loader + rules (S04-D3, S06-D5, D15).

Step 06 changes:
- `rules_path: Path` is **required** (no default); callers import
  `DEFAULT_APARTMENT_RULES_PATH` and pass it explicitly. Silent default
  fallback is intentionally absent (Plan S06-D5).
- `load_fixture` rejects fixtures whose `target_type != "apartment"`
  (S06-D15) — adapter ↔ fixture mismatch fails loudly even when the caller
  bypasses the RunConfig-based consistency check in stage00_load.
"""
from __future__ import annotations

from pathlib import Path

from proto3.schema.input import BuildingInput
from proto3.schema.serialize import from_json

from .base import TargetRules
from .rules_loader import load_target_rules

# Default apartment rules ship with the package (src/proto3/data/target_rules/apartment.json).
# `Path(__file__).resolve().parent.parent` resolves to `src/proto3/`.
DEFAULT_APARTMENT_RULES_PATH: Path = (
    Path(__file__).resolve().parent.parent / "data" / "target_rules" / "apartment.json"
)


class ApartmentAdapter:
    """Apartment fixture adapter (S04-D3). rules_path required (S06-D5)."""

    def __init__(self, rules_path: Path) -> None:
        self._rules: TargetRules = load_target_rules(rules_path)

    def load_fixture(self, path: Path) -> BuildingInput:
        b = from_json(BuildingInput, Path(path))
        if b.target_type != "apartment":
            raise ValueError(
                f"ApartmentAdapter received fixture with "
                f"target_type={b.target_type!r}, expected 'apartment' (path={path})"
            )
        return b

    def target_rules(self) -> TargetRules:
        return self._rules
