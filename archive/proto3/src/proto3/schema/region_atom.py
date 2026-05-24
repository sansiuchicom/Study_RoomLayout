"""Region/atom schemas: Region, RegionSet, Atom, AtomSet, ContactGraph.

Stage 04-05 outputs (Pipeline Overview §6.3, §9). Region/atom dual layer
(D006). Default atom resolution from RunConfig (S02-D4).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Region:
    """Coarse architectural territory (lobe, bay, pocket, neck, ...)."""
    region_id: str = ""
    kind: str = ""  # lobe | bay | pocket | neck | public | private | ...
    vertices: list[tuple[float, float]] = field(default_factory=list)
    parent_region_id: str | None = None
    # TBD: area, role-score fields


@dataclass
class RegionSet:
    """Candidate set of regions for one decomposition."""
    regions: list[Region] = field(default_factory=list)
    decomposition_score: float | None = None
    # TBD: provenance — which decomposition algorithm (Q001 deferred)


@dataclass
class Atom:
    """Fine growth unit (§6.3, D006).

    Layered field population across Steps:
      - Step 05: parent_piece_id (geometric subdivision ref) + family_id (same-theta group).
      - Step 07: parent_region_id (architectural label) when Region candidates are mapped.
      - Step 08: graph fields (exterior_contact, neighbor_atom_ids, role scores).
    """
    atom_id: str = ""
    parent_piece_id: int | None = None        # Step 05 — index into Decomposition.pieces
    parent_region_id: str | None = None       # Step 07 — architectural region label
    family_id: int = 0                         # Step 05 — same theta + phase chain group
    center: tuple[float, float] | None = None
    vertices: list[tuple[float, float]] = field(default_factory=list)
    # TBD (Step 08): exterior_contact flag, neighbor_atom_ids, role scores


@dataclass
class AtomSet:
    """Candidate set of atoms tied to parent regions."""
    atoms: list[Atom] = field(default_factory=list)
    sliver_warnings: list[str] = field(default_factory=list)
    # TBD (Step 08): tiny atom flags per RunConfig.atom_inclusion_threshold (D019 area-fraction rule supersedes earlier min_atom_side_mm-based plan)


@dataclass
class ContactGraph:
    """Contact graph for either region or atom level. node_kind disambiguates.

    edges entries (TBD: typed ContactEdge dataclass later):
        {node_a, node_b, shared_boundary_length_mm, door_capable, access_capable, ...}
    """
    node_kind: str = "atom"  # "region" | "atom"
    nodes: list[str] = field(default_factory=list)  # region_ids or atom_ids
    edges: list[dict] = field(default_factory=list)
    # TBD: typed ContactEdge in a later Step
