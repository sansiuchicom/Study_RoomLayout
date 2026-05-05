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
    """Fine growth unit (§6.3)."""
    atom_id: str = ""
    parent_region_id: str | None = None
    center: tuple[float, float] | None = None
    vertices: list[tuple[float, float]] = field(default_factory=list)
    # TBD: area, exterior_contact flag, role scores


@dataclass
class AtomSet:
    """Candidate set of atoms tied to parent regions."""
    atoms: list[Atom] = field(default_factory=list)
    sliver_warnings: list[str] = field(default_factory=list)
    # TBD: tiny atom flags per RunConfig.min_atom_side_mm


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
