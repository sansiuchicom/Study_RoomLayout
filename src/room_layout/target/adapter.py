"""TargetAdapter — single generic typology adapter (Step 06 §4.4, S06-D5).

One concrete `TargetAdapter` drives every typology (apartment / house / hotel
/ office / warehouse). Typology identity lives in the rules JSON's
`target_type` field, **not** in a per-typology subclass — there are no
`ApartmentAdapter` / `HotelAdapter` classes by design (proto3:D022). Adding a
typology that shares all algorithms is a data-only operation: author
`data/target_rules/<typology>.json`.

Single responsibility (S06-D5 / 4.4 option 가): the adapter is a **validated
rules provider** — it loads + validates at construction and exposes the
result. proto3's `load_fixture` (which read a single `BuildingInput` and
asserted its `target_type`) is **not** ported: this repo splits input into
`ShapeInput` + `ProgramRequest` (no combined fixture object), and fixtures are
loaded by callers/tests directly.

No `target_type` introspection (S06-D6): `TargetRules` carries no `target_type`
field, and the adapter exposes no `target_type` property. The reason is that
**nothing downstream reads it** — `ProgramRequest.target_type` is validated
only as a Literal (`program.py`), never matched against rules; the gates
(stage01/02) take `rules` and ignore `target_type`. So a "does this rules file
match the requested typology?" cross-check would guard a risk that does not
exist in v1 (a mismatched label produces a correct layout, just a wrong tag) —
speculative robustness, dropped per the honest-fix principle. `expand_program`
simply stamps the caller's `target_type` onto the `ProgramRequest`; the info
is not lost, and a real consumer can add the field + check when one appears.

Algorithm variants (L2 strategy plugins, 3-layer model — see
`data/target_rules/README.md`) are typology-agnostic and out of scope until a
typology needs a genuinely different algorithm (proto3:D022).
"""

from __future__ import annotations

from pathlib import Path

from room_layout.schema import TargetRules
from room_layout.target.rules_loader import load_target_rules


class TargetAdapter:
    """Generic typology adapter — a validated `TargetRules` provider (S06-D5).

    Validates at construction (via `load_target_rules`); raises `ValueError`
    on any defect in the rules file (see the loader). Exposes only the
    validated rules (no `target_type` introspection — S06-D6).
    """

    def __init__(self, rules_path: Path | str) -> None:
        self._rules: TargetRules = load_target_rules(rules_path)

    def target_rules(self) -> TargetRules:
        """The validated `TargetRules` for this typology."""
        return self._rules
