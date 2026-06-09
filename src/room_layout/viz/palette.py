"""room_layout.viz.palette — single source of the visual vocabulary (S08-D6).

Plan reference: ``008_Step08_SvgVisualization_Plan.md`` §4.2 + S08-D2 / S08-D6.

One place for the colors + layer order + metric/text constants that BOTH the
matplotlib dev-bridge renderers (``viz/stages/*.py``) and the canonical SVG
renderer (``viz/svg.py``, Step 08) read — so the two paths cannot drift apart.
Before this module the role colors lived only in ``viz/stages/final.py``; that
table moved here and ``final.py`` now imports it (4.3).

Scope is the *canonical role / layer vocabulary*. ``PART_COLORS`` (per-part
index coloring) stays in ``viz/_helpers.py`` — it is matplotlib-debug-only
(input / atomize / regionize backdrops), not a role/layer concept, and the SVG
path never needs it.

Pure constants — **no matplotlib import**, so ``import room_layout.viz`` stays
light (exercised by ``tests/test_smoke.py``).
"""

from __future__ import annotations

# --- Layer stack (S08-D2) --------------------------------------------------
# Re-derived from OUR pipeline (Pipeline §3.1: footprint → atomize → regionize
# → region_graph → growth → corridor → polygonize → labeling), NOT proto3's
# spine-first ``LAYER_ORDER`` (its ``spine`` / ``role-scores`` / ``slots`` have
# no stage in our seed-first + post-hoc-carve pipeline — they would be dead
# layers). proto3's *structural* conventions are kept: the SVG renderer emits
# one ``<g class="layer-NN-name">`` per entry, in this order, low z → high z;
# a layer with no data registers as an empty ``<g>`` so the order stays stable
# as inputs vary (one entry == one draw fn).
#
# The canonical final render (4.4) lights: grid / footprint / anchors /
# corridor / rooms / labels. The remaining layers (atoms / regions /
# region-graph / seeds / grown / failure) are reserved for the per-stage debug
# SVGs the ``SvgRunWriter`` emits (4.5) — e.g. the atomize-stage SVG lights
# ``atoms``, the regionize-stage SVG lights ``regions``.
LAYER_ORDER: list[str] = [
    "grid",  # faint metric backdrop (GRID_SPACING_M)
    "footprint",  # floor boundary outline (FloorShape parts + holes)
    "atoms",  # debug: atom cells (~0.3 m²)
    "regions",  # debug: region fills (~3 m²)
    "region-graph",  # debug: region adjacency edges
    "anchors",  # vertical anchors — forbidden shafts + vc outline
    "seeds",  # debug: growth seed markers
    "grown",  # debug: pre-carve grown rooms
    "corridor",  # carved corridor polygons
    "rooms",  # FINAL labeled rooms, filled by 7-class role
    "labels",  # room text (id / usage / role / area)
    "failure",  # failure markers (overlay, top)
]

# --- Role fill colors (D004 — 7-class) -------------------------------------
# Authoritative role → fill. Migrated verbatim from ``viz/stages/final.py`` so
# the matplotlib path renders byte-identically after the 4.3 redirect.
# corridor / vc are muted greys (circulation).
ROLE_COLORS: dict[str, str] = {
    "public": "#a6cee3",
    "private": "#b2df8a",
    "service": "#fdbf6f",
    "wet": "#fb9a99",
    "hub": "#cab2d6",
    "corridor": "#dcdcdc",
    "vertical_circulation": "#b8b8b8",
}
ROLE_FALLBACK_COLOR: str = "#cccccc"

# --- Per-layer stroke / fill colors ----------------------------------------
# For the single-color structural + debug layers. ``rooms`` is colored by
# ``ROLE_COLORS`` (per room), ``labels`` by the font constants below — neither
# has a single layer color, so neither appears here.
LAYER_COLORS: dict[str, str] = {
    "grid": "#e8e8e8",
    "footprint": "#111111",
    "atoms": "#e0e0e0",
    "regions": "#cfe8e0",
    "region-graph": "#9aa0a6",
    "anchors": "#7a3b3b",  # the vc border brown final.py used
    "seeds": "#d62728",
    "grown": "#b3a2c7",
    "corridor": "#888888",
    "failure": "#e04a3a",
}

# --- Metric / text constants -----------------------------------------------
# proto3 worked in mm (``GRID_SPACING_MM = 100``); v1 is meters everywhere
# (``proto3:D019`` dropped — Pipeline §2.4). A 1 m major grid reads cleanly at
# apartment scale (~10 m); at 0.1 m it would be ~100 lines.
GRID_SPACING_M: float = 1.0
PADDING_RATIO: float = 0.05  # viewBox pad = 5% of the larger bbox edge (proto3 S03-D6)
LABEL_FONT_FAMILY: str = "sans-serif"
LABEL_FONT_SIZE_RATIO: float = 0.015  # of the larger bbox edge (proto3)


def role_color(role: str) -> str:
    """7-class ``role`` → fill color; ``ROLE_FALLBACK_COLOR`` for an unknown role.

    Tolerant (fallback, never raise) — a *renderer* must not be the thing that
    crashes a debug view, and ``run()`` already validates ``role`` against the
    ``Role`` ``Literal`` upstream, so an unknown role cannot reach a real
    render. (Contrast proto3's ``role_to_palette_key``, which *raised*: that was
    a pre-validation tool, this is a post-``run()`` renderer.) Mirrors the
    existing ``ROLE_COLORS.get(role, _FALLBACK_COLOR)`` in ``final.py``.
    """
    return ROLE_COLORS.get(role, ROLE_FALLBACK_COLOR)
