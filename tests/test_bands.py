import pytest

from services.bands import frequency_to_band


@pytest.mark.parametrize(("frequency", "expected"), [
    ("0.135700", "2190M"),
    ("0.472000", "630M"),
    ("1.900000", "160M"),
    ("3.700000", "80M"),
    ("7.100000", "40M"),
    ("10.125000", "30M"),
    ("14.074000", "20M"),
    ("18.100000", "17M"),
    ("21.074000", "15M"),
    ("24.915000", "12M"),
    ("28.400000", "10M"),
    ("145.000000", "2M"),
    ("435.500000", "70cm"),
    ("1296.000000", "23cm"),
    ("24025.000000", "1.25cm"),
])
def test_frequency_maps_to_russian_amateur_band(frequency, expected):
    assert frequency_to_band(frequency) == expected


@pytest.mark.parametrize("frequency", [
    "", "not-a-frequency", "0", "-145", "nan", "inf",
    "50.313", "146.000", "430.000", "440.000",
])
def test_frequency_outside_russian_amateur_allocations_is_not_guessed(frequency):
    assert frequency_to_band(frequency) is None


def test_frequency_accepts_decimal_comma():
    assert frequency_to_band("145,500") == "2M"


def test_frequency_band_lower_edge_is_included_and_upper_edge_excluded():
    assert frequency_to_band("144.000") == "2M"
    assert frequency_to_band("146.000") is None
