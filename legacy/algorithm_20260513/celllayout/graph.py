"""Zone adjacency graph utilities for geometry-only layout experiments.

M1 scope: convert `zoning.zone_footprint()` output into a lightweight graph.
The graph is intentionally plain dict/list data so later experiments can reshape
it without migrating a public schema.
"""
from __future__ import annotations

import math

import shapely.geometry as sg
from shapely.ops import snap


DEFAULT_SNAP_TOLERANCE = 1e-6
DEFAULT_MIN_SHARED_LENGTH = 0.05


def _zone_id(zone):
    return int(zone.get('zone_id', 0))


def _centroid_xy(poly):
    c = poly.centroid
    return (float(c.x), float(c.y))


def shared_boundary_geometry(a, b, *, snap_tolerance=DEFAULT_SNAP_TOLERANCE):
    """Return line-like shared-boundary geometry between two zone polygons.

    Rotated / multi-axis splits often leave microscopic floating-point drift:
    two zones visually share a segment, but `boundary ∩ boundary` returns no
    LineString because one side is offset by ~1e-15 or represented as a tiny
    zero-area polygon. We recover those segment-like contacts while still
    rejecting corner-only Point contacts.
    """
    inter = a.boundary.intersection(b.boundary)
    if _linear_length(inter) > 0.0:
        return inter

    if a.distance(b) > snap_tolerance:
        return sg.GeometryCollection()

    snapped_b = a.boundary.intersection(snap(b, a, snap_tolerance).boundary)
    snapped_a = snap(a, b, snap_tolerance).boundary.intersection(b.boundary)
    return snapped_b if _linear_length(snapped_b) >= _linear_length(snapped_a) else snapped_a


def _shared_boundary_length(a, b, *, snap_tolerance=DEFAULT_SNAP_TOLERANCE):
    """Return robust shared-boundary length between two zone polygons."""
    return _linear_length(shared_boundary_geometry(a, b, snap_tolerance=snap_tolerance))


def _linear_length(geom):
    """Length of line-like contact, excluding point-only contacts."""
    if geom.is_empty:
        return 0.0
    if isinstance(geom, (sg.LineString, sg.LinearRing)):
        return float(geom.length)
    if isinstance(geom, sg.MultiLineString):
        return float(sum(g.length for g in geom.geoms))
    if isinstance(geom, sg.GeometryCollection):
        return float(sum(_linear_length(g) for g in geom.geoms))
    return 0.0


def _centroid_distance(a, b):
    ax, ay = _centroid_xy(a)
    bx, by = _centroid_xy(b)
    return float(math.hypot(ax - bx, ay - by))


def build_zone_graph(zones, *, door_boundary_min=0.8,
                     min_shared_length=DEFAULT_MIN_SHARED_LENGTH,
                     snap_tolerance=DEFAULT_SNAP_TOLERANCE):
    """Build an undirected adjacency graph from zone polygons.

    Args:
        zones: list of zone dicts from `zoning.zone_footprint()`.
        door_boundary_min: boundary length threshold for a door-capable-like
            graph edge. This is geometric only, not a domain door rule.
        min_shared_length: contact length below which contacts are ignored.
            The default 5 cm filter removes corner-like slivers and drift noise.
        snap_tolerance: max distance for recovering near-coincident segment
            contacts caused by floating-point drift. Point-only contacts are
            still rejected.

    Returns:
        dict with:
            - `nodes`: list of {zone_id, area, centroid, family_id, theta}
            - `edges`: list of {zone_a, zone_b, shared_boundary_length,
              centroid_distance, door_capable}
            - `adjacency`: {zone_id: [neighbor_zone_id, ...]}
    """
    nodes = []
    adjacency = {_zone_id(z): [] for z in zones}
    edges = []

    for z in zones:
        poly = z['polygon']
        nodes.append({
            'zone_id': _zone_id(z),
            'area': float(poly.area),
            'centroid': _centroid_xy(poly),
            'family_id': z.get('family_id'),
            'theta': z.get('family_theta'),
        })

    for i, za in enumerate(zones):
        pa = za['polygon']
        ida = _zone_id(za)
        for zb in zones[i + 1:]:
            pb = zb['polygon']
            idb = _zone_id(zb)
            shared = _shared_boundary_length(pa, pb, snap_tolerance=snap_tolerance)
            if shared <= min_shared_length:
                continue
            edges.append({
                'zone_a': ida,
                'zone_b': idb,
                'shared_boundary_length': shared,
                'centroid_distance': _centroid_distance(pa, pb),
                'door_capable': shared >= door_boundary_min,
            })
            adjacency[ida].append(idb)
            adjacency[idb].append(ida)

    for neighbors in adjacency.values():
        neighbors.sort()

    return {'nodes': nodes, 'edges': edges, 'adjacency': adjacency}


def graph_stats(zone_graph):
    """Return simple summary metrics for logs and demo titles."""
    nodes = zone_graph['nodes']
    edges = zone_graph['edges']
    degrees = [len(zone_graph['adjacency'][n['zone_id']]) for n in nodes]
    door_edges = [e for e in edges if e['door_capable']]
    components = connected_components(zone_graph)
    return {
        'nodes': len(nodes),
        'edges': len(edges),
        'door_edges': len(door_edges),
        'avg_degree': float(sum(degrees) / len(degrees)) if degrees else 0.0,
        'isolated_nodes': [n['zone_id'] for n, d in zip(nodes, degrees) if d == 0],
        'components': components,
        'component_count': len(components),
    }


def connected_components(zone_graph):
    """Return connected components as sorted zone-id lists."""
    adjacency = zone_graph['adjacency']
    unseen = set(adjacency)
    components = []

    while unseen:
        start = min(unseen)
        stack = [start]
        comp = []
        unseen.remove(start)
        while stack:
            node = stack.pop()
            comp.append(node)
            for neighbor in adjacency[node]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
        components.append(sorted(comp))

    components.sort(key=lambda c: (-len(c), c[0] if c else -1))
    return components
