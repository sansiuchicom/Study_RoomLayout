"""TargetAdapter — single generic adapter for all typologies (S06-D5, D22).

Step 06 §4.3a (옵션 C): A single concrete `TargetAdapter` class drives every
typology (apartment, house, hotel, warehouse, office, ...). The typology
identity lives in the rules JSON's `target_type` field, not in a per-typology
subclass — there are no `ApartmentAdapter` / `HotelAdapter` classes by design.

Adding a new typology that shares all algorithms with apartment is a
**data-only** operation:
1. Author `src/proto3/data/target_rules/<typology>.json` with `target_type`.
2. Register a default rules path in `proto3.stages.stage00_load._DEFAULT_ADAPTERS`.

Typology-specific algorithm variants (e.g., hotel explicit-corridor pattern,
warehouse open-plan zoning) — when introduced — go into a strategy registry
(L2 in the 3-layer model documented in `src/proto3/data/target_rules/README.md`),
not into adapter subclasses. New strategies are typology-agnostic by design.

`rules_path` is **required** (S06-D5). The default path constant is exported
for callers that opt into proto3 defaults; explicit override is encouraged.
"""
from __future__ import annotations

from pathlib import Path

from proto3.schema.input import BuildingInput
from proto3.schema.serialize import from_json

from .base import TargetRules
from .rules_loader import load_target_rules

# Default apartment rules ship with the package
# (src/proto3/data/target_rules/apartment.json). pyproject.toml ensures it
# lands in wheel + sdist distributions (DoD-5).
DEFAULT_APARTMENT_RULES_PATH: Path = (
    Path(__file__).resolve().parent.parent / "data" / "target_rules" / "apartment.json"
)


class TargetAdapter:
    """Generic typology adapter (S06-D5, D22).

    Behavior is identical for all typologies; differences live in the JSON
    file at `rules_path`. The adapter validates at construction time (via
    `load_target_rules`) and at fixture load time (target_type match).
    """

    def __init__(self, rules_path: Path) -> None:
        self._rules: TargetRules = load_target_rules(rules_path)

    @property
    def target_type(self) -> str:
        """Typology this adapter is configured for, sourced from the rules JSON."""
        return self._rules.target_type

    def load_fixture(self, path: Path) -> BuildingInput:
        """Load a fixture and assert its target_type matches this adapter (S06-D15)."""
        b = from_json(BuildingInput, Path(path))
        if b.target_type != self._rules.target_type:
            raise ValueError(
                f"TargetAdapter configured for target_type={self._rules.target_type!r} "
                f"received fixture with target_type={b.target_type!r} (path={path})"
            )
        return b

    def target_rules(self) -> TargetRules:
        return self._rules
