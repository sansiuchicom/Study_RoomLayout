"""One-shot converter: Cell 33 showcase cases → JSON goldens.

Reads ``archive/celllayout/algorithm/celllayout_tf/cases.py`` (Cell
``ShapeInput`` geometry) + ``layout_fixtures.py`` (Cell
``LayoutFixture`` room programs), maps them to the new
``room_layout.schema`` types, and emits
``tests/golden/case_<idx>_<slug>/input.json`` for each case.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.3 + S03-D7.

After this script runs once and the goldens are committed, the Python
form of Cell fixtures is **retired** — fixtures live solely as JSON
under ``tests/golden/``. The script is kept in-tree as documentation
of how the goldens were seeded.

Schema mapping:

- Cell ``ShapeInput(name, parts)`` (single-floor, tuple of ``ShapePart``)
  → new ``ShapeInput(name, floors=[FloorShape(level=1, parts=parts,
  floor_to_floor_height=None)], vertical_anchors=[])``. Pipeline §2.1
  allows ``floor_to_floor_height=None`` for single-floor v1.
- Cell ``ShapePart`` ↔ new ``ShapePart`` — same field shape. Re-validated
  via the new ``__post_init__`` (which enforces orientation; Cell relied
  on ``shapely.geometry.polygon.orient`` upstream so all 33 cases
  conform).
- Cell ``LayoutFixture.rooms`` (``RoomSpec(name, role, seed_position)``)
  → ``ProgramRequest.floor_programs[1]`` (list of ``SpaceUnitSpec``).
- Cell ``RoomSpec.role`` (4-class: public/private/wet/service)
  → new ``Role`` (7-class superset, 1:1 for the 4 used here).
- Cell ``RoomSpec.seed_position`` is **dropped**: seed placement is a
  Phase 6+ concern, not part of the current schema. Step 04 will
  re-introduce it via a stage-internal type or via ``target_rules``.
- ``area_target_m2`` heuristic: ``footprint_area_m2 / num_rooms``. Cell
  fixtures don't carry a per-room target; Phase 6 growth will refine.
- ``area_min_m2``: from Cell's ``role_min_areas`` (public=8 / private=4 /
  wet=2 / service=3); roles outside that dict map to ``None``.
- ``min_dimension_m``: ``None`` (Cell doesn't track; Step 04+ may
  populate from ``DimensionPolicy``).
- ``required=True`` for every room (all Cell fixture rooms are required).
- ``target_type="apartment"`` for all 33 cases (Cell fixtures are Korean
  apartment-style layouts; this is a heuristic, refine in Step 05 when
  ``target_rules/`` lands).

Usage::

    PYTHONPATH=src python scripts/cell_fixtures_to_json.py
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CELL_ALGORITHM_ROOT = REPO_ROOT / "archive" / "celllayout" / "algorithm"

# Make Cell's `celllayout_tf` package importable without polluting the
# new package's namespace.
sys.path.insert(0, str(CELL_ALGORITHM_ROOT))

from celllayout_tf.cases import selected_cases  # noqa: E402
from celllayout_tf.layout_fixtures import selected_fixtures  # noqa: E402

from room_layout.schema import (  # noqa: E402
    FloorShape,
    ProgramRequest,
    ShapeInput,
    ShapePart,
    SpaceUnitSpec,
    to_dict,
)

# Korean → English slug replacements. Order matters: longer / compound
# forms first so partial-matches don't fire. Cell's own `case_slug`
# strips non-ASCII and produces lossy slugs (e.g., "타워형" → "case");
# we map meaningfully so `tests/golden/<dir>/` names are readable.
_SLUG_REPLACEMENTS: list[tuple[str, str]] = [
    # Korean compound shape names (ends in 자)
    ("ㄱ자", "l_shape"),
    ("ㄷ자", "c_shape"),
    ("7자", "j_shape"),
    ("T자", "t_shape"),
    ("十자", "cross"),
    ("ㅁ자", "donut"),
    ("E자", "e_shape"),
    ("ㄹ자", "z_shape"),
    # Standalone Korean shape letters (for cases like "Curved ㄱ")
    ("ㄱ", "l"),
    ("ㄷ", "c"),
    ("ㅁ", "donut"),
    ("ㄹ", "z"),
    # Korean words
    ("판상형", "flat"),
    ("타워형", "tower"),
    ("비대칭", "asym"),
    ("큰", "big"),
    ("평", "py"),
    # English shortening (longer first to avoid sub-match conflicts)
    ("asymmetric", "asym"),
    ("symmetric", "sym"),
    ("standard", "std"),
]


def _english_slug(name: str) -> str:
    """Map a Cell case name to a meaningful English slug.

    Applies a Korean→English replacement table then ASCII-normalizes
    the result. Unlike Cell's lossy `case_slug` (which strips all
    non-ASCII), this preserves the shape-name semantics.
    """
    s = name
    for src, dst in _SLUG_REPLACEMENTS:
        s = s.replace(src, dst)
    ascii_s = s.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_s).strip("_").lower()
    return slug or "case"


def _convert_part(cell_part) -> ShapePart:
    """Cell ShapePart → new ShapePart (re-validating via new __post_init__).

    Field shapes are identical; we just reconstruct so the new
    `_validate_ring` checks (orientation / non-zero area / is_simple)
    run on Cell data.
    """
    return ShapePart(exterior=cell_part.exterior, holes=cell_part.holes)


def _convert_shape(cell_shape) -> ShapeInput:
    """Cell single-floor ShapeInput → new multi-floor-capable ShapeInput.

    Wraps Cell's `parts` tuple inside a `FloorShape(level=1)` (the v1
    single-floor convention). `floor_to_floor_height=None` per
    Pipeline §2.1 — optional for single-floor inputs.
    """
    return ShapeInput(
        name=cell_shape.name,
        floors=[
            FloorShape(
                level=1,
                parts=[_convert_part(p) for p in cell_shape.parts],
                floor_to_floor_height=None,
            )
        ],
        vertical_anchors=[],
    )


def _convert_program(cell_fixture) -> ProgramRequest:
    """Cell LayoutFixture → new ProgramRequest (single floor)."""
    n = len(cell_fixture.rooms)
    if n == 0:
        raise ValueError(f"case {cell_fixture.case_index}: zero rooms")
    target_per_room = cell_fixture.footprint_area_m2 / n
    min_areas = cell_fixture.role_min_areas
    specs = [
        SpaceUnitSpec(
            id=room.name,
            role=room.role,
            usage=None,
            area_target_m2=target_per_room,
            area_min_m2=min_areas.get(room.role),
            min_dimension_m=None,
            required=True,
            anchor_id=None,
        )
        for room in cell_fixture.rooms
    ]
    return ProgramRequest(
        target_type="apartment",
        floor_programs={1: specs},
    )


def main() -> int:
    cases = selected_cases()
    fixtures = selected_fixtures()

    if len(cases) != len(fixtures):
        raise RuntimeError(
            f"case/fixture count mismatch: {len(cases)} cases vs {len(fixtures)} fixtures"
        )

    golden_dir = REPO_ROOT / "tests" / "golden"
    golden_dir.mkdir(exist_ok=True)

    failures: list[tuple[int, str, str]] = []
    written: list[Path] = []

    for (idx, name, cell_shape), fixture in zip(cases, fixtures, strict=True):
        if fixture.case_index != idx:
            raise RuntimeError(
                f"case/fixture index mismatch: shape idx={idx} ({name!r}) "
                f"vs fixture.case_index={fixture.case_index}"
            )

        try:
            new_shape = _convert_shape(cell_shape)
            new_program = _convert_program(fixture)
        except (ValueError, TypeError) as exc:
            failures.append((idx, name, str(exc)))
            print(f"  case {idx} {name!r}: CONVERSION FAILED — {exc}")
            continue

        slug = _english_slug(name)
        case_dir = golden_dir / f"case_{idx:02d}_{slug}"
        case_dir.mkdir(exist_ok=True)

        payload = {
            "shape": to_dict(new_shape),
            "program": to_dict(new_program),
        }

        path = case_dir / "input.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")
        written.append(path)
        print(f"  case {idx:2d} {name!r}: wrote {path.relative_to(REPO_ROOT)}")

    print()
    print(f"converted {len(written)}/{len(cases)} cases")
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for idx, name, msg in failures:
            print(f"  case {idx} {name!r}: {msg}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
