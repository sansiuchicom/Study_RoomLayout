"""Compatibility wrapper for the moved v11/v12 comparison experiment."""
from experiments.compare_v11_v12 import compare, configure_fonts, visualize


if __name__ == "__main__":
    configure_fonts()
    visualize(compare())
