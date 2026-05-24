"""Smoke tests for the public integration API."""

from __future__ import annotations

import celllayout_tf as tf


def test_public_api_runs_growth_and_corridor_without_internal_imports():
    shape = tf.ShapeInput(
        "public_api_rect",
        (tf.ShapePart(exterior=((0, 0), (9, 0), (9, 6), (0, 6))),),
    )
    fixture = tf.LayoutFixture(
        case_index=0,
        case_name="public_api_rect",
        footprint_area_m2=54.0,
        rooms=(
            tf.RoomSpec("living", "public", None),
            tf.RoomSpec("bed", "private", None),
            tf.RoomSpec("bath", "wet", None),
        ),
        role_min_areas={"public": 6.0, "private": 6.0, "wet": 3.0},
        role_aspect_ranges={
            "public": (1.0, 4.0),
            "private": (1.0, 4.0),
            "wet": (1.0, 4.0),
        },
    )

    growth = tf.region_partition_growth(shape, fixture)
    layout = tf.carve_corridors(shape, growth)

    assert len(growth.rooms) == 3
    assert all(room.region_ids for room in growth.rooms)
    assert layout.fixture is fixture
    assert len(layout.rooms) == 3
    assert layout.diagnostics["phase"] == "w4-stage1+stage2+cleanup"
