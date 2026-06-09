"""room_layout.viz — stage-level rendering helpers.

Per the project's "viz at every Step" convention (S01-D10) and D006
(output directory convention), each pipeline stage's render fn lives
here. This package is intentionally scaffolded empty at Step 01 —
renderers arrive incrementally:

- **Step 03** (geometry pipeline port) brings Cell's matplotlib
  renderers as the development-bridge viz path (PNG output).
- **Step 07** (entry point + labeling) adds the final
  ``LabeledRoomLayout`` matplotlib renderer (polygonized rooms +
  corridor polygons + vc anchors) plus the ``on_stage`` /
  ``StageOutput`` JSON trace (D006).
- **Step 08** (SVG visualization) ships the canonical SVG renderer
  (``viz.svg.render``) plus the ``make_gif()`` pipeline-progression
  helper (adds ``pillow`` to the ``viz`` extra) and the single
  ``viz.palette`` visual vocabulary (S08-D6).

Package-level exports (S08-D2/D3/D6): ``LAYER_ORDER`` / ``ROLE_COLORS`` /
``role_color`` (palette) and ``render`` (SVG) are eager — all
matplotlib-free, so ``import room_layout.viz`` stays light (no ``viz``
extra needed; exercised by ``tests/test_smoke.py``). ``make_gif`` is
exposed **lazily** via ``__getattr__`` because it pulls the matplotlib
stage renderers — accessing it imports them on demand, so the bare
``import room_layout.viz`` does not require ``matplotlib``.

The filename written follows the D006 ``NN_<stage_id>.{json,svg,png}``
pattern. The caller (CLI helper, ``debug_run``, or test) supplies the
base directory; the render fns do not invent paths.
"""

from __future__ import annotations

from room_layout.viz.palette import LAYER_ORDER, ROLE_COLORS, role_color
from room_layout.viz.svg import render

__all__ = ["LAYER_ORDER", "ROLE_COLORS", "render", "role_color", "make_gif"]


def __getattr__(name: str):
    # make_gif lives in viz.gif, which imports the matplotlib stage renderers;
    # keep it out of the eager import path so `import room_layout.viz` stays
    # matplotlib-free (PEP 562 lazy attribute).
    if name == "make_gif":
        from room_layout.viz.gif import make_gif

        return make_gif
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
