"""Shared draw helpers for the dev-bridge matplotlib renderers.

Placeholder. Populated incrementally starting in work item 4.7 (the
first renderer to land).

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §3 + S03-D4.

Will provide:

- ``PART_COLORS`` palette (visual vocabulary reference: Cell
  ``viz.py::PART_COLORS``).
- ``configure_fonts()`` — Agg backend + font setup, called once per
  figure save.
- ``_draw_part(ax, part, color, idx)`` — fill a ``ShapePart`` with
  exterior + holes + a part label (`P{idx}\\n{theta:.1f}°`).
- ``_draw_footprint_outline(ax, shape)`` — union-of-parts outline
  drawn on top of part fills.
- ``_finish_axis(ax, shape)`` — axis bounds (margin around bounding
  box) + equal aspect + light grid.

Per S03-D4 (selective port), these mirror Cell ``viz.py`` private
helpers visually but are written against the new
``room_layout.schema.ShapePart``. Cell ``viz.py`` stays untouched in
``archive/`` as the visual-vocabulary reference.
"""
