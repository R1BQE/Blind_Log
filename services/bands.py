"""Frequency-to-band mapping for amateur allocations used in Russia.

The frequency values are in MHz. Band names use the ADIF Band enumeration.
"""
import math


# National amateur allocations (MHz), based on the Russian amateur-service
# allocation summary. Upper limits are exclusive to avoid ambiguous edges.
RUSSIAN_AMATEUR_BANDS = (
    (0.1357, 0.1378, "2190M"),
    (0.472, 0.479, "630M"),
    (1.810, 2.000, "160M"),
    (3.500, 3.800, "80M"),
    (7.000, 7.200, "40M"),
    (10.100, 10.150, "30M"),
    (14.000, 14.350, "20M"),
    (18.068, 18.168, "17M"),
    (21.000, 21.450, "15M"),
    (24.890, 24.990, "12M"),
    (28.000, 29.700, "10M"),
    (144.000, 146.000, "2M"),
    (430.000, 440.000, "70cm"),
    (1260.000, 1300.000, "23cm"),
    (24000.000, 24050.000, "1.25cm"),
    (47000.000, 47200.000, "6mm"),
    (77500.000, 78000.000, "4mm"),
    (134000.000, 136000.000, "2mm"),
    (248000.000, 250000.000, "1mm"),
)


def frequency_to_band(frequency_mhz):
    """Return an ADIF band name for a frequency in MHz, or None.

    The function intentionally does not guess a band outside the published
    Russian amateur allocations.
    """
    try:
        frequency = float(str(frequency_mhz).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(frequency) or frequency <= 0:
        return None
    for lower, upper, band in RUSSIAN_AMATEUR_BANDS:
        if lower <= frequency < upper:
            return band
    return None
