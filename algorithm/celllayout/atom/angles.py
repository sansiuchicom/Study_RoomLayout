"""Compatibility helper for older pipeline imports."""
import numpy as np


def angle_diff(a, b):
    """Difference between two orientations in the [0, pi/2) domain."""
    d = abs(a - b) % (np.pi / 2)
    return min(d, np.pi / 2 - d)
