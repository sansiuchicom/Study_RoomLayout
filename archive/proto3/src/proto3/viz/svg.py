"""SVG renderer (Step 03 §4.4 — D013).

Stable 12-layer order from palette.LAYER_ORDER. Empty layers register as
empty <g> groups so later Stages can fill them without renderer changes.
Coordinates: mm in, mm in viewBox; Y axis flipped (math-y up → SVG-y down).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from proto3.schema.input import BuildingInput
from proto3.viz.palette import (
    GRID_SPACING_MM,
    LAYER_COLORS,
    LAYER_ORDER,
)

_SVG_NS = "http://www.w3.org/2000/svg"
_PADDING_RATIO = 0.05  # 5% of max bbox edge (S03-D6)
_DISPLAY_MAX_PX = 800  # viewBox stays in mm; width/height attrs scale display


def _bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _to_svg_xy(x: float, y: float, bbox, pad: float) -> tuple[float, float]:
    min_x, _min_y, _max_x, max_y = bbox
    return (x - min_x) + pad, (max_y - y) + pad


def _layer(svg_root, idx: int, name: str):
    return ET.SubElement(svg_root, "g", {"class": f"layer-{idx:02d}-{name}"})


def _draw_grid(parent, bbox, pad: float, spacing: int = GRID_SPACING_MM):
    min_x, min_y, max_x, max_y = bbox
    grid = ET.SubElement(parent, "g", {"class": "grid-100mm"})
    # Vertical lines aligned to spacing multiples
    x = int(min_x // spacing) * spacing
    while x <= max_x:
        x1, y1 = _to_svg_xy(x, min_y, bbox, pad)
        x2, y2 = _to_svg_xy(x, max_y, bbox, pad)
        ET.SubElement(grid, "line", {
            "x1": f"{x1:g}", "y1": f"{y1:g}",
            "x2": f"{x2:g}", "y2": f"{y2:g}",
            "stroke": "#e8e8e8", "stroke-width": "8",
        })
        x += spacing
    y = int(min_y // spacing) * spacing
    while y <= max_y:
        x1, y1 = _to_svg_xy(min_x, y, bbox, pad)
        x2, y2 = _to_svg_xy(max_x, y, bbox, pad)
        ET.SubElement(grid, "line", {
            "x1": f"{x1:g}", "y1": f"{y1:g}",
            "x2": f"{x2:g}", "y2": f"{y2:g}",
            "stroke": "#e8e8e8", "stroke-width": "8",
        })
        y += spacing


def render(
    building: BuildingInput,
    *,
    regions=None,
    atoms=None,
    graph=None,
    spine=None,
    anchors=None,
    role_scores=None,
    slots=None,
    seeds=None,
    grown=None,
    doors=None,
    failure=None,
    out_path: str,
) -> str:
    """Render a BuildingInput (+ optional Stage outputs) to a single SVG file.

    All optional kwargs default to None; the corresponding layer registers as
    an empty <g> group. Step 03 only draws the footprint and the 100mm grid;
    later Steps populate the remaining layers.

    Step 06 §4.7 (S06-D11) tightens the contract for `atoms` / `regions` /
    `spine`: passing a non-None value raises ValueError because the renderer
    cannot honor those layers yet. Silently ignoring (Step 03 frame) hid
    Step 05 atoms render bugs (외부 review #11). Real atoms / regions / spine
    rendering arrives in Step 07 (Plan Def-12). Other kwargs (graph / anchors
    / role_scores / slots / seeds / grown / doors / failure) remain silent
    no-ops until their producing Stage lands.
    """
    _step07_unsupported = []
    if atoms is not None:
        _step07_unsupported.append("atoms")
    if regions is not None:
        _step07_unsupported.append("regions")
    if spine is not None:
        _step07_unsupported.append("spine")
    if _step07_unsupported:
        raise ValueError(
            f"render() received non-None values for {_step07_unsupported}; "
            f"actual rendering of those layers is Step 07 territory "
            f"(Plan Def-12). Pass None or omit to keep the layer empty."
        )

    if not building.floors:
        raise ValueError("BuildingInput.floors must contain at least one floor")
    floor = building.floors[0]
    if not floor.footprint:
        raise ValueError("FloorInput.footprint must be a non-empty polygon")

    bbox = _bbox(floor.footprint)
    min_x, min_y, max_x, max_y = bbox
    width_mm = max_x - min_x
    height_mm = max_y - min_y
    pad = max(width_mm, height_mm) * _PADDING_RATIO
    vb_w = width_mm + 2 * pad
    vb_h = height_mm + 2 * pad

    scale = _DISPLAY_MAX_PX / max(vb_w, vb_h)
    disp_w = vb_w * scale
    disp_h = vb_h * scale

    svg = ET.Element("svg", {
        "xmlns": _SVG_NS,
        "viewBox": f"0 0 {vb_w:g} {vb_h:g}",
        "width": f"{disp_w:g}",
        "height": f"{disp_h:g}",
    })

    layers = {name: _layer(svg, i, name) for i, name in enumerate(LAYER_ORDER)}

    # Layer 0 footprint
    fp_pts = [_to_svg_xy(x, y, bbox, pad) for x, y in floor.footprint]
    ET.SubElement(layers["footprint"], "polygon", {
        "points": " ".join(f"{x:g},{y:g}" for x, y in fp_pts),
        "fill": "none",
        "stroke": LAYER_COLORS["footprint"],
        "stroke-width": "40",
    })

    # Layer 3 atoms — 100mm reference grid only; real atom cells land in Step 07+
    _draw_grid(layers["atoms"], bbox, pad)

    # Layers 1, 2, 4-11 stay empty groups for now. Future Stages fill them via
    # the corresponding kwarg. The empty <g> presence is part of the contract
    # (DoD-4) so layer order stays stable across Steps.
    _ = (regions, atoms, graph, spine, anchors, role_scores,
         slots, seeds, grown, doors, failure)

    ET.indent(svg, space="  ")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(svg).write(out_path, encoding="utf-8", xml_declaration=True)
    return out_path
