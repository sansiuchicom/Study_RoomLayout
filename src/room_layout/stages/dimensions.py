"""Dataset-friendly modular dimension policy.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.6 + S03-D8.

Ported (near-verbatim — pure math, no schema / shapely dependency) from
Cell ``dimensions.py``. The atom grid should be fine enough for
corridor / access control while avoiding noisy fitted decimals in
generated labels. The policy treats 0.30 m as a target module, keeps
most atom widths on a 0.05 m quantum, and preserves exact interval
length after snapping to the geometry grid.

Internal to the pipeline (S03-D8): not re-exported from
``room_layout`` / ``room_layout.schema``. Consumed by ``atomize`` (uses
``DimensionPolicy`` / ``snap_length`` / ``split_interval``),
``regionize`` / ``region_graph`` (``DimensionPolicy``), and the
dimension-diagnostic viz in 4.11 (``is_quantum_aligned``).
``interval_positions`` is the natural complement to ``split_interval``
(widths → cumulative cut positions); not consumed by a Phase 3–5 stage
yet, kept for module cohesion + its existing regression coverage.
"""

from dataclasses import dataclass
from functools import lru_cache
from math import ceil, floor


@dataclass(frozen=True)
class DimensionPolicy:
    geometry_snap: float = 0.01
    module_quantum: float = 0.05
    target_atom_size: float = 0.30
    min_atom_size: float = 0.20
    max_atom_size: float = 0.40
    non_quantum_penalty: float = 20.0
    count_penalty: float = 12.0

    def __post_init__(self):
        values = (
            self.geometry_snap,
            self.module_quantum,
            self.target_atom_size,
            self.min_atom_size,
            self.max_atom_size,
        )
        if any(v <= 0 for v in values):
            raise ValueError("dimension values must be positive")
        if self.min_atom_size > self.target_atom_size:
            raise ValueError("min_atom_size cannot exceed target_atom_size")
        if self.target_atom_size > self.max_atom_size:
            raise ValueError("target_atom_size cannot exceed max_atom_size")
        _units(self.module_quantum, self.geometry_snap)
        _units(self.target_atom_size, self.geometry_snap)
        _units(self.min_atom_size, self.geometry_snap)
        _units(self.max_atom_size, self.geometry_snap)

    @property
    def quantum_units(self) -> int:
        return _units(self.module_quantum, self.geometry_snap)

    @property
    def target_units(self) -> int:
        return _units(self.target_atom_size, self.geometry_snap)

    @property
    def min_units(self) -> int:
        return _units(self.min_atom_size, self.geometry_snap)

    @property
    def max_units(self) -> int:
        return _units(self.max_atom_size, self.geometry_snap)


def snap_length(value: float, snap: float = 0.01) -> float:
    return round(round(value / snap) * snap, _decimal_places(snap))


def is_quantum_aligned(value: float, policy: DimensionPolicy | None = None) -> bool:
    policy = policy or DimensionPolicy()
    units = _units(value, policy.geometry_snap)
    return units % policy.quantum_units == 0


def split_interval(length: float, policy: DimensionPolicy | None = None) -> list[float]:
    """Split ``length`` into atom widths following ``policy``.

    Widths always sum to ``length`` snapped to ``policy.geometry_snap``.
    When the interval length is compatible with the module quantum, all
    widths are quantum-aligned. Otherwise the optimizer keeps the number
    of non-quantum widths as small as possible while preserving exact
    snapped length.
    """
    policy = policy or DimensionPolicy()
    total_units = _units(length, policy.geometry_snap)
    if total_units <= 0:
        return []
    if total_units <= policy.min_units:
        return [_from_units(total_units, policy.geometry_snap)]

    widths_units = _best_split_units(total_units, policy)
    widths_units = _arrange_widths(widths_units, policy.target_units)
    return [_from_units(w, policy.geometry_snap) for w in widths_units]


def interval_positions(
    start: float,
    widths: list[float],
    policy: DimensionPolicy | None = None,
) -> list[float]:
    policy = policy or DimensionPolicy()
    places = _decimal_places(policy.geometry_snap)
    out = [snap_length(start, policy.geometry_snap)]
    pos = out[0]
    for width in widths:
        pos = round(pos + width, places)
        out.append(snap_length(pos, policy.geometry_snap))
    return out


def _best_split_units(total_units: int, policy: DimensionPolicy) -> list[int]:
    preferred_count = max(1, round(total_units / policy.target_units))
    min_count = max(1, ceil(total_units / policy.max_units))
    max_count = max(1, floor(total_units / policy.min_units))
    if min_count > max_count:
        return [total_units]

    best = None
    for count in range(min_count, max_count + 1):
        candidate = _best_widths_for_count(
            total_units,
            count,
            policy.min_units,
            policy.max_units,
            policy.target_units,
            policy.quantum_units,
            policy.non_quantum_penalty,
        )
        if candidate is None:
            continue
        score, widths = candidate
        score += abs(count - preferred_count) * policy.count_penalty
        key = (score, abs(count - preferred_count), count, widths)
        if best is None or key < best[0]:
            best = (key, widths)

    if best is None:
        return [total_units]
    return list(best[1])


def _best_widths_for_count(
    total: int,
    count: int,
    min_width: int,
    max_width: int,
    target: int,
    quantum: int,
    non_quantum_penalty: float,
):
    result = _best_widths_cached(
        total,
        count,
        min_width,
        max_width,
        target,
        quantum,
        non_quantum_penalty,
    )
    if result is None:
        return None
    score, widths = result
    return score, list(widths)


@lru_cache(maxsize=4096)
def _best_widths_cached(
    total: int,
    count: int,
    min_width: int,
    max_width: int,
    target: int,
    quantum: int,
    non_quantum_penalty: float,
):
    if count == 0:
        return (0.0, ()) if total == 0 else None
    if total < count * min_width or total > count * max_width:
        return None

    best = None
    remaining_count = count - 1
    lo = max(min_width, total - remaining_count * max_width)
    hi = min(max_width, total - remaining_count * min_width)
    for width in range(lo, hi + 1):
        rest = _best_widths_cached(
            total - width,
            remaining_count,
            min_width,
            max_width,
            target,
            quantum,
            non_quantum_penalty,
        )
        if rest is None:
            continue
        rest_score, rest_widths = rest
        score = _width_score(width, target, quantum, non_quantum_penalty)
        candidate = (score + rest_score, (width, *rest_widths))
        if best is None or candidate < best:
            best = candidate
    return best


def _width_score(
    width: int,
    target: int,
    quantum: int,
    non_quantum_penalty: float,
) -> float:
    score = float((width - target) ** 2)
    if width % quantum != 0:
        score += non_quantum_penalty
    if width < target:
        score += 0.1
    return score


def _arrange_widths(widths: list[int], target: int) -> list[int]:
    """Move adjustment widths toward interval edges for cleaner interiors."""
    target_widths = [w for w in widths if w == target]
    deviations = [w for w in widths if w != target]
    deviations.sort(key=lambda w: (-abs(w - target), w))

    left: list[int] = []
    right: list[int] = []
    for idx, width in enumerate(deviations):
        if idx % 2 == 0:
            left.append(width)
        else:
            right.insert(0, width)
    return left + target_widths + right


def _units(value: float, snap: float) -> int:
    raw = value / snap
    rounded = round(raw)
    if abs(raw - rounded) > 1e-7:
        raise ValueError(f"{value!r} is not aligned to snap {snap!r}")
    return int(rounded)


def _from_units(units: int, snap: float) -> float:
    return round(units * snap, _decimal_places(snap))


def _decimal_places(value: float) -> int:
    text = f"{value:.10f}".rstrip("0")
    return len(text.split(".")[1]) if "." in text else 0
