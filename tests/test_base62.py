import pytest

from app.services.base62 import encode, decode


def test_encode_zero():
    assert encode(0) == "0"


def test_encode_single_digits():
    assert encode(1) == "1"
    assert encode(9) == "9"


def test_encode_base62_boundary():
    assert encode(61) == "Z"
    assert encode(62) == "10"
    assert encode(63) == "11"


def test_encode_125():
    assert encode(125) == "21"


def test_decode_zero():
    assert decode("0") == 0


def test_decode_base62_boundary():
    assert decode("Z") == 61
    assert decode("10") == 62
    assert decode("11") == 63


def test_decode_125():
    assert decode("21") == 125


@pytest.mark.parametrize(
    "number",
    [
        0,
        1,
        9,
        10,
        61,
        62,
        63,
        125,
        1000,
        123456789,
    ],
)
def test_encode_decode_round_trip(number):
    assert decode(encode(number)) == number


def test_invalid_negative_number():
    with pytest.raises(ValueError):
        encode(-1)


def test_invalid_empty_string():
    with pytest.raises(ValueError):
        decode("")


def test_invalid_character():
    with pytest.raises(ValueError):
        decode("!")