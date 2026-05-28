"""room_layout.viz.stages — dev-bridge matplotlib renderers (Phase 3–5).

Per-stage renderers selectively ported from Cell ``viz.py`` (S03-D4):
visual vocabulary mirrored (color palette, label format, backdrop +
overlay pattern), code written fresh against the new schema.

Module layout (Plan §3):

    input.py     save_input_figure (lands with the demo CLI, 4.12)
    atomize.py   save_atom_figure
    regionize.py save_region_figure + save_region_graph_figure

(No gates renderer — `shape_gate` is a Phase 6/7 helper deferred to
Step 04, not a Phase-5 stage; S03-D16.)

Renderers take **outputs** (lists of ``Atom`` / ``Region`` / the
``RegionGraph``) as parameters rather than running the algorithm
internally.
The CLI ``viz/demo.py`` (work item 4.12) orchestrates: run pipeline →
pass results to renderer → save PNG.

Step 07 replaces this dev bridge with canonical SVG rendering. The code
here is intentionally thin and throwaway.

Re-exports populated in subsequent work items (4.7 onward).
"""
