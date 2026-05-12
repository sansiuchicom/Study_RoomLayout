"""Graph facade for the atomic testfield.

Phase 0 delegates to the legacy graph implementation so demos can be wired
without duplicating graph code. A native face-aware graph can replace this later.
"""

from __future__ import annotations

from celllayout.graph import build_zone_graph, connected_components, graph_stats

__all__ = ["build_zone_graph", "connected_components", "graph_stats"]
