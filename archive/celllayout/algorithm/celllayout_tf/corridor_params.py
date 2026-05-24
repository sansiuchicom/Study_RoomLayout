"""Routing parameters for corridor carving."""

from __future__ import annotations


# Common room-size scaling used by both Stage 1 base routing and Stage 2
# shortcut routing. The sandbox spec used cell-count units; these convert that
# intent to room-area-scaled costs.
CORRIDOR_SIZE_REF = 20.0
CORRIDOR_SIZE_FLOOR = 4.0
CORRIDOR_MAX_RETRY = 30


# Stage 1: hub-radial base corridor routing.
STAGE1_ENDPOINT_COST = 0.01
STAGE1_FREE_COST = 0.01
STAGE1_BOUNDARY_BASE = 1.0
STAGE1_INTERIOR_BASE = 8.0


# Stage 2: detour shortcut routing.
STAGE2_ENDPOINT_COST = 0.01
STAGE2_FREE_COST = 0.01
STAGE2_SRC_TGT_AVOID = 5.0
STAGE2_BOUNDARY_BASE = 1.0
STAGE2_INTERIOR_BASE = 8.0
STAGE2_MAX_OUTER_ITER = 30


# Sentinel for hub collapse in Stage 2 BFS hop counting.
HUB_SUPERNODE = -1
