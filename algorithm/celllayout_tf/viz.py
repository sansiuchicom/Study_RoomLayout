"""Phase 1/2 diagnostic visualization.

Phase 1 renders a ``ShapeInput`` with each part in a distinct translucent
color so that overlapping parts (e.g. wing protrusions) remain visible.

Phase 2 renders a panel of sample interval splits showing how
``split_interval`` decomposes various lengths under the dimension policy.
"""

from __future__ import annotations

from math import degrees
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import shapely.geometry as sg
from matplotlib import font_manager
from shapely.ops import unary_union

from matplotlib.collections import LineCollection

from .atom_graph import AtomGraph, build_atom_graph
from .atomize import Atom, atomize
from .dimensions import DimensionPolicy, is_quantum_aligned, split_interval
from .geometry import polygon_parts as _polygon_parts, to_shapely as _to_shapely
from .region_graph import build_region_graph
from .regionize import Region, regionize
from .corridor import CorridoredLayout, carve_corridors
from .growth_partition import region_partition_growth
from .room_growth import GrowthResult, LayoutFixture
from .schema import ShapeInput, ShapePart, part_theta
from .seed_placement import auto_place_seeds, territory_of_region
from .territory import Territory, resolve_territories


PART_COLORS = [
    "#9ad0c2",
    "#fdb462",
    "#a6cee3",
    "#fb9a99",
    "#b2df8a",
    "#cab2d6",
    "#fdd087",
    "#b3cde3",
]


ROLE_COLORS: dict[str, str] = {
    "public":  "#ff9a4c",   # warm amber — 거실/공용
    "private": "#5b9bd5",   # blue — 침실
    "wet":     "#70ad47",   # green — 욕실
    "service": "#9467bd",   # purple — 주방·다용도실
}


def configure_fonts():
    font_path = Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
    if font_path.exists():
        font_manager.fontManager.addfont(font_path)
        plt.rcParams["font.family"] = "NanumGothic"
    plt.rcParams["axes.unicode_minus"] = False


def save_input_figure(
    shape: ShapeInput,
    path,
    *,
    title: str | None = None,
    show_vertices: bool = True,
) -> Path:
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    for idx, part in enumerate(shape.parts):
        color = PART_COLORS[idx % len(PART_COLORS)]
        _draw_part(ax, part, color, idx)
        if show_vertices:
            _draw_vertices(ax, part)

    _draw_footprint_outline(ax, shape)
    _finish_axis(ax, shape)
    ax.set_title(title or shape.name, fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def _draw_part(ax, part: ShapePart, color: str, idx: int):
    xs, ys = zip(*part.exterior)
    ax.fill(
        list(xs) + [xs[0]],
        list(ys) + [ys[0]],
        facecolor=color,
        edgecolor="#333333",
        alpha=0.55,
        linewidth=1.0,
    )
    for hole in part.holes:
        hx, hy = zip(*hole)
        ax.fill(
            list(hx) + [hx[0]],
            list(hy) + [hy[0]],
            facecolor="#444444",
            edgecolor="#111111",
            alpha=1.0,
            linewidth=0.8,
        )

    poly = _to_shapely(part)
    if not poly.is_empty:
        rp = poly.representative_point()
        theta_deg = degrees(part_theta(part))
        ax.text(
            rp.x,
            rp.y,
            f"P{idx}\n{theta_deg:.1f}°",
            ha="center",
            va="center",
            fontsize=8,
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": "white",
                "edgecolor": "#777777",
                "linewidth": 0.4,
                "alpha": 0.88,
            },
        )


def _draw_vertices(ax, part: ShapePart):
    for x, y in part.exterior:
        ax.plot(x, y, "o", markersize=3, color="#222222", zorder=10)
    for hole in part.holes:
        for x, y in hole:
            ax.plot(x, y, "o", markersize=2.5, color="#660000", zorder=10)


def _draw_footprint_outline(ax, shape: ShapeInput):
    footprint = unary_union([_to_shapely(p) for p in shape.parts])
    for poly in _polygon_parts(footprint):
        x, y = poly.exterior.xy
        ax.plot(x, y, color="#111111", linewidth=1.5, zorder=20)
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.plot(hx, hy, color="#111111", linewidth=1.2, zorder=20)


def _finish_axis(ax, shape: ShapeInput):
    footprint = unary_union([_to_shapely(p) for p in shape.parts])
    minx, miny, maxx, maxy = footprint.bounds
    pad = max(maxx - minx, maxy - miny, 1.0) * 0.08
    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)
    ax.set_aspect("equal")
    ax.grid(True, color="#dddddd", linewidth=0.5, alpha=0.8)
    ax.tick_params(labelsize=7)


def save_territory_figure(
    shape: ShapeInput,
    path,
    *,
    title: str | None = None,
) -> Path:
    """Render the input parts (faint, dashed) and their resolved territories on top.

    The faint dashed outlines show the original design parts including overlap;
    the filled regions show each part's final territory after overlap resolution.
    """
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    territories = resolve_territories(shape)

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    # 1. faint original parts (design outline, before resolution)
    for idx, part in enumerate(shape.parts):
        color = PART_COLORS[idx % len(PART_COLORS)]
        xs, ys = zip(*part.exterior)
        ax.fill(
            list(xs) + [xs[0]], list(ys) + [ys[0]],
            facecolor=color, edgecolor=color, alpha=0.15, linewidth=0,
        )
        ax.plot(
            list(xs) + [xs[0]], list(ys) + [ys[0]],
            color="#888888", linewidth=0.7, linestyle="--", zorder=2,
        )

    # 2. resolved territories on top — one label per piece
    for t in territories:
        color = PART_COLORS[t.part_id % len(PART_COLORS)]
        multi_piece = len(t.pieces) > 1
        for piece_idx, piece in enumerate(t.pieces):
            xs, ys = zip(*piece.exterior)
            ax.fill(
                list(xs) + [xs[0]], list(ys) + [ys[0]],
                facecolor=color, edgecolor="#333333",
                alpha=0.75, linewidth=1.1, zorder=5,
            )
            for hole in piece.holes:
                hx, hy = zip(*hole)
                ax.fill(
                    list(hx) + [hx[0]], list(hy) + [hy[0]],
                    facecolor="#444444", edgecolor="#111111",
                    alpha=1.0, linewidth=0.8, zorder=6,
                )

            poly = sg.Polygon(piece.exterior, [list(h) for h in piece.holes])
            if poly.is_empty:
                continue
            rp = poly.representative_point()
            label_id = f"P{t.part_id}.{piece_idx}" if multi_piece else f"P{t.part_id}"
            ax.text(
                rp.x, rp.y,
                f"{label_id}\n{degrees(t.theta):.1f}°\n[{t.kind}]",
                ha="center", va="center", fontsize=7,
                bbox={
                    "boxstyle": "round,pad=0.2", "facecolor": "white",
                    "edgecolor": "#777777", "linewidth": 0.4, "alpha": 0.88,
                },
                zorder=10,
            )

    # 3. footprint outline for reference
    _draw_footprint_outline(ax, shape)
    _finish_axis(ax, shape)
    ax.set_title(title or f"{shape.name} (resolved territories)", fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def save_atom_figure(
    shape: ShapeInput,
    path,
    *,
    title: str | None = None,
    policy: DimensionPolicy | None = None,
) -> Path:
    """Render atoms with faint territory background and the footprint outline.

    Atoms are filled with their owning part's color. Sliver atoms are marked
    with a small red dot at their centroid.
    """
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    atoms = atomize(shape, policy)
    territories = resolve_territories(shape)

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    # territory background (faint)
    for t in territories:
        color = PART_COLORS[t.part_id % len(PART_COLORS)]
        for piece in t.pieces:
            xs, ys = zip(*piece.exterior)
            ax.fill(
                list(xs) + [xs[0]], list(ys) + [ys[0]],
                facecolor=color, edgecolor=color,
                alpha=0.18, linewidth=0,
            )

    # atoms
    for atom in atoms:
        color = PART_COLORS[atom.part_id % len(PART_COLORS)]
        xs, ys = zip(*atom.shape.exterior)
        ax.fill(
            list(xs) + [xs[0]], list(ys) + [ys[0]],
            facecolor=color, edgecolor="#555555",
            alpha=0.55, linewidth=0.35, zorder=5,
        )
        if atom.is_feature_sliver:
            cx, cy = atom.centroid
            ax.plot(cx, cy, ".", color="#aa0000", markersize=2.5, zorder=10)

    _draw_footprint_outline(ax, shape)
    _finish_axis(ax, shape)
    n_atoms = len(atoms)
    n_slivers = sum(1 for a in atoms if a.is_feature_sliver)
    ax.set_title(
        title or f"{shape.name}: {n_atoms} atoms ({n_slivers} slivers)",
        fontsize=10,
    )
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def save_region_figure(
    shape: ShapeInput,
    path,
    *,
    title: str | None = None,
    policy: DimensionPolicy | None = None,
    target_area: float = 3.0,
    show_atoms: bool = True,
) -> Path:
    """Render regions as colored areas atop a faint atom grid."""
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    atoms = atomize(shape, policy)
    regions = regionize(shape, atoms=atoms, policy=policy, target_area=target_area)

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    # faint atom backdrop
    if show_atoms:
        for atom in atoms:
            xs, ys = zip(*atom.shape.exterior)
            ax.fill(
                list(xs) + [xs[0]], list(ys) + [ys[0]],
                facecolor="#eeeeee", edgecolor="#bbbbbb",
                alpha=0.6, linewidth=0.25, zorder=1,
            )

    cmap = plt.get_cmap("tab20")
    for r in regions:
        color = cmap(r.region_id % 20)
        poly = sg.Polygon(r.shape.exterior, [list(h) for h in r.shape.holes])
        xs, ys = poly.exterior.xy
        ax.fill(xs, ys, facecolor=color, edgecolor="#222222",
                alpha=0.55, linewidth=1.1, zorder=4)
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.fill(hx, hy, facecolor="#444444", edgecolor="#111111",
                    alpha=1.0, linewidth=0.7, zorder=5)
        rp = poly.representative_point()
        ax.text(
            rp.x, rp.y,
            f"R{r.region_id}\n{poly.area:.1f}m²",
            ha="center", va="center", fontsize=7,
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": "white",
                "edgecolor": "#777777",
                "linewidth": 0.4,
                "alpha": 0.9,
            },
            zorder=10,
        )

    _draw_footprint_outline(ax, shape)
    _finish_axis(ax, shape)
    n_regions = len(regions)
    avg_area = sum(
        sg.Polygon(r.shape.exterior, [list(h) for h in r.shape.holes]).area
        for r in regions
    ) / max(n_regions, 1)
    ax.set_title(
        title or f"{shape.name}: {n_regions} regions (avg {avg_area:.1f}m²)",
        fontsize=10,
    )
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def save_atom_graph_figure(
    shape: ShapeInput,
    path,
    *,
    title: str | None = None,
    policy: DimensionPolicy | None = None,
) -> Path:
    """Render the atom adjacency graph.

    Each edge is drawn as a line segment from atom A's centroid to atom B's
    centroid, so the graph is visible as a network on top of the (faint) atoms.

    Edge colors:
        gray   : same-part interior edge
        blue   : same-part edge whose shared boundary touches the footprint
                 exterior (outer-wall adjacency)
        orange : same-part edge whose shared boundary touches a hole
        red    : cross-part edge (drawn last so it sits on top)
    """
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    graph = build_atom_graph(shape, policy=policy)

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    # atoms as faint background
    for atom in graph.atoms:
        color = PART_COLORS[atom.part_id % len(PART_COLORS)]
        xs, ys = zip(*atom.shape.exterior)
        ax.fill(
            list(xs) + [xs[0]], list(ys) + [ys[0]],
            facecolor=color, edgecolor=color,
            alpha=0.22, linewidth=0.3, zorder=1,
        )

    # centroid-to-centroid edge segments grouped by category
    same_segments: list[tuple] = []
    cross_segments: list[tuple] = []
    exterior_segments: list[tuple] = []
    hole_segments: list[tuple] = []
    for e in graph.edges:
        ca = graph.atoms[e.atom_a].centroid
        cb = graph.atoms[e.atom_b].centroid
        seg = (ca, cb)
        if not e.same_part:
            cross_segments.append(seg)
        elif e.hole_contact:
            hole_segments.append(seg)
        elif e.exterior_contact:
            exterior_segments.append(seg)
        else:
            same_segments.append(seg)

    if same_segments:
        ax.add_collection(LineCollection(
            same_segments, colors="#555555", linewidths=0.45, alpha=0.6, zorder=4,
        ))
    if exterior_segments:
        ax.add_collection(LineCollection(
            exterior_segments, colors="#2266cc", linewidths=0.65, alpha=0.75, zorder=5,
        ))
    if hole_segments:
        ax.add_collection(LineCollection(
            hole_segments, colors="#dd8822", linewidths=0.65, alpha=0.85, zorder=5,
        ))
    if cross_segments:
        ax.add_collection(LineCollection(
            cross_segments, colors="#cc2222", linewidths=1.0, alpha=0.9, zorder=6,
        ))

    # centroid dots
    cx_all = [a.centroid[0] for a in graph.atoms]
    cy_all = [a.centroid[1] for a in graph.atoms]
    ax.plot(cx_all, cy_all, ".", color="#222222", markersize=0.9, zorder=10)

    _draw_footprint_outline(ax, shape)
    _finish_axis(ax, shape)
    n = len(graph.atoms)
    m = len(graph.edges)
    cross = sum(1 for e in graph.edges if not e.same_part)
    ax.set_title(
        title or f"{shape.name}: {n} atoms, {m} edges ({cross} cross-part)",
        fontsize=10,
    )
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def save_region_graph_figure(
    shape: ShapeInput,
    path,
    *,
    title: str | None = None,
    policy: DimensionPolicy | None = None,
    target_area: float = 3.0,
) -> Path:
    """Render the region adjacency graph."""
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    atoms = atomize(shape, policy)
    regions = regionize(shape, atoms=atoms, policy=policy, target_area=target_area)
    graph = build_region_graph(shape, atoms=atoms, regions=regions, policy=policy)

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    cmap = plt.get_cmap("tab20")
    region_centroids: dict[int, tuple[float, float]] = {}
    for region in graph.regions:
        color = cmap(region.region_id % 20)
        poly = sg.Polygon(region.shape.exterior, [list(h) for h in region.shape.holes])
        xs, ys = poly.exterior.xy
        ax.fill(
            xs, ys,
            facecolor=color, edgecolor="#222222",
            alpha=0.38, linewidth=0.9, zorder=2,
        )
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.fill(
                hx, hy,
                facecolor="#444444", edgecolor="#111111",
                alpha=1.0, linewidth=0.7, zorder=3,
            )
        c = poly.centroid
        region_centroids[region.region_id] = (float(c.x), float(c.y))
        ax.text(
            c.x, c.y,
            f"R{region.region_id}",
            ha="center", va="center", fontsize=7,
            bbox={
                "boxstyle": "round,pad=0.16",
                "facecolor": "white",
                "edgecolor": "#777777",
                "linewidth": 0.35,
                "alpha": 0.9,
            },
            zorder=10,
        )

    same_segments: list[tuple] = []
    cross_theta_segments: list[tuple] = []
    exterior_segments: list[tuple] = []
    hole_segments: list[tuple] = []
    for edge in graph.edges:
        seg = (region_centroids[edge.region_a], region_centroids[edge.region_b])
        if edge.hole_contact:
            hole_segments.append(seg)
        elif edge.exterior_contact:
            exterior_segments.append(seg)
        elif not edge.same_theta_group:
            cross_theta_segments.append(seg)
        else:
            same_segments.append(seg)

    if same_segments:
        ax.add_collection(LineCollection(
            same_segments, colors="#444444", linewidths=0.8, alpha=0.65, zorder=5,
        ))
    if exterior_segments:
        ax.add_collection(LineCollection(
            exterior_segments, colors="#2266cc", linewidths=1.0, alpha=0.8, zorder=6,
        ))
    if hole_segments:
        ax.add_collection(LineCollection(
            hole_segments, colors="#dd8822", linewidths=1.0, alpha=0.9, zorder=6,
        ))
    if cross_theta_segments:
        ax.add_collection(LineCollection(
            cross_theta_segments, colors="#cc2222", linewidths=1.2, alpha=0.9, zorder=7,
        ))

    if region_centroids:
        xs = [p[0] for p in region_centroids.values()]
        ys = [p[1] for p in region_centroids.values()]
        ax.plot(xs, ys, ".", color="#111111", markersize=2.2, zorder=11)

    _draw_footprint_outline(ax, shape)
    _finish_axis(ax, shape)
    n = len(graph.regions)
    m = len(graph.edges)
    door_ready = sum(1 for e in graph.edges if e.door_capable_length >= 0.9)
    ax.set_title(
        title or f"{shape.name}: {n} regions, {m} edges ({door_ready} door-ready)",
        fontsize=10,
    )
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def save_dimension_examples_figure(
    path,
    *,
    lengths: tuple[float, ...] = (0.18, 0.55, 1.00, 1.03, 2.05, 3.70, 4.10, 5.50, 8.40, 12.30),
    policy: DimensionPolicy | None = None,
) -> Path:
    """Render a stacked-bar panel of ``split_interval`` outputs for sample lengths."""
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    policy = policy or DimensionPolicy()

    fig, ax = plt.subplots(figsize=(10, max(3.5, len(lengths) * 0.5)), constrained_layout=True)

    target_color = "#9ad0c2"
    deviation_color = "#fdb462"
    non_quantum_color = "#fb9a99"
    edge_color = "#333333"

    for row, length in enumerate(lengths):
        widths = split_interval(length, policy)
        y = len(lengths) - row - 1
        cursor = 0.0
        for w in widths:
            if not is_quantum_aligned(w, policy):
                color = non_quantum_color
            elif abs(w - policy.target_atom_size) < 1e-9:
                color = target_color
            else:
                color = deviation_color
            ax.barh(
                y, w, left=cursor, height=0.7,
                color=color, edgecolor=edge_color, linewidth=0.7,
            )
            ax.text(
                cursor + w / 2, y, f"{w:.2f}",
                ha="center", va="center", fontsize=7, color="#222222",
            )
            cursor += w

        ax.text(
            -0.05, y, f"{length:.2f}m",
            ha="right", va="center", fontsize=8, color="#333333",
            transform=ax.get_yaxis_transform(),
        )
        ax.text(
            cursor + 0.10, y, f"n={len(widths)}, sum={sum(widths):.2f}",
            ha="left", va="center", fontsize=7, color="#555555",
        )

    ax.set_xlim(-0.10, max(lengths) * 1.15)
    ax.set_ylim(-0.5, len(lengths) - 0.5)
    ax.set_yticks([])
    ax.set_xlabel("meters")
    ax.tick_params(labelsize=8)
    ax.grid(True, axis="x", color="#dddddd", linewidth=0.5, alpha=0.8)

    legend = (
        f"target = {policy.target_atom_size}m  (teal)   |   "
        f"quantum-deviation (orange)   |   non-quantum (pink)   |   "
        f"quantum = {policy.module_quantum}m"
    )
    ax.set_title(f"Phase 2: split_interval examples\n{legend}", fontsize=9)

    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


# Phase 8 corridor palette — base = warm yellow, shortcut = magenta.
# Shortcut must be visually distinct from hub (public role = warm amber),
# so we pick a hue far from amber/yellow.
CORRIDOR_BASE_FILL     = "#ffe066"
CORRIDOR_BASE_EDGE     = "#b88a00"
CORRIDOR_SHORTCUT_FILL = "#e34fa3"
CORRIDOR_SHORTCUT_EDGE = "#8a1c5b"


def save_layout_figure(
    shape: ShapeInput,
    fixture: LayoutFixture,
    path,
    *,
    result: GrowthResult | None = None,
    title: str | None = None,
    policy: DimensionPolicy | None = None,
) -> Path:
    """Render the Phase 7 seeded-growth result.

    Layers (bottom-up):

    1. faint region outlines (gray)
    2. unassigned regions (hatched gray) — corridor / access candidates
    3. grown rooms (role-colored, hub edge thicker)
    4. region-id labels on unassigned, room-name labels on grown rooms
    5. seed markers (white dot for normal rooms, star for hub)
    6. footprint outline
    """
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if result is None:
        result = region_partition_growth(shape, fixture, policy=policy)

    atoms = atomize(shape, policy)
    regions = regionize(shape, atoms=atoms, policy=policy)
    region_poly_by_id = {r.region_id: _to_shapely(r.shape) for r in regions}

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    # 1. faint region outlines (background reference)
    for r in regions:
        poly = region_poly_by_id[r.region_id]
        xs, ys = poly.exterior.xy
        ax.plot(xs, ys, color="#cccccc", linewidth=0.4, zorder=1)
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.plot(hx, hy, color="#cccccc", linewidth=0.4, zorder=1)

    # 2. unassigned regions (gray hatched — corridor candidate area)
    for region_id in result.unassigned_region_ids:
        poly = region_poly_by_id[region_id]
        xs, ys = poly.exterior.xy
        ax.fill(
            xs, ys,
            facecolor="#dddddd", edgecolor="#888888",
            alpha=0.55, linewidth=0.6, hatch="///", zorder=2,
        )
        rp = poly.representative_point()
        ax.text(
            rp.x, rp.y, f"R{region_id}",
            ha="center", va="center", fontsize=6, color="#555555",
            zorder=10,
        )

    # 3. grown rooms (colored by role, hub edge thicker)
    hub_idx = fixture.hub_room_index
    for room_idx, grown in enumerate(result.rooms):
        is_hub = room_idx == hub_idx
        color = ROLE_COLORS.get(grown.role, "#888888")
        alpha = 0.72 if is_hub else 0.55
        edge_color = "#111111" if is_hub else "#333333"
        edge_w = 1.8 if is_hub else 1.0

        room_poly = unary_union(
            [region_poly_by_id[rid] for rid in grown.region_ids]
        )
        for poly in _polygon_parts(room_poly):
            xs, ys = poly.exterior.xy
            ax.fill(
                xs, ys,
                facecolor=color, edgecolor=edge_color,
                alpha=alpha, linewidth=edge_w, zorder=4,
            )
            for ring in poly.interiors:
                hx, hy = ring.xy
                ax.fill(
                    hx, hy,
                    facecolor="#444444", edgecolor="#111111",
                    alpha=1.0, linewidth=0.7, zorder=5,
                )

        if not room_poly.is_empty:
            rp = room_poly.representative_point()
            hub_mark = "★ " if is_hub else ""
            ax.text(
                rp.x, rp.y,
                f"{hub_mark}{grown.name}\n{grown.role}\n{grown.area_m2:.1f}㎡",
                ha="center", va="center", fontsize=7,
                bbox={
                    "boxstyle": "round,pad=0.22",
                    "facecolor": "white",
                    "edgecolor": "#555555",
                    "linewidth": 0.5,
                    "alpha": 0.92,
                },
                zorder=12,
            )

    # 4. seed markers (use fixture seed_position if set, else first region centroid)
    for room_idx, spec in enumerate(fixture.rooms):
        if spec.seed_position is not None:
            x, y = spec.seed_position
        else:
            grown = result.rooms[room_idx]
            if not grown.region_ids:
                continue
            seed_region_id = grown.region_ids[0]
            poly = region_poly_by_id.get(seed_region_id)
            if poly is None or poly.is_empty:
                continue
            c = poly.centroid
            x, y = c.x, c.y
        is_hub = room_idx == hub_idx
        ax.scatter(
            x, y,
            s=120 if is_hub else 55,
            marker="*" if is_hub else "o",
            facecolor="#ffffff",
            edgecolor="#000000",
            linewidth=1.0,
            zorder=15,
        )

    # 5. footprint outline + axis
    _draw_footprint_outline(ax, shape)
    _finish_axis(ax, shape)

    # title summary
    parts = [
        f"K={fixture.K}",
        f"iter={result.diagnostics.get('total_iterations', 0)}",
        f"unassigned={len(result.unassigned_region_ids)}",
    ]
    below_min = result.diagnostics.get("below_min_area", ())
    if below_min:
        parts.append(f"below_min={list(below_min)}")
    ax.set_title(
        title or f"{fixture.case_name}  |  " + ", ".join(parts),
        fontsize=10,
    )
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def save_corridor_figure(
    shape: ShapeInput,
    fixture: LayoutFixture,
    path,
    *,
    layout: CorridoredLayout | None = None,
    title: str | None = None,
    policy: DimensionPolicy | None = None,
) -> Path:
    """Render the Phase 8 corridor carving result.

    Layers (bottom-up):

    1. faint region outlines (gray reference)
    2. leftover (hatched gray) — unassigned regions that survived cleanup
    3. base corridor regions (yellow fill, dark amber edge)
    4. shortcut corridor regions (magenta fill, dark edge)
    5. grown rooms (role-colored, hub edge thicker)
    6. room labels (name / role / area)
    7. footprint outline
    """
    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if layout is None:
        growth = region_partition_growth(shape, fixture, policy=policy)
        layout = carve_corridors(shape, growth, policy=policy)

    atoms = atomize(shape, policy)
    regions = regionize(shape, atoms=atoms, policy=policy)
    region_poly_by_id = {r.region_id: _to_shapely(r.shape) for r in regions}

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    # 1. faint region outlines
    for r in regions:
        poly = region_poly_by_id[r.region_id]
        xs, ys = poly.exterior.xy
        ax.plot(xs, ys, color="#cccccc", linewidth=0.4, zorder=1)
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.plot(hx, hy, color="#cccccc", linewidth=0.4, zorder=1)

    # 2. leftover (still-unassigned after carve + cleanup)
    for region_id in layout.leftover_region_ids:
        poly = region_poly_by_id[region_id]
        xs, ys = poly.exterior.xy
        ax.fill(
            xs, ys,
            facecolor="#dddddd", edgecolor="#888888",
            alpha=0.55, linewidth=0.6, hatch="///", zorder=2,
        )

    # 3. base corridor
    for region_id in layout.base_corridor_region_ids:
        poly = region_poly_by_id[region_id]
        xs, ys = poly.exterior.xy
        ax.fill(
            xs, ys,
            facecolor=CORRIDOR_BASE_FILL, edgecolor=CORRIDOR_BASE_EDGE,
            alpha=0.92, linewidth=0.9, zorder=3,
        )

    # 4. shortcut corridor (empty pre-W3, but already wired)
    for region_id in layout.shortcut_corridor_region_ids:
        poly = region_poly_by_id[region_id]
        xs, ys = poly.exterior.xy
        ax.fill(
            xs, ys,
            facecolor=CORRIDOR_SHORTCUT_FILL, edgecolor=CORRIDOR_SHORTCUT_EDGE,
            alpha=0.95, linewidth=1.0, zorder=3,
        )

    # 5. grown rooms
    hub_idx = fixture.hub_room_index
    for room_idx, grown in enumerate(layout.rooms):
        if not grown.region_ids:
            continue
        is_hub = room_idx == hub_idx
        color = ROLE_COLORS.get(grown.role, "#888888")
        alpha = 0.72 if is_hub else 0.55
        edge_color = "#111111" if is_hub else "#333333"
        edge_w = 1.8 if is_hub else 1.0

        room_poly = unary_union(
            [region_poly_by_id[rid] for rid in grown.region_ids]
        )
        for poly in _polygon_parts(room_poly):
            xs, ys = poly.exterior.xy
            ax.fill(
                xs, ys,
                facecolor=color, edgecolor=edge_color,
                alpha=alpha, linewidth=edge_w, zorder=4,
            )
            for ring in poly.interiors:
                hx, hy = ring.xy
                ax.fill(
                    hx, hy,
                    facecolor="#444444", edgecolor="#111111",
                    alpha=1.0, linewidth=0.7, zorder=5,
                )

        # 6. label
        if not room_poly.is_empty:
            rp = room_poly.representative_point()
            hub_mark = "★ " if is_hub else ""
            ax.text(
                rp.x, rp.y,
                f"{hub_mark}{grown.name}\n{grown.role}\n{grown.area_m2:.1f}㎡",
                ha="center", va="center", fontsize=7,
                bbox={
                    "boxstyle": "round,pad=0.22",
                    "facecolor": "white",
                    "edgecolor": "#555555",
                    "linewidth": 0.5,
                    "alpha": 0.92,
                },
                zorder=12,
            )

    # 7. footprint outline + axis
    _draw_footprint_outline(ax, shape)
    _finish_axis(ax, shape)

    parts = [
        f"K={fixture.K}",
        f"base={len(layout.base_corridor_region_ids)}",
        f"shortcut={len(layout.shortcut_corridor_region_ids)}",
        f"leftover={len(layout.leftover_region_ids)}",
    ]
    disc = layout.diagnostics.get("disconnected_rooms", ())
    if disc:
        parts.append(f"disconnected={list(disc)}")
    ax.set_title(
        title or f"{fixture.case_name}  |  " + ", ".join(parts),
        fontsize=10,
    )
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


SEED_PHASE_COLORS: dict[str, str] = {
    "hub":      "#d62728",  # red
    "coverage": "#ff8c00",  # orange
    "fps":      "#1f77b4",  # blue
}

SEED_PHASE_MARKERS: dict[str, str] = {
    "hub":      "*",
    "coverage": "s",
    "fps":      "o",
}

SEED_PHASE_SIZES: dict[str, int] = {
    "hub":      240,
    "coverage": 110,
    "fps":      80,
}


def save_seed_figure(
    shape: ShapeInput,
    path,
    *,
    K: int,
    has_public: bool,
    title: str | None = None,
    policy: DimensionPolicy | None = None,
) -> Path:
    """Render auto-placed seeds for Phase 7 Round 4 W2.

    Layers (bottom-up):
      1. faint atom backdrop
      2. region tint by territory (so multi-part footprints are legible)
      3. seed markers — phase-colored (hub=red star, coverage=orange square,
         fps=blue circle), annotated with region_id
      4. footprint outline
    """
    from matplotlib.lines import Line2D

    configure_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    atoms = atomize(shape, policy)
    regions = regionize(shape, atoms=atoms, policy=policy)
    region_graph = build_region_graph(
        shape, atoms=atoms, regions=regions, policy=policy,
    )
    territories = resolve_territories(shape)
    seeds = auto_place_seeds(
        region_graph, territories, K=K, has_public=has_public,
    )

    region_poly_by_id = {r.region_id: _to_shapely(r.shape) for r in regions}

    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)

    # 1. faint atom backdrop
    for atom in atoms:
        xs, ys = zip(*atom.shape.exterior)
        ax.fill(
            list(xs) + [xs[0]], list(ys) + [ys[0]],
            facecolor="#f5f5f5", edgecolor="#cccccc",
            alpha=0.6, linewidth=0.2, zorder=1,
        )

    # 2. region tint by territory
    for r in regions:
        terr = territory_of_region(r, territories)
        color = (
            PART_COLORS[terr.part_id % len(PART_COLORS)]
            if terr is not None else "#dddddd"
        )
        poly = region_poly_by_id[r.region_id]
        xs, ys = poly.exterior.xy
        ax.fill(
            xs, ys,
            facecolor=color, edgecolor="#999999",
            alpha=0.28, linewidth=0.5, zorder=2,
        )
        for ring in poly.interiors:
            hx, hy = ring.xy
            ax.fill(
                hx, hy,
                facecolor="#444444", edgecolor="#111111",
                alpha=1.0, linewidth=0.7, zorder=3,
            )

    # 3. seed markers + region_id labels
    seed_global_positions: dict[int, tuple[float, float]] = {}
    for i, s in enumerate(seeds):
        poly = region_poly_by_id[s.region.region_id]
        rp = poly.representative_point()
        seed_global_positions[i] = (rp.x, rp.y)
        ax.scatter(
            rp.x, rp.y,
            s=SEED_PHASE_SIZES[s.phase],
            marker=SEED_PHASE_MARKERS[s.phase],
            facecolor=SEED_PHASE_COLORS[s.phase],
            edgecolor="#000000",
            linewidth=1.0,
            zorder=15,
        )
        ax.text(
            rp.x, rp.y,
            f"R{s.region.region_id}",
            ha="center", va="center", fontsize=6,
            color="white",
            zorder=16,
        )

    # 4. footprint outline + axis
    _draw_footprint_outline(ax, shape)
    _finish_axis(ax, shape)

    # legend (phase → marker/color)
    legend_handles = [
        Line2D(
            [], [], marker=SEED_PHASE_MARKERS[p], color="w",
            markerfacecolor=SEED_PHASE_COLORS[p], markeredgecolor="black",
            markersize=10 if p == "hub" else 8,
            label=p,
        )
        for p in ("hub", "coverage", "fps")
    ]
    ax.legend(
        handles=legend_handles, loc="upper right",
        fontsize=7, frameon=True, framealpha=0.85,
    )

    # title summary (always appended so caller's title remains informative)
    phase_counts = {"hub": 0, "coverage": 0, "fps": 0}
    for s in seeds:
        phase_counts[s.phase] += 1
    summary = (
        f"K={K} · territories={len(territories)} · "
        + " ".join(f"{k}={v}" for k, v in phase_counts.items())
    )
    base_title = title or shape.name
    ax.set_title(f"{base_title}  |  {summary}", fontsize=10)

    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path
