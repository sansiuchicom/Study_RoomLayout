"""Stage 00 — input load + normalization (S04-D4, S04-D13).

Step 06 (DoD-9): the `adapter is None` fallback is the **only** site that
uses `DEFAULT_APARTMENT_RULES_PATH` implicitly. All other call sites are
expected to construct adapters with an explicit rules_path (S06-D5).
"""
from __future__ import annotations

from pathlib import Path

from proto3.config import RunConfig, assert_target_consistent
from proto3.schema.input import BuildingInput
from proto3.target import DEFAULT_APARTMENT_RULES_PATH, ApartmentAdapter, TargetAdapter


_ADAPTERS: dict[str, TargetAdapter] = {
    "apartment": ApartmentAdapter(DEFAULT_APARTMENT_RULES_PATH),
}


def _resolve_adapter(target_type: str) -> TargetAdapter:
    if target_type not in _ADAPTERS:
        raise ValueError(
            f"no TargetAdapter registered for target_type={target_type!r} "
            f"(registered: {sorted(_ADAPTERS)})"
        )
    return _ADAPTERS[target_type]


def run(
    path: Path,
    *,
    run_config: RunConfig | None = None,
    adapter: TargetAdapter | None = None,
) -> BuildingInput:
    """Load and normalize a fixture into a BuildingInput.

    Adapter resolution: explicit `adapter` wins; else inferred from
    `run_config.target_type`; else defaults to ApartmentAdapter.

    If `run_config` is given, target_type consistency between RunConfig
    and BuildingInput is asserted (S02-D14).
    """
    if adapter is None:
        target_type = run_config.target_type if run_config is not None else "apartment"
        adapter = _resolve_adapter(target_type)
    building = adapter.load_fixture(Path(path))
    if run_config is not None:
        assert_target_consistent(run_config, building)
    return building
