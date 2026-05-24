"""Tests for the package root import boundary."""

from __future__ import annotations

import subprocess
import sys
import textwrap


def test_package_root_import_stays_public_facade_only():
    code = textwrap.dedent(
        """
        import sys
        import celllayout_tf
        import celllayout_tf.api as api

        expected = {
            "ShapeInput",
            "ShapePart",
            "part_theta",
            "DimensionPolicy",
            "Role",
            "RoomSpec",
            "LayoutFixture",
            "GrownRoom",
            "GrowthResult",
            "CorridoredLayout",
            "region_partition_growth",
            "carve_corridors",
        }

        assert set(celllayout_tf.__all__) == expected
        assert set(api.__all__) == expected

        for name in expected:
            assert getattr(celllayout_tf, name) is getattr(api, name)

        for internal in (
            "Atom",
            "AtomEdge",
            "AtomGraph",
            "Region",
            "RegionEdge",
            "RegionGraph",
            "atomize",
            "build_atom_graph",
            "regionize",
            "build_region_graph",
            "make_cases",
            "selected_cases",
            "save_input_figure",
        ):
            assert internal not in celllayout_tf.__all__

        assert "matplotlib" not in sys.modules
        """
    )
    subprocess.run([sys.executable, "-c", code], check=True)
