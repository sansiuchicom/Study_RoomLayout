"""Shared fixtures for expensive full-pipeline layout solves."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import pytest

from celllayout_tf.atomize import atomize
from celllayout_tf.cases import make_cases
from celllayout_tf.corridor import CorridoredLayout, carve_corridors
from celllayout_tf.growth_partition import region_partition_growth
from celllayout_tf.layout_fixtures import make_fixtures
from celllayout_tf.region_graph import build_region_graph
from celllayout_tf.regionize import regionize
from celllayout_tf.room_growth import GrowthResult, LayoutFixture
from celllayout_tf.schema import ShapeInput


@dataclass
class CaseFixture:
    shape: ShapeInput
    fixture: LayoutFixture


@dataclass
class GrowthCase:
    shape: ShapeInput
    fixture: LayoutFixture
    growth: GrowthResult


@dataclass
class CorridorCase:
    shape: ShapeInput
    fixture: LayoutFixture
    growth: GrowthResult
    layout: CorridoredLayout
    region_adj: dict[int, set[int]]
    all_region_ids: set[int]


def _case_fixture_pairs() -> tuple[CaseFixture, ...]:
    cases = {c.name: c for c in make_cases()}
    return tuple(CaseFixture(cases[f.case_name], f) for f in make_fixtures())


def _region_adj_for(shape: ShapeInput) -> tuple[dict[int, set[int]], set[int]]:
    atoms = atomize(shape)
    regions = regionize(shape, atoms=atoms)
    rg = build_region_graph(shape, atoms=atoms, regions=regions)
    adj: dict[int, set[int]] = defaultdict(set)
    for e in rg.edges:
        adj[e.region_a].add(e.region_b)
        adj[e.region_b].add(e.region_a)
    for r in regions:
        adj.setdefault(r.region_id, set())
    return dict(adj), {r.region_id for r in regions}


@pytest.fixture(scope="session")
def case_fixtures() -> tuple[CaseFixture, ...]:
    return _case_fixture_pairs()


@pytest.fixture(scope="session")
def growth_cases(case_fixtures: tuple[CaseFixture, ...]) -> tuple[GrowthCase, ...]:
    return tuple(
        GrowthCase(c.shape, c.fixture, region_partition_growth(c.shape, c.fixture))
        for c in case_fixtures
    )


@pytest.fixture(scope="session")
def corridor_cases(growth_cases: tuple[GrowthCase, ...]) -> tuple[CorridorCase, ...]:
    cases: list[CorridorCase] = []
    for c in growth_cases:
        layout = carve_corridors(c.shape, c.growth)
        region_adj, all_region_ids = _region_adj_for(c.shape)
        cases.append(
            CorridorCase(
                shape=c.shape,
                fixture=c.fixture,
                growth=c.growth,
                layout=layout,
                region_adj=region_adj,
                all_region_ids=all_region_ids,
            )
        )
    return tuple(cases)
