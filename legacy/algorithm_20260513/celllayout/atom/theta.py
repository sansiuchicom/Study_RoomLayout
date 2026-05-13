"""Compatibility helper for older pipeline imports."""
import numpy as np


def piece_direct_theta(piece, *args, min_straight_length=1.0):
    """Infer a dominant boundary direction, normalized to [0, pi/2)."""
    if args and isinstance(args[-1], (int, float)):
        min_straight_length = args[-1]
    coords = list(piece.exterior.coords)
    angles, weights = [], []
    for i in range(len(coords) - 1):
        dx = coords[i + 1][0] - coords[i][0]
        dy = coords[i + 1][1] - coords[i][1]
        length = np.hypot(dx, dy)
        if length < min_straight_length:
            continue
        angles.append(np.arctan2(dy, dx) % (np.pi / 2))
        weights.append(length)
    if not angles:
        return None
    s = sum(w * np.sin(4 * a) for w, a in zip(weights, angles))
    c = sum(w * np.cos(4 * a) for w, a in zip(weights, angles))
    if np.hypot(s, c) < 0.1 * sum(weights):
        return None
    return (np.arctan2(s, c) / 4) % (np.pi / 2)
