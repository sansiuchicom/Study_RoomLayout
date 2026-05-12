from shapely.geometry import box

from celllayout_tf.viz import save_zoning_figure
from celllayout_tf.zoning import zone_footprint


def test_save_zoning_figure_writes_png(tmp_path):
    footprint = box(0, 0, 10, 10)
    result = zone_footprint(footprint, k=4)
    out = tmp_path / "zoning.png"

    save_zoning_figure(result, footprint, out, title="smoke")

    assert out.exists()
    assert out.stat().st_size > 0
