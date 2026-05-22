"""Tests for the package root import boundary."""

from __future__ import annotations

import subprocess
import sys
import textwrap


def test_package_root_import_stays_algorithm_core_only():
    code = textwrap.dedent(
        """
        import sys
        import celllayout_tf

        assert "matplotlib" not in sys.modules
        assert not hasattr(celllayout_tf, "make_cases")
        assert not hasattr(celllayout_tf, "selected_cases")
        assert not hasattr(celllayout_tf, "save_input_figure")
        """
    )
    subprocess.run([sys.executable, "-c", code], check=True)
