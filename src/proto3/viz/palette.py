"""Visual vocabulary v1 (S03-D4).

Codifies the suggested-treatment table from Pipeline Overview §12.3 plus the
12-layer order from D013. Single source of truth for the renderer in svg.py.
"""
from __future__ import annotations


LAYER_ORDER: list[str] = [
    "footprint",
    "anchors",
    "regions",
    "atoms",
    "graph-edges",
    "role-scores",
    "spine",
    "slots",
    "seeds",
    "grown",
    "doors",
    "failure",
]


LAYER_COLORS: dict[str, str] = {
    "footprint": "#000",
    "anchors": "#444",
    "public-hub": "#ffb84d",
    "private": "#8cc97a",
    "wet-service": "#b58ad1",
    "corridor": "#888",
    "spine": "#3f7cd0",
    "invalid": "#e04a3a",
    "sliver": "#aaa",
}


_ROLE_TO_PALETTE_KEY: dict[str, str] = {
    "public": "public-hub",
    "hub": "public-hub",
    "private": "private",
    "wet": "wet-service",
    "service": "wet-service",
    "corridor": "corridor",
}


def role_to_palette_key(role: str) -> str:
    """Map SpaceUnitSpec.role enum to LAYER_COLORS key.

    Unknown roles fall back to "private". Formal mapping from
    ProgramInstance.category to palette key is yielded to Step 06
    (Program & Domain Constraint Engine) per S04-D7 (R-S03-2).
    """
    return _ROLE_TO_PALETTE_KEY.get(role, "private")


GRID_SPACING_MM: int = 100
LABEL_FONT_FAMILY: str = "sans-serif"
LABEL_FONT_SIZE_RATIO: float = 0.015
