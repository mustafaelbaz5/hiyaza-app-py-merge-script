from core.area import calculate_m2


def test_one_feddan():
    assert calculate_m2(1, 0, 0) == 4200.83


def test_24_qirat_equals_one_feddan():
    assert calculate_m2(0, 24, 0) == 4200.83


def test_576_sahm_equals_one_feddan():
    assert calculate_m2(0, 0, 576) == 4200.83


def test_zero():
    assert calculate_m2(0, 0, 0) == 0.0


def test_rounding_to_two_decimals():
    result = calculate_m2(1, 1, 1)
    assert result == round(result, 2)


def test_mixed_values():
    result = calculate_m2(2, 5, 10)
    expected = round(2 * 4200.833 + 5 * (4200.833 / 24) + 10 * (4200.833 / 24 / 24), 2)
    assert result == expected
