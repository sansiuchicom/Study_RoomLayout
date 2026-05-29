"""Dev-bridge CLI — render any showcase case through any stage to PNG.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.12 + S03-D4 / D12;
extended for Step 04 stages in ``004_Step04_AlgorithmCore_Plan.md`` §4.16.

Orchestrates the pipeline and the per-stage renderers, writing figures to
``outputs/step04/<case>/<stage>.png`` (D006 dev target, gitignored). The
renderers take stage outputs as parameters; this CLI runs the algorithm and
feeds them.

The Step 04 stages (``seed`` / ``layout`` / ``corridor``) render the
**production path**: the new-schema ``ProgramRequest`` (``input.json``'s
``program``) → ``program_to_fixture`` → auto seed placement → growth → carve.
(The manual-seed goldens have their own committed PNG sidecars under
``tests/golden/``.)

Usage::

    python -m room_layout.viz.demo --case 5 --stage atomize
    python -m room_layout.viz.demo --case 33 --stage corridor
    python -m room_layout.viz.demo --all --stage all

Cases are read from the golden fixtures (``tests/golden/case_*/input.json``).
Requires the ``viz`` extra (matplotlib); not exercised in CI.
"""

import argparse
import json
import sys
from pathlib import Path

from room_layout.schema import ProgramRequest, ShapeInput, from_dict
from room_layout.stages.atomize import atomize
from room_layout.stages.corridor import carve_corridors
from room_layout.stages.growth_partition import region_partition_growth
from room_layout.stages.growth_seed import auto_place_seeds_by_cells
from room_layout.stages.program_adapter import program_to_fixture
from room_layout.stages.region_graph import build_region_graph
from room_layout.stages.regionize import regionize
from room_layout.stages.territory import resolve_territories
from room_layout.viz.stages.atomize import save_atom_figure
from room_layout.viz.stages.corridor import save_corridor_figure
from room_layout.viz.stages.input import save_input_figure
from room_layout.viz.stages.layout import save_layout_figure
from room_layout.viz.stages.regionize import save_region_figure, save_region_graph_figure
from room_layout.viz.stages.seed import save_seed_figure

STAGES = (
    "input",
    "atomize",
    "regionize",
    "region_graph",
    "seed",
    "layout",
    "corridor",
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_GOLDEN = _REPO_ROOT / "tests" / "golden"


def _case_dirs(golden_dir: Path) -> list[Path]:
    return sorted(p for p in golden_dir.iterdir() if p.is_dir() and p.name.startswith("case_"))


def _select_cases(golden_dir: Path, indices: list[int] | None) -> list[Path]:
    dirs = _case_dirs(golden_dir)
    if not indices:
        return dirs
    by_index = {int(p.name.split("_")[1]): p for p in dirs}
    out = []
    for i in indices:
        if i not in by_index:
            raise SystemExit(f"no case with index {i} under {golden_dir}")
        out.append(by_index[i])
    return out


def _load_case(case_dir: Path):
    with (case_dir / "input.json").open(encoding="utf-8") as f:
        data = json.load(f)
    floor = from_dict(ShapeInput, data["shape"]).floors[0]
    program = from_dict(ProgramRequest, data["program"])
    return floor, program


def _render(case_dir: Path, stage: str, out_dir: Path) -> Path:
    floor, program = _load_case(case_dir)
    dest = out_dir / case_dir.name / f"{stage}.png"
    title = f"{case_dir.name} — {stage}"

    if stage == "input":
        return save_input_figure(floor, dest, title=title)
    atoms = atomize(floor)
    if stage == "atomize":
        return save_atom_figure(floor, atoms, dest, title=title)
    regions = regionize(floor, atoms=atoms)
    if stage == "regionize":
        return save_region_figure(floor, atoms, regions, dest, title=title)
    graph = build_region_graph(floor, atoms=atoms, regions=regions)
    if stage == "region_graph":
        return save_region_graph_figure(floor, graph, dest, title=title)

    # Step 04 stages — production / auto path via the program adapter.
    fixture = program_to_fixture(floor, program)
    if stage == "seed":
        territories = resolve_territories(floor)
        placements = auto_place_seeds_by_cells(
            floor, graph, territories, K=fixture.K, has_public=fixture.hub_room_index is not None
        )
        return save_seed_figure(floor, regions, placements, dest, title=f"{title} (auto)")
    growth = region_partition_growth(floor, fixture, regions=regions, region_graph=graph)
    if stage == "layout":
        return save_layout_figure(floor, regions, growth, dest, title=f"{title} (auto)")
    if stage == "corridor":
        carved = carve_corridors(floor, growth, regions=regions, region_graph=graph)
        return save_corridor_figure(
            floor, regions, carved, dest, region_graph=graph, title=f"{title} (auto)"
        )
    raise SystemExit(f"unknown stage {stage!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--case", type=int, action="append", help="case index (repeatable); omit with --all"
    )
    parser.add_argument("--all", action="store_true", help="render every showcase case")
    parser.add_argument("--stage", choices=(*STAGES, "all"), default="all")
    parser.add_argument("--out", default=str(_REPO_ROOT / "outputs" / "step04"))
    parser.add_argument("--golden-dir", default=str(_DEFAULT_GOLDEN))
    args = parser.parse_args(argv)

    golden_dir = Path(args.golden_dir)
    if not golden_dir.exists():
        raise SystemExit(f"golden dir not found: {golden_dir}")
    if not args.all and not args.case:
        parser.error("pass --case <n> (repeatable) or --all")

    cases = _select_cases(golden_dir, None if args.all else args.case)
    stages = STAGES if args.stage == "all" else (args.stage,)
    out_dir = Path(args.out)

    for case_dir in cases:
        for stage in stages:
            path = _render(case_dir, stage, out_dir)
            print(f"saved {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
