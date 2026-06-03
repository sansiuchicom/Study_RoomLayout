"""Debug-run trace persistence (Step 07 §4.7) — the D006 ``outputs/debug_runs``.

``run()`` is pure; this module is the **side-effecting consumer** of its
``on_stage`` callback (S07-D3). ``DebugRunWriter`` writes each ``StageOutput``
to ``NN_<stage_id>.json`` (the payload via the generic ``to_dict``), and
``write_debug_run`` orchestrates a full run into a D006 directory:

    outputs/debug_runs/<run_id>/
    ├── manifest.json            # seed, git_commit, config, timing, version
    ├── 00_input.json            # ShapeInput + ProgramRequest + seed
    ├── 01_atomize.json … 06_labeling.json
    └── final.json               # the returned LabeledRoomLayout

Per-stage *rendering* (PNG/SVG, GIF) is Step 08 (D006); this ships only the
JSON trace + manifest. ``run_id`` defaults to ``seed<N>_<utc-isoformat>``
(sortable; same code+seed re-run makes a new folder — preserves history).
"""

from __future__ import annotations

import json
import subprocess
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
    started = datetime.now(UTC)
    run_id = run_id or f"seed{seed}_{started.strftime('%Y-%m-%dT%H-%M-%S')}"
    out_dir = Path(out_root) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    result = run(shape, program, seed=seed, on_stage=DebugRunWriter(out_dir))
    ended = datetime.now(UTC)

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
