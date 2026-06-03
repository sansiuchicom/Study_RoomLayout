"""`RunConfig` — cross-cutting run configuration (D006 manifest ``config``).

Plan reference: ``007_Step07_EntryPoint_Plan.md`` §4.7 + D006.

Minimal in v1 — serialized into the debug-run ``manifest.json`` (``config``
field). Step 08 extends it (debug-overlay opt-in, render options); kept tiny
now so no speculative fields land before a consumer exists (honest-fix).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunConfig:
    #: opt-in for per-stage debug artifacts (Pipeline §2.3 / D006); wired by the
    #: debug-run helper, not by the pure ``run()``.
    debug_artifacts: bool = False
