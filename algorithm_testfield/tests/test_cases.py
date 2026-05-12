import shapely.geometry as sg
from shapely.ops import unary_union

from celllayout_tf.cases import case_slug, make_cases, selected_cases
from celllayout_tf.schema import ShapeInput, ShapePart


def _to_shapely(part: ShapePart) -> sg.Polygon:
    return sg.Polygon(part.exterior, [list(h) for h in part.holes])


def _union(shape: ShapeInput):
    return unary_union([_to_shapely(p) for p in shape.parts])


def test_make_cases_returns_33_shape_inputs():
    cases = make_cases()
    assert len(cases) == 33
    assert all(isinstance(c, ShapeInput) for c in cases)


def test_first_and_last_case_names_match_original_indexing():
    cases = make_cases()
    assert cases[0].name == "30평 판상형"
    assert cases[-1].name == "ㅁ자 + wing"


def test_every_case_has_at_least_one_part_and_valid_union():
    for idx, case in enumerate(make_cases(), start=1):
        assert len(case.parts) >= 1, idx
        union = _union(case)
        assert not union.is_empty, idx
        assert union.area > 0, idx


def test_selected_cases_uses_one_based_indices_and_ignores_out_of_range():
    selected = selected_cases([1, 18, 999])
    assert [idx for idx, _name, _shape in selected] == [1, 18]
    assert selected[1][1] == "Rect rotated 30°"


def test_selected_cases_without_indices_returns_all():
    selected = selected_cases()
    assert len(selected) == 33
    assert selected[0][0] == 1
    assert selected[-1][0] == 33


def test_case_slug_is_stable_and_ascii_safe():
    assert case_slug(18, "Rect rotated 30°") == "18_rect_rotated_30"
    assert case_slug(1, "30평 판상형").startswith("01_30")
    assert case_slug(22, "Main + wing 25°") == "22_main_wing_25"


def test_main_plus_wing_25_has_axis_aligned_main_and_rotated_wing():
    cases = make_cases()
    case = cases[21]  # index 22
    assert case.name == "Main + wing 25°"
    assert len(case.parts) == 2
    # main: 4 vertices on axis-aligned rectangle
    assert len(case.parts[0].exterior) == 4
    # wing should have 4 vertices, rotated 25° from x-axis
    import math
    from celllayout_tf.schema import part_theta
    assert part_theta(case.parts[0]) == 0.0
    assert abs(part_theta(case.parts[1]) - math.radians(25)) < 1e-6


def test_mieum_small_hole_has_single_part_with_hole():
    cases = make_cases()
    case = cases[15]  # index 16
    assert case.name == "ㅁ자 small hole"
    assert len(case.parts) == 1
    assert len(case.parts[0].holes) == 1


def test_curved_giyeok_has_three_parts_with_disk():
    cases = make_cases()
    case = cases[27]  # index 28
    assert case.name == "Curved ㄱ"
    assert len(case.parts) == 3
    # last part is the disk — many vertices
    assert len(case.parts[2].exterior) > 32


def test_mieum_wing_has_hole_and_rotated_free_wing():
    cases = make_cases()
    case = cases[32]  # index 33
    assert case.name == "ㅁ자 + wing"
    assert len(case.parts) == 2
    assert len(case.parts[0].holes) == 1


def test_circle_case_is_single_high_vertex_part():
    cases = make_cases()
    case = cases[24]  # index 25
    assert case.name == "Circle r=6"
    assert len(case.parts) == 1
    assert len(case.parts[0].exterior) > 64
