"""room_layout.viz — stage-level rendering helpers.

Per the project's "viz at every Step" convention (S01-D10) and D006
(output directory convention), each pipeline stage's render fn lives
here. This package is intentionally scaffolded empty at Step 01 —
renderers arrive incrementally:

- **Step 03** (geometry pipeline port) brings Cell's matplotlib
  renderers as the development-bridge viz path (PNG output).
- **Step 07** (SVG visualization) ships the canonical SVG renderer
  plus the ``make_gif()`` composition helper (adds ``pillow`` or
  ``imageio`` to the ``viz`` extra at that point).

Target render-fn convention (when these land)::

    def render_atoms(atoms: list[Atom], path: Path) -> Path
    def render_regions(regions: list[Region], path: Path) -> Path
    def render_rooms(rooms: list[Room], path: Path) -> Path
    def render_corridors(rooms, corridors, path: Path) -> Path
    # ... one per pipeline stage (see docs/000_Pipeline_Overview.md §3)

The filename written follows the D006 ``NN_<stage_id>.{json,png}``
pattern. The caller (CLI helper or test) supplies the base directory
(``outputs/debug_runs/<run_id>/`` or ``tests/golden/<fixture_name>/``);
the render fn does not invent paths.

``matplotlib`` is an *optional* install — ``pip install
room_layout[viz]`` adds it. Importing ``room_layout.viz`` on its own
(without the renderers) succeeds and is exercised by
``tests/test_smoke.py``.
"""
