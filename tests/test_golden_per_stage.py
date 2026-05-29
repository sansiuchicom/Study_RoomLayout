"""Per-stage golden regression across the 33 showcase fixtures.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.8 + S03-D5 /
S03-D10 / S03-D14.

Each stage is driven over every ``tests/golden/case_*/`` fixture and
compared against its golden file (or rewritten under
``pytest --update-goldens``). Stages are added here as they land:

    atomize → atomize.json   (DIGEST per S03-D14, not full geometry)
    regionize → regionize.json     (4.9, full)
    region_graph → region_graph.json (4.10, full)
    gates → gates.json             (4.11, full)

No matplotlib import here — the digest / full-geometry comparison is
pure data, so this runs in CI without the ``viz`` extra. PNG sidecars
are generated + reviewed out of band (bootstrap / demo CLI).
"""

import json
from collections import Counter
from pathlib import Path

import pytest
from shapely.ops import unary_union
from tests._fixtures import load_growth_fixture, to_auto_fixture
from tests._golden import assert_golden

from room_layout.schema import ShapeInput, from_dict, to_dict
from room_layout.stages._helpers import to_shapely
from room_layout.stages.atomize import Atom, atomize
from room_layout.stages.corridor import carve_corridors
from room_layout.stages.growth_partition import region_partition_growth
from room_layout.stages.growth_seed import auto_place_seeds_by_cells
from room_layout.stages.region_graph import RegionGraph, build_region_graph
from room_layout.stages.regionize import Region, regionize
from room_layout.stages.territory import resolve_territories

GOLDEN_DIR = Path(__file__).parent / "golden"


def _case_dirs() -> list[Path]:
    if not GOLDEN_DIR.exists():
        return []
    return sorted(p for p in GOLDEN_DIR.iterdir() if p.is_dir() and p.name.startswith("case_"))


CASE_DIRS = _case_dirs()
_CASE_IDS = [p.name for p in CASE_DIRS] or None


def _load_floor(case_dir: Path):
    """Load the single floor from a fixture (S03-D13: stages are floor-scoped)."""
    with (case_dir / "input.json").open(encoding="utf-8") as f:
        data = json.load(f)
    shape = from_dict(ShapeInput, data["shape"])
    return shape.floors[0]


# Per-case pipeline cache: each fixture's Phase 3-5 stages run exactly once
# across the whole suite, shared by every per-stage golden test. Without it,
# each stage's golden test re-ran every upstream stage (atomize alone ran
# ~once per downstream stage per case). Module-level dict → persists for the
# session; outputs are immutable, so tests stay independent.
_PIPELINE_CACHE: dict[Path, dict] = {}


def _pipeline(case_dir: Path) -> dict:
    cached = _PIPELINE_CACHE.get(case_dir)
    if cached is None:
        floor = _load_floor(case_dir)
        atoms = atomize(floor)
        regions = regionize(floor, atoms=atoms)
        region_graph = build_region_graph(floor, atoms=atoms, regions=regions)
        cached = {
            "floor": floor,
            "atoms": atoms,
            "regions": regions,
            "region_graph": region_graph,
            "territories": resolve_territories(floor),
        }
        _PIPELINE_CACHE[case_dir] = cached
    return cached


def atomize_digest(atoms: tuple[Atom, ...]) -> dict:
    """Compact golden representation for atomize (S03-D14).

    Atoms are mechanical grid cells with no individual identity, so we
    pin only the gross structural quantities that a port regression would
    disturb: count, conserved area, per-part counts, sliver count,
    bounding box, and the distinct thetas present.
    """
    polys = [to_shapely(a.shape) for a in atoms]
    per_part = Counter(a.part_id for a in atoms)
    union = unary_union(polys) if polys else None
    has_bounds = union is not None and not union.is_empty
    return {
        "n_atoms": len(atoms),
        "total_area": round(sum(p.area for p in polys), 6),
        "per_part_counts": {str(k): per_part[k] for k in sorted(per_part)},
        "n_slivers": sum(1 for a in atoms if a.is_feature_sliver),
        "bbox": [round(v, 6) for v in union.bounds] if has_bounds else [],
        "thetas": sorted({round(a.theta, 9) for a in atoms}),
    }


def regionize_golden(regions: tuple[Region, ...]) -> list[dict]:
    """Full-geometry golden record for regionize (S03-D14), minus atom_ids.

    Each region is pinned by its decided geometry + metadata: region_id,
    area, part_id, piece_id, theta, cut_history, and the union polygon.
    `atom_ids` is deliberately excluded — it is provenance (which atomize
    cells fell in the region), brittle to atomize renumbering, and
    redundant with the polygon. regionize regressions surface as polygon
    / cut_history / count changes regardless.
    """
    return [
        {
            "region_id": r.region_id,
            "area": round(to_shapely(r.shape).area, 6),
            "part_id": r.part_id,
            "piece_id": r.piece_id,
            "theta": round(r.theta, 9),
            "cut_history": [list(c) for c in r.cut_history],
            "polygon": to_dict(r.shape),
        }
        for r in regions
    ]


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=_CASE_IDS)
def test_atomize_golden(case_dir: Path, update_goldens: bool):
    digest = atomize_digest(_pipeline(case_dir)["atoms"])
    assert_golden(digest, case_dir / "atomize.json", update_goldens=update_goldens)


def region_graph_golden(graph: RegionGraph) -> list[dict]:
    """Edges-only golden for region_graph (S03-D15).

    The regions are already pinned by ``regionize.json``; this stage adds
    the adjacency, so the golden stores only the edge records (floats
    rounded for stable diffs).
    """
    return [
        {
            "region_a": e.region_a,
            "region_b": e.region_b,
            "shared_boundary_length": round(e.shared_boundary_length, 6),
            "centroid_distance": round(e.centroid_distance, 6),
            "same_theta_group": e.same_theta_group,
            "exterior_contact": e.exterior_contact,
            "hole_contact": e.hole_contact,
        }
        for e in graph.edges
    ]


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=_CASE_IDS)
def test_regionize_golden(case_dir: Path, update_goldens: bool):
    record = regionize_golden(_pipeline(case_dir)["regions"])
    assert_golden(record, case_dir / "regionize.json", update_goldens=update_goldens)


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=_CASE_IDS)
def test_region_graph_golden(case_dir: Path, update_goldens: bool):
    record = region_graph_golden(_pipeline(case_dir)["region_graph"])
    assert_golden(record, case_dir / "region_graph.json", update_goldens=update_goldens)


def layout_golden(result) -> dict:
    """Region-id digest golden for region_partition_growth (S04-D5).

    Per room: name, role, the seed region (``region_ids[0]`` by construction —
    catches regionize boundary shifts that move a manual seed, consideration B),
    the **sorted** region-id membership + count, and area. Membership is sorted
    because insertion order is immaterial downstream (only the seed identity
    matters). Plus the unassigned regions (Phase 8 corridor candidates) and the
    min-area / hub diagnostics.
    """
    return {
        "rooms": [
            {
                "name": gr.name,
                "role": gr.role,
                "seed_region_id": gr.region_ids[0],
                "region_ids": sorted(gr.region_ids),
                "n_regions": len(gr.region_ids),
                "area_m2": round(gr.area_m2, 6),
            }
            for gr in result.rooms
        ],
        "unassigned_region_ids": list(result.unassigned_region_ids),
        "below_min_area": list(result.diagnostics.get("below_min_area", ())),
        "hub_room_index": result.diagnostics.get("hub_room_index"),
    }


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=_CASE_IDS)
def test_layout_golden(case_dir: Path, update_goldens: bool):
    p = _pipeline(case_dir)
    fixture = load_growth_fixture(case_dir)
    result = region_partition_growth(
        p["floor"], fixture, regions=p["regions"], region_graph=p["region_graph"]
    )
    assert_golden(layout_golden(result), case_dir / "layout.json", update_goldens=update_goldens)


# --- Auto seed-placement goldens (S04-D7: the production path; seeds computed,
# not Cell's manual coords). Driven by the seed-stripped fixture. ---


def auto_seed_golden(placements) -> list[dict]:
    """Auto seed-placement digest: region_id + phase, in placement order."""
    return [{"region_id": sp.region.region_id, "phase": sp.phase} for sp in placements]


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=_CASE_IDS)
def test_seed_golden(case_dir: Path, update_goldens: bool):
    p = _pipeline(case_dir)
    fixture = to_auto_fixture(load_growth_fixture(case_dir))
    placements = auto_place_seeds_by_cells(
        p["floor"],
        p["region_graph"],
        p["territories"],
        K=fixture.K,
        has_public=fixture.hub_room_index is not None,
    )
    assert_golden(
        auto_seed_golden(placements), case_dir / "seed.json", update_goldens=update_goldens
    )


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=_CASE_IDS)
def test_layout_auto_golden(case_dir: Path, update_goldens: bool):
    p = _pipeline(case_dir)
    fixture = to_auto_fixture(load_growth_fixture(case_dir))
    result = region_partition_growth(
        p["floor"], fixture, regions=p["regions"], region_graph=p["region_graph"]
    )
    assert_golden(
        layout_golden(result), case_dir / "layout_auto.json", update_goldens=update_goldens
    )


# --- Corridor carving golden (Phase 8 — Step 04 terminal output, S04-D2).
# Driven by the manual-seed growth (algorithm-faithful path, S04-D7 a1). ---


def corridor_golden(cl) -> dict:
    """Region-id digest for carve_corridors (S04-D5): post-carve room membership
    + base / shortcut / leftover corridor region sets + connectivity diagnostics.
    """
    return {
        "rooms": [
            {
                "name": r.name,
                "role": r.role,
                "region_ids": sorted(r.region_ids),
                "n_regions": len(r.region_ids),
                "area_m2": round(r.area_m2, 6),
            }
            for r in cl.rooms
        ],
        "base_corridor_region_ids": list(cl.base_corridor_region_ids),
        "shortcut_corridor_region_ids": list(cl.shortcut_corridor_region_ids),
        "leftover_region_ids": list(cl.leftover_region_ids),
        "disconnected_rooms": list(cl.diagnostics.get("disconnected_rooms", ())),
        "emptied_rooms": list(cl.diagnostics.get("emptied_rooms", ())),
    }


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=_CASE_IDS)
def test_corridor_golden(case_dir: Path, update_goldens: bool):
    p = _pipeline(case_dir)
    fixture = load_growth_fixture(case_dir)
    growth = region_partition_growth(
        p["floor"], fixture, regions=p["regions"], region_graph=p["region_graph"]
    )
    cl = carve_corridors(p["floor"], growth, regions=p["regions"], region_graph=p["region_graph"])
    assert_golden(corridor_golden(cl), case_dir / "corridor.json", update_goldens=update_goldens)


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=_CASE_IDS)
def test_corridor_auto_golden(case_dir: Path, update_goldens: bool):
    """Corridor on the auto-seed layout — production path end-to-end (S04-D7)."""
    p = _pipeline(case_dir)
    fixture = to_auto_fixture(load_growth_fixture(case_dir))
    growth = region_partition_growth(
        p["floor"], fixture, regions=p["regions"], region_graph=p["region_graph"]
    )
    cl = carve_corridors(p["floor"], growth, regions=p["regions"], region_graph=p["region_graph"])
    assert_golden(
        corridor_golden(cl), case_dir / "corridor_auto.json", update_goldens=update_goldens
    )
