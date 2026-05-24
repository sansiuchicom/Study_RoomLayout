# Portable Core Checklist

This checklist defines the files to copy when moving RoomLayoutCell into another
workspace as an integration module. The goal is to preserve the public API while
leaving the local testfield, showcase cases, and matplotlib diagnostics behind.

## Public API Contract

External code should import only from `celllayout_tf` or `celllayout_tf.api`:

```python
from celllayout_tf import (
    ShapeInput, ShapePart, DimensionPolicy,
    RoomSpec, LayoutFixture, GrowthResult, CorridoredLayout,
    region_partition_growth, carve_corridors,
)
```

The atom/cell lattice, region graph, seed helpers, and corridor stages remain
internal implementation modules. They are copied because the public entry points
depend on them, but callers should not import them directly.

## Files To Copy

Copy the package directory with exactly these core files:

<!-- portable-core-files:start -->
```text
celllayout_tf/__init__.py
celllayout_tf/api.py
celllayout_tf/schema.py
celllayout_tf/dimensions.py
celllayout_tf/geometry.py
celllayout_tf/territory.py
celllayout_tf/atomize.py
celllayout_tf/atom_graph.py
celllayout_tf/regionize.py
celllayout_tf/region_graph.py
celllayout_tf/seed_placement.py
celllayout_tf/shape_gate.py
celllayout_tf/growth_cells.py
celllayout_tf/growth_seed.py
celllayout_tf/growth_absorb.py
celllayout_tf/growth_partition.py
celllayout_tf/room_growth.py
celllayout_tf/corridor_params.py
celllayout_tf/corridor_index.py
celllayout_tf/corridor_path.py
celllayout_tf/corridor_stage1.py
celllayout_tf/corridor_stage2.py
celllayout_tf/corridor.py
```
<!-- portable-core-files:end -->

## Files To Leave Behind

These are useful in this repository but should not be required by an integration
copy:

```text
celllayout_tf/cases.py              # synthetic showcase footprint catalog
celllayout_tf/layout_fixtures.py    # room programs for showcase cases
celllayout_tf/viz.py                # matplotlib diagnostics
demos/                              # local rendering CLI
tests/conftest.py                   # fixture cache around showcase cases
```

Most current tests are testfield/regression tests and depend on `cases.py` or
`layout_fixtures.py`. For a minimal integration smoke suite, copy or recreate:

```text
tests/test_package_import.py
tests/test_public_api.py
```

## Runtime Dependencies

Portable runtime dependencies:

```text
Python 3.10+
Shapely 2.x
```

`matplotlib` is diagnostic-only and should not be imported by the package root.
`pytest` is needed only for tests.

## Copy Checklist

1. Copy the files listed in **Files To Copy** into the target workspace.
2. Keep the package name `celllayout_tf`, or update all relative package imports
   consistently before running tests.
3. Do not copy `cases.py`, `layout_fixtures.py`, `viz.py`, or `demos/` unless the
   target workspace explicitly wants the local showcase/testfield tools.
4. Install Shapely 2.x in the target environment.
5. Provide target-specific `ShapeInput` and `LayoutFixture` data. The public API
   expects those data objects and does not depend on the showcase catalog.
6. Run the smoke checks below in the target workspace.

## Validation Commands

From the source repository before copying:

```bash
python3 -m pytest -q tests/test_package_import.py tests/test_public_api.py tests/test_portable_manifest.py
```

After copying into the target workspace, run at least:

```bash
python3 - <<'PY'
import celllayout_tf
print(celllayout_tf.__all__)
PY

python3 -m pytest -q tests/test_package_import.py tests/test_public_api.py
```

If the target workspace does not carry this repository's tests, recreate the
public API smoke from `tests/test_public_api.py` with one target-specific
`ShapeInput` and `LayoutFixture`.
