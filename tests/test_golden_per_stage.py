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

from room_layout.schema import ShapeInput, from_dict
from room_layout.stages._helpers import to_shapely
from room_layout.stages.atomize import Atom, atomize

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


@pytest.mark.parametrize("case_dir", CASE_DIRS, ids=_CASE_IDS)
def test_atomize_golden(case_dir: Path, update_goldens: bool):
    floor = _load_floor(case_dir)
    digest = atomize_digest(atomize(floor))
    assert_golden(digest, case_dir / "atomize.json", update_goldens=update_goldens)
