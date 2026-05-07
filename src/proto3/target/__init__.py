"""Target adapters per S04-D3 — Protocol + per-Target implementations.

Apartment-first; B/C/D/E adapters added when each Target is concretely tackled.
"""
from .base import TargetAdapter
from .apartment import ApartmentAdapter

__all__ = ["TargetAdapter", "ApartmentAdapter"]
