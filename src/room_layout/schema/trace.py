"""`StageOutput` — the per-stage trace payload carried by ``run(on_stage=...)``.

Plan reference: ``007_Step07_EntryPoint_Plan.md`` §4.6 (+ S07-D3, D006).

``run()`` is pure; its only side-effect channel is the ``on_stage`` callback
(default ``None``). Each pipeline stage, after computing its output, calls
``on_stage(StageOutput(...))``. The callback is where persistence / rendering
happens — *outside* the pure core. This type is the contract between ``run()``
(the producer, §4.6) and the consumers (JSON serializer + ``manifest.json``
writer §4.7; canonical renderer Step 08).

``payload`` is the stage's **raw** output object (atoms / regions /
``RegionGraph`` / ``GrowthResult`` / ``CorridoredLayout`` /
``LabeledFloorLayout`` / the input snapshot); consumers dispatch on its type.
``index`` + ``stage_id`` drive the D006 ``NN_<stage_id>`` file layout; ``level``
disambiguates per-floor emissions in a multi-floor run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StageOutput:
    index: int
    stage_id: str
    payload: Any
    level: int | None = None
