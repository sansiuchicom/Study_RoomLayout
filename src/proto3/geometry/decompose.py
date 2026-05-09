"""High-level decomposition entry point.

Ported from references/cell_v3_2.md §10. Step 05 §4.5 adds `to_schema()` to
convert the raw shapely-based dict into the proto3 `Decomposition` schema.
"""
from __future__ import annotations

from proto3.schema.geometry import Decomposition, GeometricPiece
from proto3.schema.region_atom import Atom

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

    For the proto3 schema form, pass this result through `to_schema()`.
    """
    cells, pieces, root_main, _ = recursive_progressive_per_family(
        footprint, target_cell_size=target_cell_size, seed=seed,
        max_depth=max_depth, min_lir_ratio=min_lir_ratio,
        min_recurse_area=min_recurse_area,
    )
    return {'cells': cells, 'pieces': pieces, 'root_main_rect': root_main}


def _vertices_of(polygon):
    """Extract a polygon's exterior vertex list (drop the closing duplicate)."""
    return [tuple(c) for c in polygon.exterior.coords[:-1]]


def to_schema(raw) -> Decomposition:
    """Convert raw `auto_partition` output dict to the `Decomposition` schema.

    Maps the shapely-based algorithm output into vertex-list-based dataclasses
    (S05-D5, M2). Atoms reference their parent piece by index into `pieces`.
    """
    pieces = [
        GeometricPiece(
            polygon_vertices=_vertices_of(p['polygon']),
            theta=p['theta'],
            role=p['role'],
            name=p['name'],
            depth=p['depth'],
            family_id=p['family_id'],
            cell_w=p['cell_w'],
            cell_h=p['cell_h'],
            n_cells=p['n_cells'],
        )
        for p in raw['pieces']
    ]

    atoms = []
    for i, (cell, piece_id) in enumerate(raw['cells']):
        family_id = pieces[piece_id].family_id if pieces else 0
        atoms.append(Atom(
            atom_id=f"atom_{i:05d}",
            parent_piece_id=piece_id,
            family_id=family_id,
            vertices=_vertices_of(cell),
            center=tuple(cell.centroid.coords[0]),
        ))

    root_vertices = (_vertices_of(raw['root_main_rect'])
                     if raw['root_main_rect'] is not None else None)

    return Decomposition(
        pieces=pieces,
        atoms=atoms,
        root_main_rect_vertices=root_vertices,
    )
