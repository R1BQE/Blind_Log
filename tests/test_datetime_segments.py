from accessibility.datetime_segments import (
    _field_order,
    move_segment_index,
)


def test_date_fields_follow_display_order_and_ignore_quoted_text():
    assert _field_order("'Day:' dd.MM.yyyy", {"d": "day", "M": "month", "y": "year"}) == [
        "day", "month", "year"
    ]
    assert _field_order("M/d/yyyy", {"d": "day", "M": "month", "y": "year"}) == [
        "month", "day", "year"
    ]


def test_time_fields_include_seconds_and_ignore_ampm_marker():
    assert _field_order("h:mm:ss tt", {"h": "hour", "H": "hour", "m": "minute", "s": "second"}) == [
        "hour", "minute", "second"
    ]


def test_field_parser_does_not_duplicate_repeated_tokens():
    assert _field_order("dddd, MMMM d, yyyy", {"d": "day", "M": "month", "y": "year"}) == [
        "day", "month", "year"
    ]


def test_segment_index_moves_forward_backward_and_wraps():
    assert move_segment_index(0, 1, 3) == 1
    assert move_segment_index(2, 1, 3) == 0
    assert move_segment_index(0, -1, 3) == 2
    assert move_segment_index(1, -1, 3) == 0


def test_segment_index_handles_empty_controls():
    assert move_segment_index(0, 1, 0) == 0
