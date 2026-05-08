"""RunConfig — runtime configuration (S02-D4) + Stage 00 consistency check (S02-D14).

Minimal start (6 fields). Extension policy: new fields require defaults
(backward-compat) and Plan §2 decision-ID record. See
002_Step02_CoreSchema_Plan.md §2/S02-D4 for full extension policy and
predicted growth points (Step 04, 07, 08, 11, 13, 14).
"""
from __future__ import annotations

from dataclasses import dataclass

from .schema.input import BuildingInput, TargetType


@dataclass
class RunConfig:
    """Runtime configuration for one proto3 search run.

    All new fields MUST have defaults (S02-D4 extension policy) so that
    existing call sites and saved run_config.json files remain valid.
    """
    target_type: TargetType = "apartment"  # run-time intent; must match BuildingInput.target_type at Stage 00 (S02-D14)
    atom_size_mm: int = 300                # default layout atom side (D006 amended by D019; was 600)
    atom_inclusion_threshold: float = 0.5  # boundary-cell area fraction to include as atom (D019, v3.2 50% merge rule)
    min_atom_side_mm: int = 300            # deprecated by D019 — superseded by atom_inclusion_threshold; kept for backward compat
    door_min_boundary_mm: int = 800        # door-capable shared boundary minimum (D006, Pipeline §8)
    random_seed: int | None = None         # reproducibility; None = nondeterministic
    debug_run_id: str | None = None        # outputs/debug_runs/<this>/; None = auto-generate


def assert_target_consistent(run_config: RunConfig, building: BuildingInput) -> None:
    """Enforce RunConfig.target_type == BuildingInput.target_type at Stage 00 (S02-D14).

    The two carry the same value but distinct meanings (run intent vs data
    identity), so a mismatch is a real error — not a silent default.
    """
    if run_config.target_type != building.target_type:
        raise ValueError(
            f"target_type mismatch: RunConfig={run_config.target_type!r}, "
            f"BuildingInput={building.target_type!r}"
        )
