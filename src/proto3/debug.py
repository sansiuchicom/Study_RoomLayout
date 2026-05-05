"""DebugArtifact + debug output folder contract (S02-D5).

Defines the canonical filename constants for outputs/debug_runs/<run_id>/
(Pipeline Overview §12.2) plus run_folder() and stage_svg_filename() helpers.
Actual write functions are deferred to Step 03 (visualization).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# --- Canonical JSON filenames (Pipeline Overview §12.2) -------------------
INPUT_FILENAME                  = "input.json"
RUN_CONFIG_FILENAME             = "run_config.json"
PROGRAM_INSTANCE_FILENAME       = "program_instance.json"
REGIONS_FILENAME                = "regions.json"
ATOMS_FILENAME                  = "atoms.json"
GRAPHS_FILENAME                 = "graphs.json"
SPINE_CANDIDATES_FILENAME       = "spine_candidates.json"
SEED_CANDIDATES_FILENAME        = "seed_candidates.json"
GROWTH_STEPS_FILENAME           = "growth_steps.json"
PRE_REPAIR_VALIDATION_FILENAME  = "pre_repair_validation.json"
REPAIR_OPERATIONS_FILENAME      = "repair_operations.json"
POST_REPAIR_VALIDATION_FILENAME = "post_repair_validation.json"
FAILURE_RECORDS_FILENAME        = "failure_records.json"
NO_GOOD_RECORDS_FILENAME        = "no_good_records.json"
FINAL_LAYOUT_FILENAME           = "final_or_invalid_layout.json"

# --- SVG filename prefix/suffix (dynamic per stage) -----------------------
STAGE_SVG_PREFIX = "stage_"
STAGE_SVG_SUFFIX = ".svg"

# --- Default debug folder root --------------------------------------------
DEFAULT_DEBUG_ROOT = Path("outputs/debug_runs")


def run_folder(run_id: str, base: Path = DEFAULT_DEBUG_ROOT) -> Path:
    """Path for one debug run's folder. Does not create it (write helpers do)."""
    return base / run_id


def stage_svg_filename(stage_num: int, name: str) -> str:
    """e.g., stage_svg_filename(8, 'spine') -> 'stage_08_spine.svg' (Pipeline §12.2)."""
    return f"{STAGE_SVG_PREFIX}{stage_num:02d}_{name}{STAGE_SVG_SUFFIX}"


@dataclass
class DebugArtifact:
    """One named artifact produced during a Stage run (cross-cutting infra).

    Pipeline Overview §12 lists this as cross-cutting infrastructure, not a
    Stage. Concrete write contract — file path, JSON vs SVG choice — is
    populated by Step 03 visualization.
    """
    kind: str = ""                                          # e.g., "regions", "spine_candidates"
    payload: dict = field(default_factory=dict)             # serialized form (TBD: Any later)
    provenance: dict = field(default_factory=dict)          # source candidate / stage (§12.1)
    # TBD: file_path, format ("json" | "svg"), stage_num
