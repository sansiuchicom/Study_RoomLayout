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
    """Map SpaceUnitSpec.role to LAYER_COLORS key.

    Step 06 §4.7 (S06-D11): unknown roles raise ValueError. The Step 03 frame
    silently fell back to "private" — that hid typo bugs and conflicted with
    Stage 01's strict role validation (S06-D10). Failing here is consistent
    with D004/D005 fail-loud policy. Schema diff is the explicit path to
    add a new role (extend `Role` Literal in proto3.schema.program +
    `_ROLE_TO_PALETTE_KEY` here).
    """
    try:
        return _ROLE_TO_PALETTE_KEY[role]
    except KeyError:
        raise ValueError(
            f"role_to_palette_key: unknown role {role!r}; "
            f"allowed roles: {sorted(_ROLE_TO_PALETTE_KEY)}"
        ) from None


GRID_SPACING_MM: int = 100
LABEL_FONT_FAMILY: str = "sans-serif"
LABEL_FONT_SIZE_RATIO: float = 0.015
