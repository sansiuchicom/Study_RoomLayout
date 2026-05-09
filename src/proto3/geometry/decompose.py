"""High-level decomposition entry point.

Ported from references/cell_v3_2.md §10. Step 05 §4.5 adds `to_schema()` to
convert the raw shapely-based dict into the proto3 `Decomposition` schema.

**Two callable entry points** (R-S05-7 mitigation):

- `auto_partition(footprint_m, ...)` — original v3.2 algorithm, m-unit. Use for
  external comparison, debugging against v3.2 stress-test artifacts, or when
  callers already work in m.
- `run(footprint_mm, ...)` — proto3 default, mm-unit. Wraps `auto_partition` with
  on-entry mm→m conversion and on-exit m→mm conversion of cells/pieces. Most
  proto3 callers (Stage 04 integration in Step 07, fixtures, notebooks) should
  use this.
"""
from __future__ import annotations

import shapely.affinity as sa
import shapely.geometry as sg

from proto3.schema.geometry import Decomposition, GeometricPiece
from proto3.schema.region_atom import Atom

from .recursive import recursive_progressive_per_family


_MM_PER_M = 1000.0


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


def run(footprint_mm,
        target_cell_size_mm=300,
        seed=42,
        max_depth=3,
        min_lir_ratio=0.4,
        min_recurse_area_m2=8.0):
    """proto3-friendly mm-unit entry point. Wraps `auto_partition` with unit conversion.

    proto3 schema (D006) uses mm; the underlying v3.2 algorithm uses m. This
    wrapper converts on entry (footprint mm → m) and on exit (cells/pieces m → mm)
    so callers can stay in mm consistently with `BuildingInput.floors[*].footprint`.

    Args:
        footprint_mm: shapely.Polygon in mm coordinates (proto3 schema convention).
        target_cell_size_mm: nominal cell side in mm (default 300; v3.2 0.3 m).
        seed, max_depth, min_lir_ratio: forwarded to `auto_partition` (unit-agnostic).
        min_recurse_area_m2: minimum recursable polygon area in m² (kept in m² for
            architectural intuition — 8 m² ≈ small studio; the algorithm sees this
            as 8.0 internally).

    Returns:
        Same dict shape as `auto_partition`, but cells/pieces/root_main_rect are
        in mm coordinates. `cell_w` / `cell_h` are also in mm.

    R-S05-7 mitigation: removes the per-call `(x/1000, y/1000)` conversion that
    test_geometry_decompose previously did inline. Stage 00 normalization layer
    (Step 07 Plan §5 Def-14) will absorb broader unit normalization, including
    BuildingInput → run dispatch and ContactGraph mm-aware door checks.
    """
    coords_m = [(x / _MM_PER_M, y / _MM_PER_M)
                for x, y in footprint_mm.exterior.coords[:-1]]
    poly_m = sg.Polygon(coords_m)

    raw_m = auto_partition(
        poly_m,
        target_cell_size=target_cell_size_mm / _MM_PER_M,
        seed=seed,
        max_depth=max_depth,
        min_lir_ratio=min_lir_ratio,
        min_recurse_area=min_recurse_area_m2,
    )

    cells_mm = [
        (sa.scale(c, xfact=_MM_PER_M, yfact=_MM_PER_M, origin=(0, 0)), pid)
        for c, pid in raw_m['cells']
    ]
    pieces_mm = [
        {
            **p,
            'polygon': sa.scale(p['polygon'], xfact=_MM_PER_M, yfact=_MM_PER_M, origin=(0, 0)),
            'cell_w': p['cell_w'] * _MM_PER_M,
            'cell_h': p['cell_h'] * _MM_PER_M,
        }
        for p in raw_m['pieces']
    ]
    root_mm = (sa.scale(raw_m['root_main_rect'],
                        xfact=_MM_PER_M, yfact=_MM_PER_M, origin=(0, 0))
               if raw_m['root_main_rect'] is not None else None)

    return {'cells': cells_mm, 'pieces': pieces_mm, 'root_main_rect': root_mm}


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
