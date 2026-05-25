"""Smoke tests for the Step 01 scaffold.

The package is intentionally empty at Step 01 — these tests verify
imports succeed and the package version is exposed. Real behavior
tests arrive Step 02 onward as the schema and stages land.
"""

import room_layout
import room_layout.viz


def test_top_level_package_imports():
    """The top-level package must be importable."""
    assert hasattr(room_layout, "__version__")


def test_package_version_matches_pyproject():
    """The package version exposed via ``__version__`` is the v1 scaffold value."""
    assert room_layout.__version__ == "0.1.0"


def test_viz_subpackage_imports_without_matplotlib():
    """``room_layout.viz`` must import even when the ``[viz]`` extra is absent.

    Step 01 ships ``viz`` as a placeholder package with no runtime imports
    of matplotlib. If a future change makes ``import room_layout.viz``
    require matplotlib at import time, this test catches the regression.
    """
    assert room_layout.viz is not None
