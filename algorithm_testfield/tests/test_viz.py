from celllayout_tf.cases import selected_cases
from celllayout_tf.schema import ShapeInput, ShapePart
from celllayout_tf.viz import save_input_figure


def test_save_input_figure_writes_png(tmp_path):
    shape = ShapeInput(
        name="rect",
        parts=(ShapePart(exterior=((0, 0), (12, 0), (12, 8), (0, 8))),),
    )
    out = tmp_path / "rect.png"

    save_input_figure(shape, out)

    assert out.exists()
    assert out.stat().st_size > 0


def test_save_input_figure_handles_multi_part_with_hole(tmp_path):
    shape = ShapeInput(
        name="ㅁ + wing",
        parts=(
            ShapePart(
                exterior=((0, 0), (12, 0), (12, 10), (0, 10)),
                holes=(((3, 3), (3, 7), (7, 7), (7, 3)),),
            ),
            ShapePart(exterior=((8, 5), (15, 5), (15, 9), (8, 9))),
        ),
    )
    out = tmp_path / "mh_wing.png"

    save_input_figure(shape, out)

    assert out.exists()
    assert out.stat().st_size > 0


def test_save_input_figure_for_showcase_subset(tmp_path):
    for idx, name, shape in selected_cases([1, 18, 22, 28]):
        out = tmp_path / f"{idx}.png"
        save_input_figure(shape, out, title=name)
        assert out.exists()
        assert out.stat().st_size > 0
