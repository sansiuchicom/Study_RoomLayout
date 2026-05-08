"""Geometry schemas: GeometricPiece, Decomposition (S05-D5, D019).

Output of the v3.2 algorithm (`proto3.geometry.decompose.auto_partition`).

**Layer separation (M2 decision)**:
  - `GeometricPiece` is the algorithm-derived geometric subdivision — no architectural
    label. Carries algorithm role ('main' | 'terminal'), recursion depth, family/theta,
    and per-family cell sizing.
  - `Region` (D006, see `region_atom.py`) is the coarse architectural territory layer
    (lobe / bay / public-candidate / private-candidate). It is *not* populated here.
    Step 07 maps `GeometricPiece` → `Region` candidate (geometry); Step 09 spine
    candidate analysis assigns architectural labels.

`Decomposition` bundles the algorithm output: a list of pieces, the atoms tied to
each piece (`Atom.parent_piece_id` indexes into `pieces`), and the top-level LIR
(`root_main_rect_vertices`) for diagnostic / visualization use.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .region_atom import Atom


@dataclass
class GeometricPiece:
    """One geometric subdivision emitted by the v3.2 recursive decomposition.

    Vertices are stored as a vertex list (matches `BuildingInput.floors[*].footprint`
    convention) — simple polygon, single ring, no holes (v3.2 cells/pieces are always
    simple). For shapely operations, wrap as `shapely.Polygon(piece.polygon_vertices)`.
    """
    polygon_vertices: list[tuple[float, float]] = field(default_factory=list)
    theta: float = 0.0          # family rotation in radians, in [0, π/2)
    role: str = "terminal"      # algorithm role: 'main' (LIR-fitted) | 'terminal' (no recursion)
    name: str = ""              # algorithm-derived label, e.g. 'd0_main', 'd1_terminal'
    depth: int = 0              # recursion depth at which this piece was emitted
    family_id: int = 0          # same-theta + phase-chain group
    cell_w: float = 0.0         # per-family cell width (m)
    cell_h: float = 0.0         # per-family cell height (m)
    n_cells: int = 0            # number of atoms inside this piece


@dataclass
class Decomposition:
    """Result of v3.2 cell partition for one footprint.

    Step 05 output. Step 07 will additionally map each piece (or group of pieces)
    onto `Region` candidates per the M2 architecture.
    """
    pieces: list[GeometricPiece] = field(default_factory=list)
    atoms: list[Atom] = field(default_factory=list)
    root_main_rect_vertices: list[tuple[float, float]] | None = None
