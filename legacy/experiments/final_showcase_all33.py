"""Generate the 33-case final showcase image for Pipeline 12."""
from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import shapely.geometry as sg

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from roomlayout_cell.experiments import showcase_cases
from roomlayout_cell.zoning import pipeline12


def configure_fonts():
    font_path = Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
    if font_path.exists():
        font_manager.fontManager.addfont(font_path)
        plt.rcParams["font.family"] = "NanumGothic"
    plt.rcParams["axes.unicode_minus"] = False


def piece_quality_mrr(piece):
    if piece.is_empty or piece.area < 1e-6:
        return {"aspect": 99, "compactness": 0, "score": 0}
    try:
        mbr = piece.minimum_rotated_rectangle
        coords = list(mbr.exterior.coords)
        e1 = np.hypot(coords[1][0] - coords[0][0], coords[1][1] - coords[0][1])
        e2 = np.hypot(coords[2][0] - coords[1][0], coords[2][1] - coords[1][1])
        if min(e1, e2) < 1e-6:
            return {"aspect": 99, "compactness": 0, "score": 0}
        aspect = max(e1, e2) / min(e1, e2)
        compactness = piece.area / mbr.area
    except Exception:
        return {"aspect": 99, "compactness": 0, "score": 0}
    if 1.0 <= aspect <= 2.5:
        asp_s = 1.0
    elif aspect <= 4.0:
        asp_s = 1.0 - (aspect - 2.5) / 1.5 * 0.5
    else:
        asp_s = 0.3
    return {"aspect": aspect, "compactness": compactness, "score": 0.5 * compactness + 0.5 * asp_s}


def quality_mark(q):
    if q >= 0.95:
        return "★"
    if q >= 0.85:
        return "·"
    return "!"


def plot_result(ax, idx, name, footprint, zones, families, q):
    colors = [
        "#f2b3b6", "#f8c281", "#b79bd0", "#acd6ca", "#9ecbdd",
        "#cfde95", "#dfb3d7", "#b8cde0", "#ffdf3f", "#a9df9d",
    ]
    for z in zones:
        poly = z["polygon"]
        if isinstance(poly, sg.MultiPolygon):
            parts = list(poly.geoms)
        else:
            parts = [poly]
        for part in parts:
            if part.is_empty:
                continue
            x, y = part.exterior.xy
            ax.fill(
                x, y,
                color=colors[z["zone_id"] % len(colors)],
                edgecolor="black",
                linewidth=1.0,
                alpha=0.92,
            )

    x, y = footprint.exterior.xy
    ax.plot(x, y, color="black", linewidth=1.6)
    for hole in footprint.interiors:
        hx, hy = hole.xy
        ax.fill(hx, hy, color="#444444", zorder=10)

    if len(families) > 1:
        for family in families:
            poly = family["polygon"]
            parts = list(poly.geoms) if isinstance(poly, sg.MultiPolygon) else [poly]
            for part in parts:
                if part.is_empty:
                    continue
                fx, fy = part.exterior.xy
                ax.plot(fx, fy, "--", color="red", linewidth=0.8, alpha=0.65, zorder=20)

    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(
        f"{idx}. {name}\n#{len(zones)} q={q:.2f} {quality_mark(q)}",
        fontsize=8,
        fontweight="bold",
        pad=3,
    )


def generate(output="final_showcase_all33.png"):
    configure_fonts()
    cases = showcase_cases.make_showcase_cases()
    cols = 6
    rows = int(np.ceil(len(cases) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(24, 4.0 * rows))
    axes = axes.ravel()

    scores = []
    for i, (name, footprint) in enumerate(cases, start=1):
        zones, families = pipeline12.zone_footprint(footprint)
        q = float(np.mean([piece_quality_mrr(z["polygon"])["score"] for z in zones]))
        scores.append(q)
        plot_result(axes[i - 1], i, name, footprint, zones, families, q)

    for ax in axes[len(cases):]:
        ax.axis("off")

    fig.suptitle(
        "Pipeline 12 — Final Zoning Algorithm: 33 cases\n"
        "(red dashed = family boundary; ★ q>=0.95, · q>=0.85, ! q<0.85)",
        fontsize=18,
        fontweight="bold",
        y=0.995,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    out = PROJECT_ROOT / "outputs" / "figures" / output
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"saved: {out}")
    print(f"cases={len(cases)} avg_q={np.mean(scores):.3f}")


if __name__ == "__main__":
    generate()
