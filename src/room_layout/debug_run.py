"""Debug-run trace persistence (Step 07 §4.7) — the D006 ``outputs/debug_runs``.

``run()`` is pure; this module is the **side-effecting consumer** of its
``on_stage`` callback (S07-D3). ``DebugRunWriter`` writes each ``StageOutput``
to ``NN_<stage_id>.json`` (the payload via the generic ``to_dict``), and
``write_debug_run`` orchestrates a full run into a D006 directory:

    outputs/debug_runs/<run_id>/
    ├── manifest.json            # seed, git_commit, config, timing, version
    ├── 00_input.json            # ShapeInput + ProgramRequest + seed
    ├── 01_atomize.json … 06_labeling.json   # if "json" in debug_artifacts
    ├── 06_labeling_f<level>.svg # canonical layered SVG, if "svg" selected
    └── final.json               # the returned LabeledRoomLayout (if "json")

Step 08 (S08-D9) adds SVG: ``SvgRunWriter`` renders the canonical per-floor
layered SVG (the ``labeling`` stage — the only one ``viz/svg.py`` handles;
geometry-stage debug stays the matplotlib path). ``write_debug_run`` fans the
``on_stage`` hook out to whichever writers ``RunConfig.debug_artifacts``
selects (``"json"`` / ``"svg"``). ``run_id`` defaults to
``seed<N>_<utc-isoformat>`` (sortable; same code+seed re-run makes a new folder
— preserves history).
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from room_layout import __version__
from room_layout.run import run
from room_layout.schema import (
    ProgramRequest,
    RunConfig,
    ShapeInput,
    StageOutput,
    to_dict,
)
from room_layout.viz.svg import render as render_svg


def _dump(path: Path, obj: object) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _git_commit() -> str | None:
    """Short HEAD commit, or ``None`` when the tree is dirty / git is unreadable."""
    try:
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        ).stdout.strip()
        if dirty:
            return None
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        return out or None
    except Exception:
        return None


@dataclass
class DebugRunWriter:
    """An ``on_stage`` callback that writes ``NN_<stage_id>.json`` per stage."""

    out_dir: Path

    def __call__(self, stage: StageOutput) -> None:
        # suffix the floor level so multi-floor runs don't overwrite (S07 review):
        # input has level=None → no suffix; per-floor stages → `_f<level>`.
        suffix = "" if stage.level is None else f"_f{stage.level}"
        name = f"{stage.index:02d}_{stage.stage_id}{suffix}.json"
        _dump(self.out_dir / name, to_dict(stage.payload))


@dataclass
class SvgRunWriter:
    """An ``on_stage`` callback that renders the canonical per-floor SVG (S08-D9).

    Only the ``labeling`` stage renders — its payload is the
    ``LabeledFloorLayout`` that ``viz/svg.py``'s ``render`` consumes. Geometry-
    stage debug (atoms / regions / graph / growth / corridor) stays the
    matplotlib dev-bridge path, so this writer ignores those stages and leaves
    the SVG's 6 debug layers empty (post-v1 extension). Closes over ``shape``
    for the footprint + vertical anchors the render needs.
    """

    out_dir: Path
    shape: ShapeInput

    def __call__(self, stage: StageOutput) -> None:
        if stage.stage_id != "labeling":
            return
        floor = next((f for f in self.shape.floors if f.level == stage.level), None)
        if floor is None:  # defensive — labeling always carries a real level
            return
        suffix = "" if stage.level is None else f"_f{stage.level}"
        out = self.out_dir / f"{stage.index:02d}_labeling{suffix}.svg"
        render_svg(floor, stage.payload, out, anchors=self.shape.vertical_anchors)


def _fanout(writers: list[Callable[[StageOutput], None]]):
    """Combine 0+ ``on_stage`` writers into one callback (``None`` if empty)."""
    if not writers:
        return None
    if len(writers) == 1:
        return writers[0]

    def emit(stage: StageOutput) -> None:
        for w in writers:
            w(stage)

    return emit


def write_debug_run(
    shape: ShapeInput,
    program: ProgramRequest,
    *,
    seed: int,
    out_root: Path | str = "outputs/debug_runs",
    run_id: str | None = None,
    config: RunConfig | None = None,
    fixture_name: str | None = None,
):
    """Run ``run()`` and persist its full trace under ``out_root/<run_id>/``.

    Returns ``(result, out_dir)`` — the in-memory ``LabeledRoomLayout`` and the
    directory it was written to.
    """
    config = config or RunConfig()
    fmts = config.debug_artifacts
    started = datetime.now(UTC)
    run_id = run_id or f"seed{seed}_{started.strftime('%Y-%m-%dT%H-%M-%S')}"
    out_dir = Path(out_root) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    writers: list = []
    if "json" in fmts:
        writers.append(DebugRunWriter(out_dir))
    if "svg" in fmts:
        writers.append(SvgRunWriter(out_dir, shape))

    result = run(shape, program, seed=seed, on_stage=_fanout(writers))
    ended = datetime.now(UTC)

    if "json" in fmts:
        _dump(out_dir / "final.json", to_dict(result))
    _dump(
        out_dir / "manifest.json",
        {
            "seed": seed,
            "fixture_name": fixture_name,
            "git_commit": _git_commit(),
            "config": to_dict(config),
            "started_at": started.isoformat(),
            "ended_at": ended.isoformat(),
            "duration_ms": int((ended - started).total_seconds() * 1000),
            "package_version": __version__,
        },
    )
    return result, out_dir
