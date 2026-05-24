"""Deterministic cut planning for the atomic subdivision testfield."""

from __future__ import annotations

from dataclasses import dataclass, field

import shapely.geometry as sg
from shapely.ops import split

from .geometry import polygon_parts


DEFAULT_AREA_PER_ZONE = 10.0
MIN_ZONE_AREA = 3.0
MIN_BALANCE = 0.12
CUT_FRACTIONS = (0.5, 0.4, 0.6, 1 / 3, 2 / 3, 0.25, 0.75)


@dataclass(frozen=True)
class CutRecord:
    """A planned cut line and its provenance."""

    line: object
    label: str
    depth: int = 0
    family_id: int | None = None


@dataclass
class CandidateZone:
    """A provisional zone used only for face assignment."""

    zone_id: int
    polygon: object
    cut_history: list[str] = field(default_factory=list)
    family_id: int | None = None
    family_theta: float = 0.0


@dataclass
class PlanningResult:
    """Planner output consumed by subdivision and assignment stages."""

    candidates: list[CandidateZone]
    cuts: list[CutRecord] = field(default_factory=list)
    requested_k: int = 1

    @property
    def achieved_k(self) -> int:
        return len(self.candidates)


@dataclass(frozen=True)
class _CutChoice:
    line: object
    pieces: list
    label: str
    balance: float
    max_aspect: float


def plan_initial_zones(
    footprint,
    *,
    k: int | None = None,
    area_per_zone: float = DEFAULT_AREA_PER_ZONE,
    min_zone_area: float = MIN_ZONE_AREA,
) -> PlanningResult:
    """Plan provisional zones with recursive balanced axis cuts.

    Phase 3 deliberately starts with a conservative world-axis planner. It
    returns provisional candidate polygons and the cut lines needed by the
    atomic subdivision stage; final zone geometry is still rebuilt from faces.
    """
    if k is None:
        k = max(1, round(footprint.area / area_per_zone))
    k = max(1, int(k))

    cuts: list[CutRecord] = []
    candidates: list[CandidateZone] = []
    next_zone_id = [0]
    _partition(
        footprint,
        k,
        depth=0,
        cuts=cuts,
        candidates=candidates,
        next_zone_id=next_zone_id,
        cut_history=[],
        min_zone_area=min_zone_area,
    )
    return PlanningResult(candidates=candidates, cuts=cuts, requested_k=k)


def _partition(
    poly,
    k: int,
    *,
    depth: int,
    cuts: list[CutRecord],
    candidates: list[CandidateZone],
    next_zone_id: list[int],
    cut_history: list[str],
    min_zone_area: float,
):
    if k <= 1 or poly.area < min_zone_area * 2:
        _append_candidate(poly, candidates, next_zone_id, cut_history)
        return

    choice = _select_cut(poly, k, min_zone_area)
    if choice is None:
        _append_candidate(poly, candidates, next_zone_id, cut_history)
        return

    cuts.append(CutRecord(line=choice.line, label=choice.label, depth=depth))
    allocations = _allocate_k(choice.pieces, k)
    for piece, child_k in zip(choice.pieces, allocations):
        _partition(
            piece,
            child_k,
            depth=depth + 1,
            cuts=cuts,
            candidates=candidates,
            next_zone_id=next_zone_id,
            cut_history=[*cut_history, choice.label],
            min_zone_area=min_zone_area,
        )


def _append_candidate(poly, candidates, next_zone_id, cut_history):
    zid = next_zone_id[0]
    next_zone_id[0] += 1
    candidates.append(
        CandidateZone(
            zone_id=zid,
            polygon=poly,
            cut_history=list(cut_history),
        )
    )


def _select_cut(poly, k: int, min_zone_area: float) -> _CutChoice | None:
    choices = []
    axis_preference = _axis_preference(poly)
    for axis, fraction, line in _candidate_axis_lines(poly):
        pieces = _split_polygons(poly, line)
        if len(pieces) < 2 or len(pieces) > k:
            continue
        if min(p.area for p in pieces) < min_zone_area:
            continue
        bal = _balance(pieces)
        if bal < MIN_BALANCE:
            continue
        choices.append(
            _CutChoice(
                line=line,
                pieces=pieces,
                label=f"axis_{axis}_{fraction:.3f}",
                balance=bal,
                max_aspect=max(_piece_aspect(p) for p in pieces),
            )
        )
    if not choices:
        return None
    choices.sort(
        key=lambda c: (
            c.label.split("_")[1] != axis_preference,
            -round(c.balance, 6),
            c.max_aspect,
            c.label,
        )
    )
    return choices[0]


def _candidate_axis_lines(poly):
    minx, miny, maxx, maxy = poly.bounds
    width = maxx - minx
    height = maxy - miny
    pad = max(width, height, 1.0)
    axes = ("x", "y") if width >= height else ("y", "x")
    for fraction in CUT_FRACTIONS:
        x = minx + width * fraction
        y = miny + height * fraction
        for axis in axes:
            if axis == "x":
                yield axis, fraction, sg.LineString([(x, miny - pad), (x, maxy + pad)])
            else:
                yield axis, fraction, sg.LineString([(minx - pad, y), (maxx + pad, y)])


def _split_polygons(poly, line):
    try:
        result = split(poly, line)
    except Exception:
        return []
    pieces = [p for p in polygon_parts(result) if p.area > 1e-9]
    return sorted(pieces, key=lambda p: (-p.area, p.bounds))


def _allocate_k(pieces, k: int) -> list[int]:
    if len(pieces) > k:
        return []
    base = [1] * len(pieces)
    remaining = k - len(pieces)
    if remaining <= 0:
        return base

    total = sum(p.area for p in pieces)
    raw = [remaining * p.area / total for p in pieces]
    floors = [int(v) for v in raw]
    allocations = [b + f for b, f in zip(base, floors)]
    leftovers = remaining - sum(floors)
    order = sorted(
        range(len(pieces)),
        key=lambda i: (-(raw[i] - floors[i]), -pieces[i].area),
    )
    for idx in order[:leftovers]:
        allocations[idx] += 1
    return allocations


def _balance(pieces) -> float:
    areas = [p.area for p in pieces]
    return min(areas) / max(areas)


def _axis_preference(poly) -> str:
    minx, miny, maxx, maxy = poly.bounds
    return "x" if (maxx - minx) >= (maxy - miny) else "y"


def _piece_aspect(poly) -> float:
    try:
        mrr = poly.minimum_rotated_rectangle
        coords = list(mrr.exterior.coords)
        edge_a = sg.Point(coords[0]).distance(sg.Point(coords[1]))
        edge_b = sg.Point(coords[1]).distance(sg.Point(coords[2]))
        return max(edge_a, edge_b) / max(min(edge_a, edge_b), 1e-9)
    except Exception:
        return 999.0
