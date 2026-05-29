"""Corridor carving visualization — ``save_corridor_figure``.

Plan reference: ``004_Step04_AlgorithmCore_Plan.md`` §4.13 + S04-D4.

Dev-bridge renderer for ``carve_corridors`` output (``CorridoredLayout``):
post-carve rooms colored by room, base corridor + shortcut corridor in distinct
overlay colors, leftover regions hatched. When ``region_graph`` is supplied, a
connectivity overlay shows how the corridor network hangs together — solid
links among base/shortcut/hub regions, dotted links where a shortcut joins the
network *through a room entrance* (a detour shortcut is a new cut between two
corridor-adjacent rooms, so it attaches at its endpoints, not along its body).
Takes computed outputs as parameters (decoupled from the algorithm per Plan §6).
"""

from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.ops import unary_union

from room_layout.schema import FloorShape
from room_layout.stages._helpers import to_shapely
from room_layout.stages.corridor import CorridoredLayout
from room_layout.stages.region_graph import RegionGraph
from room_layout.stages.regionize import Region
from room_layout.viz._helpers import _draw_footprint_outline, _finish_axis, configure_fonts

_BASE_COLOR = "#555555"
_SHORTCUT_COLOR = "#d62728"
_NET_COLOR = "#1f77b4"


def save_corridor_figure(
    floor: FloorShape,
    regions: tuple[Region, ...],
    corridored: CorridoredLayout,
    path,
    *,
    region_graph: RegionGraph | None = None,
    title: str | None = None,
) -> Path:
    """Render carved layout: rooms by color, base + shortcut corridor, leftovers,
    and (if ``region_graph`` given) the corridor-network connectivity overlay.
    """
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    region_poly = {r.region_id: to_shapely(r.shape) for r in regions}
    room_of: dict[int, int] = {}
    for room_idx, gr in enumerate(corridored.rooms):
        for rid in gr.region_ids:
            room_of[rid] = room_idx
    base = set(corridored.base_corridor_region_ids)
    shortcut = set(corridored.shortcut_corridor_region_ids)
    leftover = set(corridored.leftover_region_ids)
    hub_idx = corridored.fixture.hub_room_index
    hub = set(corridored.rooms[hub_idx].region_ids) if hub_idx is not None else set()

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)
    cmap = plt.get_cmap("tab20")

    for rid, poly in region_poly.items():
        xs, ys = poly.exterior.xy
        if rid in base:
            ax.fill(xs, ys, facecolor=_BASE_COLOR, edgecolor="#222222", linewidth=0.6, zorder=4)
        elif rid in shortcut:
            ax.fill(xs, ys, facecolor=_SHORTCUT_COLOR, edgecolor="#222222", linewidth=0.6, zorder=4)
        elif rid in leftover:
            ax.fill(
                xs,
                ys,
                facecolor="#dddddd",
                edgecolor="#999999",
                linewidth=0.6,
                hatch="////",
                zorder=2,
            )
        elif rid in room_of:
            ax.fill(
                xs,
                ys,
                facecolor=cmap(room_of[rid] % 20),
                edgecolor="#222222",
                alpha=0.6,
                linewidth=0.8,
                zorder=3,
            )
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.fill(hx, hy, facecolor="#444444", edgecolor="#111111", linewidth=0.7, zorder=5)

    # Connectivity overlay: shows the corridor network is actually connected —
    # in particular that each shortcut attaches to base/hub through a room
    # entrance at its endpoints (dotted), even though its carved body (red) only
    # borders rooms.
    if region_graph is not None:
        adj: dict[int, set[int]] = defaultdict(set)
        for e in region_graph.edges:
            adj[e.region_a].add(e.region_b)
            adj[e.region_b].add(e.region_a)
        cen = {rid: region_poly[rid].centroid for rid in region_poly}
        network = base | shortcut | hub

        seen: set[tuple[int, int]] = set()
        for u in network:
            for v in adj[u] & network:
                key = (min(u, v), max(u, v))
                if key in seen:
                    continue
                seen.add(key)
                ax.plot(
                    [cen[u].x, cen[v].x],
                    [cen[u].y, cen[v].y],
                    color=_NET_COLOR,
                    lw=1.3,
                    alpha=0.9,
                    zorder=8,
                )
        # shortcut → entrance room → network (the via-room bridge), dotted
        for s in shortcut:
            for r in adj[s]:
                if r in network or r not in room_of:
                    continue
                bridges = adj[r] & network
                if not bridges:
                    continue
                ax.plot(
                    [cen[s].x, cen[r].x],
                    [cen[s].y, cen[r].y],
                    color=_NET_COLOR,
                    lw=1.0,
                    ls=":",
                    alpha=0.85,
                    zorder=8,
                )
                for w in bridges:
                    ax.plot(
                        [cen[r].x, cen[w].x],
                        [cen[r].y, cen[w].y],
                        color=_NET_COLOR,
                        lw=1.0,
                        ls=":",
                        alpha=0.85,
                        zorder=8,
                    )
        for rid in network:
            ax.plot(cen[rid].x, cen[rid].y, ".", color=_NET_COLOR, markersize=3.5, zorder=9)

    for gr in corridored.rooms:
        if not gr.region_ids:
            continue
        union = unary_union([region_poly[rid] for rid in gr.region_ids])
        rp = union.representative_point()
        ax.text(
            rp.x,
            rp.y,
            f"{gr.name}\n{gr.role}\n{gr.area_m2:.1f}m²",
            ha="center",
            va="center",
            fontsize=7,
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": "white",
                "edgecolor": "#555555",
                "linewidth": 0.5,
                "alpha": 0.92,
            },
            zorder=11,
        )

    _draw_footprint_outline(ax, floor)
    _finish_axis(ax, floor)
    legend = [
        Patch(facecolor=_BASE_COLOR, label=f"base ({len(base)})"),
        Patch(facecolor=_SHORTCUT_COLOR, label=f"shortcut ({len(shortcut)})"),
    ]
    if leftover:
        legend.append(Patch(facecolor="#dddddd", hatch="////", label=f"leftover ({len(leftover)})"))
    if region_graph is not None:
        legend.append(
            Line2D([0], [0], color=_NET_COLOR, lw=1.3, label="corridor network (… = via room)")
        )
    ax.legend(handles=legend, loc="upper right", fontsize=8, framealpha=0.9)
    ax.set_title(title or f"{len(corridored.rooms)} rooms + corridor", fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path
