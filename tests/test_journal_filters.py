from gui.journal_filters import _deduplicate_labels, empty_filter_state, filter_qsos, sort_qsos


def sample_qsos():
    return [
        {"call": "R1AAA", "name": "Алексей", "city": "Псков", "qth": "KO35",
         "band": "40m", "mode": "SSB", "freq": "7100", "rst_received": "59",
         "rst_sent": "59", "comment": "first", "datetime": "2026-09-20T10:30:00"},
        {"call": "R2BBB", "name": "Иван", "city": "Альметьевск", "qth": "LO66",
         "band": "20m", "mode": "CW", "freq": "14000", "rst_received": "599",
         "rst_sent": "599", "comment": "second", "datetime": "2026-09-30T23:30:00"},
        {"call": "R3CCC", "name": "Олег", "city": "Казань", "qth": "LO54",
         "band": "40m", "mode": "SSB", "freq": "7200", "rst_received": "57",
         "rst_sent": "58", "comment": "third", "datetime": "2026-10-01T01:30:00"},
    ]


def test_search_matches_substrings_across_all_fields():
    found = filter_qsos(sample_qsos(), "ал")
    assert [qso["call"] for qso in found] == ["R1AAA", "R2BBB"]


def test_band_and_mode_filters_combine_with_and():
    filters = empty_filter_state()
    filters["bands"] = ["40m"]
    filters["modes"] = ["SSB"]
    assert [qso["call"] for qso in filter_qsos(sample_qsos(), filters=filters)] == ["R1AAA", "R3CCC"]


def test_date_range_includes_both_boundary_dates():
    filters = empty_filter_state()
    filters.update({"date_range_enabled": True, "date_from": "20.09.2026", "date_to": "30.09.2026"})
    assert [qso["call"] for qso in filter_qsos(sample_qsos(), filters=filters)] == ["R1AAA", "R2BBB"]


def test_time_range_can_cross_midnight():
    filters = empty_filter_state()
    filters.update({"time_range_enabled": True, "time_from": "22:00", "time_to": "02:00"})
    assert [qso["call"] for qso in filter_qsos(sample_qsos(), filters=filters)] == ["R2BBB", "R3CCC"]


def test_frequency_sort_is_numeric_and_descending():
    sorted_qsos = sort_qsos(sample_qsos(), "freq_desc")
    assert [qso["freq"] for qso in sorted_qsos] == ["14000", "7200", "7100"]


def test_date_sort_uses_chronological_order():
    sorted_qsos = sort_qsos(sample_qsos(), "datetime_asc")
    assert [qso["call"] for qso in sorted_qsos] == ["R1AAA", "R2BBB", "R3CCC"]



def test_filter_labels_deduplicate_case_and_whitespace_variants():
    assert _deduplicate_labels(["AM", "FM", "SSB", "ssb", " SSB ", "CW", "fm", ""]) == [
        "AM", "FM", "SSB", "CW"
    ]
