"""Target adapters per S04-D3 — Protocol + per-Target implementations.

Apartment-first; B/C/D/E adapters added when each Target is concretely tackled.

Step 06: TargetRules dataclass (S06-D9) + DEFAULT_APARTMENT_RULES_PATH constant
(S06-D5) added to public surface.
"""
from .base import TargetAdapter, TargetRules
from .apartment import ApartmentAdapter, DEFAULT_APARTMENT_RULES_PATH

__all__ = [
    "TargetAdapter",
    "TargetRules",
    "ApartmentAdapter",
    "DEFAULT_APARTMENT_RULES_PATH",
]
