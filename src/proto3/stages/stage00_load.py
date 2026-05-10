"""Stage 00 — input load + normalization (S04-D4, S04-D13, S06-D5).

The `_DEFAULT_ADAPTERS` dict below is the **only** site in proto3 that
implicitly uses a default rules path (S06-D5 fail-loud exception, DoD-9).
Every other call site is expected to construct adapters explicitly:
`TargetAdapter(rules_path=...)`.

Adding a new typology that shares all algorithms with apartment requires
**only**: (a) a new JSON in `src/proto3/data/target_rules/`, and (b) one
line below registering its default path. No new adapter class is needed —
typology-specific algorithm variants belong to the strategy registry (L2)
documented in `src/proto3/data/target_rules/README.md`.
"""
from __future__ import annotations

from pathlib import Path

from proto3.config import RunConfig, assert_target_consistent
from proto3.schema.input import BuildingInput
from proto3.target import DEFAULT_APARTMENT_RULES_PATH, TargetAdapter


# typology -> default-path adapter instance. Eager construction at import
# time = JSON validity is fail-fast; rule-file errors surface during
# `import proto3.stages.stage00_load`, not during the first real run.
_DEFAULT_ADAPTERS: dict[str, TargetAdapter] = {
    "apartment": TargetAdapter(DEFAULT_APARTMENT_RULES_PATH),
}


def _resolve_adapter(target_type: str) -> TargetAdapter:
    if target_type not in _DEFAULT_ADAPTERS:
        raise ValueError(
            f"no default TargetAdapter registered for target_type={target_type!r} "
            f"(registered: {sorted(_DEFAULT_ADAPTERS)}); "
            f"pass an explicit adapter=TargetAdapter(rules_path=...)"
        )
    return _DEFAULT_ADAPTERS[target_type]


def run(
    path: Path,
    *,
    run_config: RunConfig | None = None,
    adapter: TargetAdapter | None = None,
) -> BuildingInput:
    """Load and normalize a fixture into a BuildingInput.

    Adapter resolution: explicit `adapter` wins; else inferred from
    `run_config.target_type`; else defaults to apartment.

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
