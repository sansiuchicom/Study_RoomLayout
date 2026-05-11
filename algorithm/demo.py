"""Compatibility entry point for the zoning showcase demo.

The implementation lives in `demos/zoning_demo.py` so future experiment demos
can sit next to it without overloading this file.
"""
from demos.zoning_demo import main, configure_fonts


if __name__ == '__main__':
    import sys

    configure_fonts()
    main(sys.argv[1:])
