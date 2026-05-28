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
from tests._golden import assert_golden

from room_layout.schema import ShapeInput, from_dict, to_dict
from room_layout.stages._helpers import to_shapely
from room_layout.stages.atomize import Atom, atomize
from room_layout.stages.regionize import Region, regionize

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
        cached = {"floor": floor, "atoms": atoms, "regions": regions}
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


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=_CASE_IDS)
def test_regionize_golden(case_dir: Path, update_goldens: bool):
    record = regionize_golden(_pipeline(case_dir)["regions"])
    assert_golden(record, case_dir / "regionize.json", update_goldens=update_goldens)
