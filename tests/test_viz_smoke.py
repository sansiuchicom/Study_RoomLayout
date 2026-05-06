"""Step 03 §4.5 viz smoke tests.

Cover DoD-4 (12-layer stable order + empty groups present) and DoD-6
(SVG file exists, valid XML, ≥1 footprint polygon).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from proto3.schema.input import BuildingInput
from proto3.schema.serialize import from_json
from proto3.viz import LAYER_ORDER, render


FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "apartment_minimal.json"


def _local(elem) -> str:
    """Strip XML namespace from a tag name."""
    return elem.tag.rsplit("}", 1)[-1]


def _load_minimal() -> BuildingInput:
    return from_json(BuildingInput, FIXTURE_PATH.read_text())


def test_viz_module_imports() -> None:
    """Trivial import smoke (carried over from §4.1 placeholder)."""
    import proto3.viz  # noqa: F401
    import proto3.viz.palette  # noqa: F401
    import proto3.viz.svg  # noqa: F401


def test_render_minimal_creates_file(tmp_path: Path) -> None:
    out = tmp_path / "minimal.svg"
    result = render(_load_minimal(), out_path=str(out))
    assert out.exists()
    assert out.stat().st_size > 0
    assert result == str(out)


def test_render_layer_order_stable(tmp_path: Path) -> None:
    out = tmp_path / "minimal.svg"
    render(_load_minimal(), out_path=str(out))
    root = ET.parse(out).getroot()
    assert _local(root) == "svg"
    groups = [g for g in root if _local(g) == "g"]
    assert len(groups) == 12, f"expected 12 layer groups, got {len(groups)}"
    classes = [g.attrib.get("class", "") for g in groups]
    expected = [f"layer-{i:02d}-{name}" for i, name in enumerate(LAYER_ORDER)]
    assert classes == expected


def test_render_footprint_polygon_present(tmp_path: Path) -> None:
    out = tmp_path / "minimal.svg"
    render(_load_minimal(), out_path=str(out))
    root = ET.parse(out).getroot()
    fp_layer = next(g for g in root if g.attrib.get("class") == "layer-00-footprint")
    polygons = [c for c in fp_layer if _local(c) == "polygon"]
    assert len(polygons) >= 1


def test_render_empty_layers_present_but_empty(tmp_path: Path) -> None:
    """Layers 1, 2, 4–11 must register as empty <g> per DoD-4 + S03-D1."""
    out = tmp_path / "minimal.svg"
    render(_load_minimal(), out_path=str(out))
    root = ET.parse(out).getroot()
    empty_layer_indices = [1, 2, 4, 5, 6, 7, 8, 9, 10, 11]
    for i in empty_layer_indices:
        layer = next(
            g for g in root
            if g.attrib.get("class", "").startswith(f"layer-{i:02d}-")
        )
        assert len(list(layer)) == 0, (
            f"layer {i:02d} should be empty in Step 03, has "
            f"{len(list(layer))} children"
        )
