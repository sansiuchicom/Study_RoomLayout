"""``make_gif`` — pipeline-progression GIF (Step 08 §4.6 — S08-D3/D4).

Animates one layout's geometry build-up: one frame per pipeline stage
(input → atomize → regionize → region_graph → growth → corridor → labeled),
composed from the **existing matplotlib stage renderers** via ``pillow``
(S08-D3 — not SVG rasterization, no ``cairosvg`` dep). The frames are the live
typed stage payloads collected from ``run()``'s ``on_stage`` hook (no pipeline
re-orchestration; ``run()`` stays pure — we only read its trace).

The ``seed`` stage is omitted: ``run()`` does not emit seed placements (a
growth sub-step), and re-deriving them would couple ``make_gif`` to growth
internals — the ``growth`` frame already shows the placed result. ``make_gif``
runs the pipeline fresh (it does not re-hydrate a debug-run dir — that would
mean deserializing JSON back into stage objects). Single-floor by default
(v1); ``level`` selects the floor to animate.

Needs the ``viz`` extra (``matplotlib`` + ``pillow``): ``pip install
room_layout[viz]``.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from room_layout.run import run
from room_layout.schema import ProgramRequest, ShapeInput
from room_layout.viz.stages.atomize import save_atom_figure
from room_layout.viz.stages.corridor import save_corridor_figure
from room_layout.viz.stages.final import save_labeled_floor_figure
from room_layout.viz.stages.input import save_input_figure
from room_layout.viz.stages.layout import save_layout_figure
from room_layout.viz.stages.regionize import save_region_figure, save_region_graph_figure


def make_gif(
    shape: ShapeInput,
    program: ProgramRequest,
    *,
    seed: int,
    out_path: str | Path,
    level: int | None = None,
    frame_ms: int = 900,
    loop: int = 0,
) -> str:
    """Render a pipeline-progression GIF for one floor's layout.

    Runs ``run(shape, program, seed=seed)``, collects each stage's live payload
    from the ``on_stage`` trace, renders the stages that ran to PNG frames (the
    matplotlib dev-bridge renderers), and stitches them into an animated GIF at
    ``out_path``. ``frame_ms`` is per-frame duration; ``loop=0`` loops forever.
    Returns ``out_path``. A run that fails early simply yields fewer frames
    (only the stages that emitted).
    """
    try:
        from PIL import Image
    except ImportError as e:  # pragma: no cover - environment guard
        raise RuntimeError(
            "make_gif needs pillow — install the viz extra: pip install room_layout[viz]"
        ) from e

    lvl = shape.floors[0].level if level is None else level
    floor = next(f for f in shape.floors if f.level == lvl)

    payloads: dict[str, object] = {}

    def collect(stage) -> None:
        if stage.level == lvl:
            payloads[stage.stage_id] = stage.payload

    run(shape, program, seed=seed, on_stage=collect)

    # (label, render-to-dest) in pipeline order; gated on the payload having
    # been emitted. `input` needs only the floor; the rest read `payloads`.
    plan: list[tuple[str, object]] = [
        ("0_input", lambda d: save_input_figure(floor, d, title="1 · input")),
    ]
    if "atomize" in payloads:
        plan.append(
            (
                "1_atomize",
                lambda d: save_atom_figure(floor, payloads["atomize"], d, title="2 · atomize"),
            )
        )
    if "regionize" in payloads:
        plan.append(
            (
                "2_regionize",
                lambda d: save_region_figure(
                    floor, payloads["atomize"], payloads["regionize"], d, title="3 · regionize"
                ),
            )
        )
    if "region_graph" in payloads:
        plan.append(
            (
                "3_region_graph",
                lambda d: save_region_graph_figure(
                    floor, payloads["region_graph"], d, title="4 · region graph"
                ),
            )
        )
    if "growth" in payloads:
        plan.append(
            (
                "4_growth",
                lambda d: save_layout_figure(
                    floor, payloads["regionize"], payloads["growth"], d, title="5 · growth"
                ),
            )
        )
    if "corridor" in payloads:
        plan.append(
            (
                "5_corridor",
                lambda d: save_corridor_figure(
                    floor, payloads["regionize"], payloads["corridor"], d, title="6 · corridor"
                ),
            )
        )
    if "labeling" in payloads:
        plan.append(
            (
                "6_labeled",
                lambda d: save_labeled_floor_figure(
                    floor, payloads["labeling"], d, title="7 · labeled"
                ),
            )
        )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        frames = []
        for name, render in plan:
            dest = Path(tmp) / f"{name}.png"
            render(dest)
            frames.append(Image.open(dest).convert("RGB"))

        # The renderers use bbox_inches="tight" → per-frame pixel sizes vary; a
        # GIF needs one frame size. Pad each frame (centered) onto a white canvas
        # sized to the largest frame so nothing is cropped or jitters.
        max_w = max(im.width for im in frames)
        max_h = max(im.height for im in frames)
        canvases = []
        for im in frames:
            canvas = Image.new("RGB", (max_w, max_h), "white")
            canvas.paste(im, ((max_w - im.width) // 2, (max_h - im.height) // 2))
            canvases.append(canvas)

        canvases[0].save(
            out,
            save_all=True,
            append_images=canvases[1:],
            duration=frame_ms,
            loop=loop,
        )
    return str(out_path)
