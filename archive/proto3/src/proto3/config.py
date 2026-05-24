"""RunConfig — runtime configuration (S02-D4) + Stage 00 consistency check (S02-D14).

Minimal start (6 fields). Extension policy: new fields require defaults
(backward-compat) and Plan §2 decision-ID record. See
002_Step02_CoreSchema_Plan.md §2/S02-D4 for full extension policy and
predicted growth points (Step 04, 07, 08, 11, 13, 14).

Step 06 §4.7 (S06-D14) adds `__post_init__` value-range validation —
fail-loud on impossible values (e.g., `atom_size_mm=0`,
`atom_inclusion_threshold=2.0`) instead of silent downstream errors.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .schema.input import BuildingInput, TargetType


@dataclass
class RunConfig:
    """Runtime configuration for one proto3 search run.

    All new fields MUST have defaults (S02-D4 extension policy) so that
    existing call sites and saved run_config.json files remain valid.

    `__post_init__` enforces value ranges — silently accepting invalid
    values (e.g., negative atom_size, threshold > 1) lets bugs surface as
    confusing geometry errors many stages downstream (S06-D14, D005).
    """
    target_type: TargetType = "apartment"  # run-time intent; must match BuildingInput.target_type at Stage 00 (S02-D14)
    atom_size_mm: int = 300                # default layout atom side (D006 amended by D019; was 600)
    atom_inclusion_threshold: float = 0.5  # boundary-cell area fraction to include as atom (D019, v3.2 50% merge rule)
    min_atom_side_mm: int = 300            # deprecated by D019 — superseded by atom_inclusion_threshold; kept for backward compat
    door_min_boundary_mm: int = 800        # door-capable shared boundary minimum (D006, Pipeline §8)
    random_seed: int | None = None         # reproducibility; None = nondeterministic
    debug_run_id: str | None = None        # outputs/debug_runs/<this>/; None = auto-generate

    def __post_init__(self) -> None:
        # `type(x) is int` (not isinstance) — bool subclasses int and would
        # otherwise smuggle through (e.g., RunConfig(atom_size_mm=True) with
        # True silently meaning 1).
        if type(self.atom_size_mm) is not int or self.atom_size_mm <= 0:
            raise ValueError(
                f"RunConfig.atom_size_mm must be a positive int, "
                f"got {self.atom_size_mm!r}"
            )
        # threshold ∈ (0, 1] — 0 would include nothing, > 1 makes no sense.
        if (type(self.atom_inclusion_threshold) not in (int, float)
                or math.isnan(self.atom_inclusion_threshold)
                or math.isinf(self.atom_inclusion_threshold)
                or not (0 < self.atom_inclusion_threshold <= 1)):
            raise ValueError(
                f"RunConfig.atom_inclusion_threshold must be a finite number "
                f"in (0, 1], got {self.atom_inclusion_threshold!r}"
            )
        # min_atom_side_mm is deprecated (D019) but still has a value range.
        if type(self.min_atom_side_mm) is not int or self.min_atom_side_mm <= 0:
            raise ValueError(
                f"RunConfig.min_atom_side_mm must be a positive int "
                f"(deprecated by D019 but range still enforced), "
                f"got {self.min_atom_side_mm!r}"
            )
        if type(self.door_min_boundary_mm) is not int or self.door_min_boundary_mm < 0:
            raise ValueError(
                f"RunConfig.door_min_boundary_mm must be a non-negative int, "
                f"got {self.door_min_boundary_mm!r}"
            )


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
