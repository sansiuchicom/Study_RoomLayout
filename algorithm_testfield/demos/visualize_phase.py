"""Common phase visualization CLI for the 33 showcase cases.

Only the ``input`` phase is implemented in Phase 1. Future phases (atomizer,
regionizer, layout) add new renderers here so every phase uses the same case
indexing and output layout.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from celllayout_tf.cases import case_slug, selected_cases
from celllayout_tf.layout_fixtures import selected_fixtures
from celllayout_tf.viz import (
    save_atom_figure,
    save_atom_graph_figure,
    save_dimension_examples_figure,
    save_input_figure,
    save_layout_figure,
    save_region_graph_figure,
    save_region_figure,
    save_seed_figure,
    save_territory_figure,
)


PER_CASE_PHASES = (
    "input", "territory", "atom", "graph", "region", "region_graph",
    "seed", "layout",
)
SINGLETON_PHASES = ("dimensions",)
IMPLEMENTED_PHASES = PER_CASE_PHASES + SINGLETON_PHASES


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("case_indices", nargs="*", type=int)
    parser.add_argument("--phase", choices=IMPLEMENTED_PHASES, default="input")
    parser.add_argument("--out-root", default=str(ROOT / "outputs"))
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or [])
    if args.phase in SINGLETON_PHASES:
        out = _render_singleton(args.phase, args)
        print(f"saved: {out}")
        return 0

    failures = []
    for idx, name, shape in selected_cases(args.case_indices):
        try:
            out = _render_case(args.phase, idx, name, shape, args)
            print(f"saved: {out}")
        except Exception as exc:
            failures.append((idx, name, str(exc)))
            print(f"ERROR {idx}. {name}: {exc}")
    return 1 if failures else 0


def _render_case(phase, idx, name, shape, args):
    out_dir = Path(args.out_root) / phase
    out = out_dir / f"{case_slug(idx, name)}.png"
    if phase == "input":
        return save_input_figure(
            shape,
            out,
            title=f"{idx}. {name}: input parts",
        )
    if phase == "territory":
        return save_territory_figure(
            shape,
            out,
            title=f"{idx}. {name}: resolved territories",
        )
    if phase == "atom":
        return save_atom_figure(
            shape,
            out,
            title=f"{idx}. {name}: atoms",
        )
    if phase == "graph":
        return save_atom_graph_figure(
            shape,
            out,
            title=f"{idx}. {name}: atom graph",
        )
    if phase == "region":
        return save_region_figure(
            shape,
            out,
            title=f"{idx}. {name}: regions",
        )
    if phase == "region_graph":
        return save_region_graph_figure(
            shape,
            out,
            title=f"{idx}. {name}: region graph",
        )
    if phase == "layout":
        fixtures = selected_fixtures([idx])
        if not fixtures:
            raise ValueError(f"no fixture for case index {idx}")
        return save_layout_figure(
            shape,
            fixtures[0],
            out,
            title=f"{idx}. {name}: layout (region_priority_growth)",
        )
    if phase == "seed":
        fixtures = selected_fixtures([idx])
        if not fixtures:
            raise ValueError(f"no fixture for case index {idx}")
        fx = fixtures[0]
        return save_seed_figure(
            shape,
            out,
            K=fx.K,
            has_public=fx.hub_room_index is not None,
            title=f"{idx}. {name}: auto seed placement",
        )
    raise ValueError(f"unsupported phase: {phase}")


def _render_singleton(phase, args):
    out_dir = Path(args.out_root) / phase
    if phase == "dimensions":
        return save_dimension_examples_figure(out_dir / "split_interval_examples.png")
    raise ValueError(f"unsupported singleton phase: {phase}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
