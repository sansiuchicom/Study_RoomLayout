"""room_layout.target — per-typology rule values + loading (Step 06).

The value+loading half of the S05-D2 boundary (Step 05 shipped the
`TargetRules` *type*; this package supplies the *values*):

- `rules_loader.load_target_rules(path)` — JSON file → validated `TargetRules`.
- `adapter.TargetAdapter` — single generic typology adapter (proto3:D022).
- `expand_program.expand_program` — `{role: count}` → `ProgramRequest`.

See ``006_Step06_TargetRules_Plan.md``.
"""

from room_layout.target.rules_loader import load_target_rules

__all__ = ["load_target_rules"]
