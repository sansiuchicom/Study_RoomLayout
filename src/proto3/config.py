"""RunConfig — runtime configuration (S02-D4).

Minimal start (6 fields). Extension policy: new fields require defaults
(backward-compat) and Plan §2 decision-ID record. See
002_Step02_CoreSchema_Plan.md §2/S02-D4 for full extension policy and
predicted growth points (Step 04, 07, 08, 11, 13, 14).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RunConfig:
    """Runtime configuration for one proto3 search run.

    All new fields MUST have defaults (S02-D4 extension policy) so that
    existing call sites and saved run_config.json files remain valid.
    """
    target_type: str = "apartment"        # apartment | house | hotel | warehouse | office (D003)
    atom_size_mm: int = 600                # default layout atom side (D006, Pipeline §8)
    min_atom_side_mm: int = 300            # below this is sliver (D006, Pipeline §8)
    door_min_boundary_mm: int = 800        # door-capable shared boundary minimum (D006, Pipeline §8)
    random_seed: int | None = None         # reproducibility; None = nondeterministic
    debug_run_id: str | None = None        # outputs/debug_runs/<this>/; None = auto-generate
