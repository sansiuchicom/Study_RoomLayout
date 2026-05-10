"""TargetRules dataclass (S06-D9, D22).

Step 06 §4.3a: TargetAdapter Protocol removed in favor of a single concrete
TargetAdapter class (proto3.target.adapter). Typology identity moves from
class name to JSON `target_type` field — see config/target_rules/README.md
for the 3-layer extensibility model.

TargetRules is the typed contract returned by `TargetAdapter.target_rules()`.
All fields required (no dataclass-level defaults) so silent fallbacks cannot
mask rule-file errors (S06-D5 fail-loud policy).
"""
from __future__ import annotations

from dataclasses import dataclass

from proto3.schema.input import TargetType
from proto3.schema.program import Role


@dataclass
class TargetRules:
    """Per-typology domain rule contract used by Stage 01/02 (S06-D9, D22).

    Populated from `src/proto3/data/target_rules/<target>.json` via
    `proto3.target.rules_loader.load_target_rules`. The JSON's `target_type`
    field is mirrored here so downstream code can introspect adapter
    identity without importing typology-specific classes (there are none).

    External pipelines override by passing a custom `rules_path` to
    `TargetAdapter`; the override file replaces this one entirely (Plan
    S06-D17, no partial merge).
    """
    target_type: TargetType                      # mirrors fixture target_type (S06-D22)
    min_cardinality: dict[Role, int]             # Stage 01 cardinality gate
    default_min_area_m2: dict[Role, float]       # Stage 01 fill for None min_area_m2 (S06-D7)
    density_factor: float                         # Stage 02 area gate; 0 < x ≤ 1
    requires_single_floor: bool                   # Stage 02 multi-floor feasibility
