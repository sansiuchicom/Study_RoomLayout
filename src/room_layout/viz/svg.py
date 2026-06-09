"""Canonical layered SVG renderer (Step 08 §4.4 — S08-D2).

Adapts proto3 ``viz/svg.py``'s *architecture* — ordered, named ``<g>`` layer
groups (``layer-NN-name`` class), ``xml.etree.ElementTree`` construction,
Y-flip (math-y-up → SVG-y-down), ``viewBox`` + padding + display-scale — to
**our** schema (``FloorShape`` / ``ShapePart`` with parts + holes,
``LabeledFloorLayout``) and **meters** (proto3 was mm — ``proto3:D019`` dropped,
Pipeline §2.4). Layer names + order + colors come from ``viz.palette`` (S08-D6),
not a local table.

The canonical FINAL render lights: ``grid`` / ``footprint`` / ``anchors``
(optional) / ``corridor`` / ``rooms`` (7-class role fill) / ``labels``. The
remaining layers (``atoms`` / ``regions`` / ``region-graph`` / ``seeds`` /
``grown`` / ``failure``) register as **empty ``<g>`` groups** — the stable-order
contract (proto3 DoD-4) — and are filled by the per-stage debug SVGs the
``SvgRunWriter`` emits (4.5).

Pure stdlib + shapely + the schema; no matplotlib (this is the *canonical*
path, not the dev-bridge). ``vertical_circulation`` rooms arrive inside
``layout.rooms`` (role fill); the ``anchors`` kwarg is for drawing the raw
``VerticalAnchor`` footprints (vc outline + ``host_role=None`` forbidden shafts)
as an overlay when the caller has them.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterable, Sequence
from pathlib import Path

from shapely.geometry import Polygon

from room_layout.schema import FloorShape, LabeledFloorLayout
from room_layout.schema.geometry import VerticalAnchor
from room_layout.stages._helpers import to_shapely
from room_layout.viz.palette import (
    GRID_SPACING_M,
    LABEL_FONT_FAMILY,
    LABEL_FONT_SIZE_RATIO,
    LAYER_COLORS,
    LAYER_ORDER,
    PADDING_RATIO,
    role_color,
)

_SVG_NS = "http://www.w3.org/2000/svg"
_DISPLAY_MAX_PX = 800  # viewBox stays in meters; width/height attrs scale display

# Stroke widths + label size as fractions of the larger bbox edge, so a line
# reads the same whether the floor is 6 m or 16 m across (proto3 used fixed mm).
_STROKE = {
    "grid": 0.0015,
    "footprint": 0.007,
    "room": 0.002,
    "room_vc": 0.006,
    "corridor": 0.002,
    "anchor": 0.004,
}


# --- geometry → SVG coordinate helpers -------------------------------------


def _bbox_of_floor(floor: FloorShape) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for part in floor.parts:
        for x, y in part.exterior:
            xs.append(x)
            ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def _make_transform(bbox, pad: float):
    """math-y-up world (meters) → SVG-y-down, origin at padded top-left."""
    min_x, _min_y, _max_x, max_y = bbox

    def tf(x: float, y: float) -> tuple[float, float]:
        return (x - min_x) + pad, (max_y - y) + pad

    return tf


def _poly_path_d(poly: Polygon, tf) -> str:
    """``d`` for a shapely Polygon: exterior + holes as subpaths (evenodd fill)."""
    subpaths: list[str] = []
    rings = [poly.exterior, *poly.interiors]
    for ring in rings:
        pts = [tf(x, y) for x, y in ring.coords]
        subpaths.append("M " + " L ".join(f"{a:g} {b:g}" for a, b in pts) + " Z")
    return " ".join(subpaths)


# --- per-layer draws -------------------------------------------------------


def _draw_grid(g, bbox, pad: float, tf, su: float) -> None:
    min_x, min_y, max_x, max_y = bbox
    sw = f"{su * _STROKE['grid']:g}"
    color = LAYER_COLORS["grid"]
    x = (int(min_x // GRID_SPACING_M)) * GRID_SPACING_M
    while x <= max_x:
        x1, y1 = tf(x, min_y)
        x2, y2 = tf(x, max_y)
        ET.SubElement(
            g,
            "line",
            {
                "x1": f"{x1:g}",
                "y1": f"{y1:g}",
                "x2": f"{x2:g}",
                "y2": f"{y2:g}",
                "stroke": color,
                "stroke-width": sw,
            },
        )
        x += GRID_SPACING_M
    y = (int(min_y // GRID_SPACING_M)) * GRID_SPACING_M
    while y <= max_y:
        x1, y1 = tf(min_x, y)
        x2, y2 = tf(max_x, y)
        ET.SubElement(
            g,
            "line",
            {
                "x1": f"{x1:g}",
                "y1": f"{y1:g}",
                "x2": f"{x2:g}",
                "y2": f"{y2:g}",
                "stroke": color,
                "stroke-width": sw,
            },
        )
        y += GRID_SPACING_M


def _draw_footprint(g, floor: FloorShape, tf, su: float) -> None:
    sw = f"{su * _STROKE['footprint']:g}"
    for part in floor.parts:
        ET.SubElement(
            g,
            "path",
            {
                "d": _poly_path_d(to_shapely(part), tf),
                "fill": "none",
                "stroke": LAYER_COLORS["footprint"],
                "stroke-width": sw,
                "fill-rule": "evenodd",
            },
        )


def _draw_anchors(g, anchors: Iterable[VerticalAnchor], level: int, tf, su: float) -> None:
    sw = f"{su * _STROKE['anchor']:g}"
    for a in anchors:
        lo, hi = a.floor_range
        if not (lo <= level <= hi):
            continue
        is_vc = a.host_role == "vertical_circulation"
        ET.SubElement(
            g,
            "path",
            {
                "d": _poly_path_d(a.footprint_polygon, tf),
                # forbidden shafts (host_role=None) hatch-fill faint; vc = outline only
                "fill": "none" if is_vc else LAYER_COLORS["anchors"],
                "fill-opacity": "0" if is_vc else "0.18",
                "stroke": LAYER_COLORS["anchors"],
                "stroke-width": sw,
                "stroke-dasharray": "none" if is_vc else f"{su * 0.01:g}",
            },
        )


def _draw_corridors(g, corridor_polygons: Sequence[Polygon], tf, su: float) -> None:
    sw = f"{su * _STROKE['corridor']:g}"
    color = LAYER_COLORS["corridor"]
    for poly in corridor_polygons:
        ET.SubElement(
            g,
            "path",
            {
                "d": _poly_path_d(poly, tf),
                "fill": color,
                "fill-opacity": "0.55",
                "stroke": color,
                "stroke-width": sw,
                "fill-rule": "evenodd",
            },
        )


def _draw_rooms(g, rooms, tf, su: float) -> None:
    for room in rooms:
        is_vc = room.role == "vertical_circulation"
        ET.SubElement(
            g,
            "path",
            {
                "d": _poly_path_d(room.polygon, tf),
                "fill": role_color(room.role),
                "fill-opacity": "0.85",
                "stroke": "#7a3b3b" if is_vc else "#222222",
                "stroke-width": f"{su * (_STROKE['room_vc'] if is_vc else _STROKE['room']):g}",
                "fill-rule": "evenodd",
            },
        )


def _draw_labels(g, rooms, tf, su: float) -> None:
    fs = su * LABEL_FONT_SIZE_RATIO
    for room in rooms:
        rp = room.polygon.representative_point()
        x, y = tf(rp.x, rp.y)
        text = ET.SubElement(
            g,
            "text",
            {
                "x": f"{x:g}",
                "y": f"{y:g}",
                "font-family": LABEL_FONT_FAMILY,
                "font-size": f"{fs:g}",
                "text-anchor": "middle",
                "dominant-baseline": "central",
                "fill": "#111111",
            },
        )
        line1 = ET.SubElement(text, "tspan", {"x": f"{x:g}", "dy": f"{-fs * 0.3:g}"})
        line1.text = room.id
        line2 = ET.SubElement(
            text,
            "tspan",
            {"x": f"{x:g}", "dy": f"{fs * 1.1:g}", "font-size": f"{fs * 0.8:g}", "fill": "#555555"},
        )
        line2.text = f"[{room.role}] {room.area_m2:.1f}m²"


# --- entry point -----------------------------------------------------------


def render(
    floor: FloorShape,
    layout: LabeledFloorLayout,
    out_path: str | Path,
    *,
    anchors: Iterable[VerticalAnchor] = (),
    title: str | None = None,
) -> str:
    """Render one labeled floor to a single layered ``.svg`` file.

    ``floor`` supplies the footprint + bbox; ``layout`` supplies the carved
    rooms (role fill) + corridor polygons. ``anchors`` optionally overlays the
    raw ``VerticalAnchor`` footprints (filtered to this floor's level). All 12
    ``viz.palette.LAYER_ORDER`` layers are emitted in order as ``<g>`` groups;
    unlit ones stay empty (stable-order contract). Returns ``out_path``.
    """
    bbox = _bbox_of_floor(floor)
    min_x, min_y, max_x, max_y = bbox
    w = max_x - min_x
    h = max_y - min_y
    su = max(w, h)
    pad = su * PADDING_RATIO
    vb_w = w + 2 * pad
    vb_h = h + 2 * pad
    scale = _DISPLAY_MAX_PX / max(vb_w, vb_h)
    tf = _make_transform(bbox, pad)

    svg = ET.Element(
        "svg",
        {
            "xmlns": _SVG_NS,
            "viewBox": f"0 0 {vb_w:g} {vb_h:g}",
            "width": f"{vb_w * scale:g}",
            "height": f"{vb_h * scale:g}",
        },
    )
    if title is not None:
        ET.SubElement(svg, "title").text = title

    layers = {
        name: ET.SubElement(svg, "g", {"class": f"layer-{i:02d}-{name}"})
        for i, name in enumerate(LAYER_ORDER)
    }

    _draw_grid(layers["grid"], bbox, pad, tf, su)
    _draw_footprint(layers["footprint"], floor, tf, su)
    if anchors:
        _draw_anchors(layers["anchors"], anchors, floor.level, tf, su)
    _draw_corridors(layers["corridor"], layout.corridor_polygons, tf, su)
    _draw_rooms(layers["rooms"], layout.rooms, tf, su)
    _draw_labels(layers["labels"], layout.rooms, tf, su)

    ET.indent(svg, space="  ")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(svg).write(out, encoding="utf-8", xml_declaration=True)
    return str(out_path)
