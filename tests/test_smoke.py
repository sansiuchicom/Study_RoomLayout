"""Smoke tests for the proto3 package (Step 02 — S02-D6).

import-level smoke + dataclass instantiation + RunConfig defaults +
debug filename contracts. Behavior tests live in their own files.
"""
from pathlib import Path


def test_proto3_imports() -> None:
    """Package is installed and importable."""
    import proto3  # noqa: F401


def test_subpackage_imports() -> None:
    """All Step 02 modules import cleanly."""
    from proto3 import config, debug, schema  # noqa: F401


def test_22_schema_dataclasses_instantiate() -> None:
    """All 22 schema dataclasses must construct with defaults."""
    from proto3.schema import (
        AccessPolicy,
        Atom,
        AtomSet,
        BuildingInput,
        ClusterSpec,
        ContactGraph,
        FailureRecord,
        FloorInput,
        GrowthResult,
        HubCandidate,
        LayoutCandidate,
        NoGoodRecord,
        PersistentAnchor,
        ProgramInstance,
        Region,
        RegionSet,
        SeedCandidate,
        SlotCandidate,
        SpaceUnitSpec,
        SpineCandidate,
        TerminalCandidate,
        ValidationResult,
    )

    classes = [
        BuildingInput, FloorInput, PersistentAnchor,                              # input
        ProgramInstance, SpaceUnitSpec, ClusterSpec, AccessPolicy,                # program
        Region, RegionSet, Atom, AtomSet, ContactGraph,                           # region/atom
        HubCandidate, TerminalCandidate, SpineCandidate, SlotCandidate, SeedCandidate,  # candidate
        GrowthResult, LayoutCandidate,                                             # growth
        ValidationResult, FailureRecord, NoGoodRecord,                             # validation
    ]
    assert len(classes) == 22
    for c in classes:
        inst = c()
        assert inst is not None


def test_runconfig_defaults() -> None:
    """RunConfig defaults match S02-D4 / D006 / Pipeline §8."""
    from proto3.config import RunConfig

    c = RunConfig()
    assert c.target_type == "apartment"
    assert c.atom_size_mm == 300                 # D019 amended from 600 → 300
    assert c.atom_inclusion_threshold == 0.5     # D019 NEW (v3.2 50% rule)
    assert c.min_atom_side_mm == 300             # deprecated by D019, kept for backward compat
    assert c.door_min_boundary_mm == 800
    assert c.random_seed is None
    assert c.debug_run_id is None


def test_debug_filename_constants_distinct() -> None:
    """All 15 canonical JSON filenames are distinct and end with .json."""
    from proto3 import debug

    fnames = [
        debug.INPUT_FILENAME,
        debug.RUN_CONFIG_FILENAME,
        debug.PROGRAM_INSTANCE_FILENAME,
        debug.REGIONS_FILENAME,
        debug.ATOMS_FILENAME,
        debug.GRAPHS_FILENAME,
        debug.SPINE_CANDIDATES_FILENAME,
        debug.SEED_CANDIDATES_FILENAME,
        debug.GROWTH_STEPS_FILENAME,
        debug.PRE_REPAIR_VALIDATION_FILENAME,
        debug.REPAIR_OPERATIONS_FILENAME,
        debug.POST_REPAIR_VALIDATION_FILENAME,
        debug.FAILURE_RECORDS_FILENAME,
        debug.NO_GOOD_RECORDS_FILENAME,
        debug.FINAL_LAYOUT_FILENAME,
    ]
    assert len(fnames) == 15
    assert len(set(fnames)) == 15
    assert all(f.endswith(".json") for f in fnames)


def test_run_folder_and_stage_svg_filename() -> None:
    """Folder + SVG filename helpers (Pipeline §12.2)."""
    from proto3.debug import run_folder, stage_svg_filename

    assert run_folder("r42") == Path("outputs/debug_runs/r42")
    assert run_folder("r42", base=Path("/tmp/dbg")) == Path("/tmp/dbg/r42")
    assert stage_svg_filename(8, "spine") == "stage_08_spine.svg"
    assert stage_svg_filename(13, "final") == "stage_13_final.svg"


def test_assert_target_consistent_passes_when_equal() -> None:
    """S02-D14: matching RunConfig and BuildingInput target_type is the happy path."""
    from proto3.config import RunConfig, assert_target_consistent
    from proto3.schema import BuildingInput

    rc = RunConfig(target_type="apartment")
    bi = BuildingInput(target_type="apartment")
    assert_target_consistent(rc, bi)  # no raise


def test_assert_target_consistent_raises_on_mismatch() -> None:
    """S02-D14: mismatch must raise — silent fallthrough is the bug being fixed."""
    import pytest

    from proto3.config import RunConfig, assert_target_consistent
    from proto3.schema import BuildingInput

    rc = RunConfig(target_type="apartment")
    bi = BuildingInput(target_type="hotel")
    with pytest.raises(ValueError) as exc:
        assert_target_consistent(rc, bi)
    assert "apartment" in str(exc.value) and "hotel" in str(exc.value)


def test_layout_candidate_unified_output_fields_defaults() -> None:
    """D018: LayoutCandidate carries unified fields with empty/None defaults.

    `valid=False` candidates need failure_records / debug_artifact_refs;
    `valid=True` may legitimately leave them empty. Defaults must accommodate
    both without forcing Optional handling.
    """
    from proto3.schema import LayoutCandidate

    lc = LayoutCandidate()
    assert lc.valid is False
    assert lc.validation_result is None
    assert lc.failure_records == []
    assert lc.debug_artifact_refs == {}
    assert lc.provenance == {}
    assert lc.output_artifacts == {}
