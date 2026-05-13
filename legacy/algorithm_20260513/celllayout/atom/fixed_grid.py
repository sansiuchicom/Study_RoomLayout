"""Simple fixed-grid baseline used by 02M_per_family.py visual comparisons."""
import numpy as np
import shapely.affinity as sa
import shapely.geometry as sg


def _grid_cells(piece, theta, cell_size):
    cx, cy = piece.centroid.x, piece.centroid.y
    rotated = sa.rotate(piece, -np.degrees(theta), origin=(cx, cy))
    minx, miny, maxx, maxy = rotated.bounds
    cells = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            inter = sg.box(x, y, x + cell_size, y + cell_size).intersection(rotated)
            if isinstance(inter, sg.Polygon) and inter.area > 1e-6:
                cells.append(sa.rotate(inter, np.degrees(theta), origin=(cx, cy)))
            elif hasattr(inter, "geoms"):
                for part in inter.geoms:
                    if isinstance(part, sg.Polygon) and part.area > 1e-6:
                        cells.append(sa.rotate(part, np.degrees(theta), origin=(cx, cy)))
            y += cell_size
        x += cell_size
    return cells


def auto_partition_final(footprint, cell_size=0.3, seed=42):
    """Return a minimal result shape compatible with the old 02L API."""
    cells = _grid_cells(footprint, 0.0, cell_size)
    pieces = [{
        "polygon": footprint,
        "theta": 0.0,
        "role": "fixed_grid",
        "name": "fixed_grid",
        "depth": 0,
        "family_id": 0,
        "cell_w": cell_size,
        "cell_h": cell_size,
        "n_cells": len(cells),
    }]
    return {"cells": [(cell, 0) for cell in cells], "pieces": pieces, "root_main_rect": None}
