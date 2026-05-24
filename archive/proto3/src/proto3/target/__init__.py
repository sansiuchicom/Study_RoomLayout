"""Target adapters — single generic TargetAdapter + per-typology JSON rules
(S04-D3 redesigned at S06-D5, D17, D22).

Engine ↔ data separation: typology identity lives in JSON, not in code.
See `src/proto3/data/target_rules/README.md` for the 3-layer extensibility
model (L0 invariant Python / L1 parameter JSON / L2 strategy plugin).
"""
from .base import TargetRules
from .adapter import TargetAdapter, DEFAULT_APARTMENT_RULES_PATH

__all__ = [
    "TargetRules",
    "TargetAdapter",
    "DEFAULT_APARTMENT_RULES_PATH",
]
