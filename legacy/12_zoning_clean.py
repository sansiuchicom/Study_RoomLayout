"""Compatibility wrapper for the moved Pipeline 12 implementation."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from roomlayout_cell.zoning.pipeline12 import *  # noqa: F401,F403
