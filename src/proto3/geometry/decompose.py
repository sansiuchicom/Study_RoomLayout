"""High-level decomposition entry point.

Ported from references/cell_v3_2.md §10.

`auto_partition(footprint)` is the one-line entry: it accepts a footprint polygon
and returns a dict with `cells`, `pieces`, and `root_main_rect`. This is the
external surface for the v3.2 algorithm; downstream Steps (07 region mapping,
08 graph) consume this dict.

Note: this returns the raw v3.2 algorithm output. Conversion into proto3 schema
(`GeometricPiece` + `Decomposition` from `proto3.schema.geometry`) lands in
Step 05 §4.5; until then the dict shape is the contract.
"""
from __future__ import annotations

from .recursive import recursive_progressive_per_family


def auto_partition(footprint, target_cell_size=0.3, seed=42,
                   max_depth=3, min_lir_ratio=0.4, min_recurse_area=8.0):
    """Decompose a footprint polygon into per-family proportional atom cells.

    Args:
        footprint: shapely.Polygon (any orientation, holes OK).
        target_cell_size: nominal cell side (default 0.3 m). Actual sizing is
            family-proportional.
        seed: RNG seed (controls phase-origin randomization at the root).
        max_depth: recursion depth cap (default 3).
        min_lir_ratio: minimum LIR-to-polygon area ratio for recursion (default 0.4).
        min_recurse_area: polygons below this area are always terminal (default 8 m²).

    Returns:
        dict with keys:
            - `cells`: list of `(shapely.Polygon, piece_id)` tuples.
            - `pieces`: list of piece-info dicts (polygon, theta, role, family_id,
              cell_w, cell_h, depth, n_cells, ...).
            - `root_main_rect`: the top-level LIR (or None).
    """
    cells, pieces, root_main, _ = recursive_progressive_per_family(
        footprint, target_cell_size=target_cell_size, seed=seed,
        max_depth=max_depth, min_lir_ratio=min_lir_ratio,
        min_recurse_area=min_recurse_area,
    )
    return {'cells': cells, 'pieces': pieces, 'root_main_rect': root_main}
