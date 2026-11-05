"""Keyboard segment tracking for native date and time picker controls."""

import ctypes
import sys


_LOCALE_SSHORTDATE = 0x0000001F
_LOCALE_STIMEFORMAT = 0x00001003

_DATE_FIELDS = {"d": "day", "M": "month", "y": "year"}
_TIME_FIELDS = {"h": "hour", "H": "hour", "m": "minute", "s": "second"}


def _windows_locale_format(locale_type):
    """Return a Windows user-locale format string, or None if unavailable."""
    if sys.platform != "win32":
        return None

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_locale_info = kernel32.GetLocaleInfoEx
        get_locale_info.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint,
            ctypes.c_wchar_p,
            ctypes.c_int,
        ]
        get_locale_info.restype = ctypes.c_int

        required = get_locale_info(None, locale_type, None, 0)
        if required <= 1:
            return None

        buffer = ctypes.create_unicode_buffer(required)
        if not get_locale_info(None, locale_type, buffer, required):
            return None
        return buffer.value
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _field_order(format_string, field_map):
    """Extract unique date/time fields in their displayed order."""
    if not format_string:
        return []

    fields = []
    quoted = False
    index = 0

    while index < len(format_string):
        char = format_string[index]

        if char == "'":
            if index + 1 < len(format_string) and format_string[index + 1] == "'":
                index += 2
                continue
            quoted = not quoted
            index += 1
            continue

        if quoted or char not in field_map:
            index += 1
            continue

        while index + 1 < len(format_string) and format_string[index + 1] == char:
            index += 1

        field = field_map[char]
        if field not in fields:
            fields.append(field)
        index += 1

    return fields


def get_datetime_segments(control_name):
    """Get the native control's segment order from the Windows user locale."""
    if control_name == "date":
        fields = _field_order(
            _windows_locale_format(_LOCALE_SSHORTDATE), _DATE_FIELDS
        )
        return fields or ["day", "month", "year"]

    if control_name == "time":
        fields = _field_order(
            _windows_locale_format(_LOCALE_STIMEFORMAT), _TIME_FIELDS
        )
        return fields or ["hour", "minute", "second"]

    return []


def move_segment_index(current_index, direction, segment_count):
    """Return the wrapped segment index after a left/right navigation key."""
    if segment_count <= 0:
        return 0
    return (current_index + direction) % segment_count
