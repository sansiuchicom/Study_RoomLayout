"""`RunConfig` — cross-cutting run configuration (D006 manifest ``config``).

Plan reference: ``007_Step07_EntryPoint_Plan.md`` §4.7 + D006.

Serialized into the debug-run ``manifest.json`` (``config`` field). Step 08
(S08-D9) turns ``debug_artifacts`` from a bare ``bool`` into a format selector
now that a second artifact format (SVG) exists alongside JSON.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunConfig:
    #: Which per-stage debug artifacts ``write_debug_run`` emits (D006 / S08-D9).
    #: A tuple of format tokens: ``"json"`` (the per-stage + final JSON trace)
    #: and/or ``"svg"`` (the canonical per-floor layered SVG — ``viz/svg.py``).
    #: Empty = emit none (only ``manifest.json``). ``run()`` itself never reads
    #: this — it is pure; only the side-effecting debug-run helper does.
    debug_artifacts: tuple[str, ...] = ("json",)
