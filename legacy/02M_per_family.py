"""Compatibility wrapper for the moved atom-cell per-family implementation."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from roomlayout_cell.atom.per_family import *  # noqa: F401,F403
from roomlayout_cell.atom.per_family import main


if __name__ == "__main__":
    main()
