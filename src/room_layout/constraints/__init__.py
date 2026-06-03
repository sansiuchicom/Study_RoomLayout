"""room_layout.constraints — domain feasibility checks.

`gates.py` holds the pure **pre-growth** program-admission gates consumed by
`stages/stage02_gate.py` (Step 05, S05-D4) — aggregate (Σ fits) and
raise-on-first. `room_gate.py` holds the **post-growth** per-room area /
dimension check (Step 07 §4.5) — it measures actual grown polygons and
*collects* `FailureRecord`s instead of raising. See
``005_Step05_ProgramLayer_Plan.md`` §4.5 /
``007_Step07_EntryPoint_Plan.md`` §4.5.
"""
