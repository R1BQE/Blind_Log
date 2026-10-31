"""ADIF import support for Blind_Log."""

from datetime import datetime
import re

from common.utils import Result

try:
    import adif_io
except ImportError:
    adif_io = None


# ADIF field descriptors are ASCII. The optional type suffix is part of the
# descriptor, while the declared length describes the value that follows.
_FIELD_RE = re.compile(rb"<([A-Za-z0-9_]+):(\d+)(?::[^>]*)?>")


def _normalize_datetime(qso):
    qso_date = qso.get('QSO_DATE') or qso.get('QSO_DATE_OFF') or ''
    time_value = qso.get('TIME_ON') or qso.get('TIME_OFF') or ''
    if not qso_date:
        return ''

    time_value = time_value.strip()
    if len(time_value) == 4:
        time_value += '00'
    elif len(time_value) == 2:
        time_value += '0000'
    elif len(time_value) == 0:
        time_value = '000000'

    try:
        parsed = datetime.strptime(qso_date + time_value, '%Y%m%d%H%M%S')
        return parsed.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        try:
            parsed = datetime.strptime(qso_date, '%Y%m%d')
            return parsed.strftime('%Y-%m-%d')
        except ValueError:
            return ''


def _map_adif_to_internal(qso):
    return {
        'call': qso.get('CALL', '').strip().upper(),
        'name': qso.get('NAME', '').strip(),
        'city': qso.get('QTH', '').strip(),
        'qth': qso.get('GRIDSQUARE', '').strip(),
        'band': qso.get('BAND', '').strip(),
        'mode': qso.get('MODE', '').strip(),
        'freq': qso.get('FREQ', '').strip(),
        'rst_received': qso.get('RST_RCVD', '').strip(),
        'rst_sent': qso.get('RST_SENT', '').strip(),
        'comment': qso.get('COMMENT', '').strip(),
        'datetime': _normalize_datetime(qso),
    }


def _decode_mixed_adif(raw_data):
    """Normalize a legacy ADI containing CP1251 and UTF-8 field values.

    Some loggers write the ADIF character count as the encoded byte count,
    including for UTF-8 values. We therefore consume each declared value as
    bytes, decode it as CP1251 first and use UTF-8 only when CP1251 cannot
    decode that value. The descriptor length is then rewritten as the number
    of Unicode code points expected by adif-io.

    This is deliberately a fallback for malformed, mixed-encoding legacy
    files. Standard UTF-8 and CP1251 files continue through the normal reader.
    """
    chunks = []
    position = 0
    data_length = len(raw_data)

    while position < data_length:
        match = _FIELD_RE.search(raw_data, position)
        if match is None:
            chunks.append(raw_data[position:].decode('cp1251'))
            break

        # Text between descriptors (normally whitespace or ADIF header text).
        chunks.append(raw_data[position:match.start()].decode('cp1251'))
        value_length = int(match.group(2))
        value_start = match.end()
        value_end = value_start + value_length
        if value_end > data_length:
            raise ValueError("ADIF field value is shorter than its declared byte length")

        raw_value = raw_data[value_start:value_end]
        try:
            value = raw_value.decode('cp1251')
        except UnicodeDecodeError:
            value = raw_value.decode('utf-8')

        descriptor = match.group(1).decode('ascii')
        type_suffix = b''
        descriptor_tail = raw_data[match.start():match.end()]
        colon_parts = descriptor_tail[:-1].split(b':', 2)
        if len(colon_parts) == 3:
            type_suffix = b':' + colon_parts[2]
        chunks.append(f"<{descriptor}:{len(value)}" + type_suffix.decode('ascii') + ">" + value)
        position = value_end

    return ''.join(chunks)


def import_adif_file(filepath, encoding=None):
    """Read an ADIF file and return parsed QSOs in internal format.

    Detects UTF-8 first and supports legacy CP1251 files. If a file mixes
    encodings and strict CP1251 decoding fails, field values are normalized
    individually before they are passed to adif-io.
    """
    if adif_io is None:
        return Result(False, error="Missing dependency: adif-io")

    if encoding:
        try:
            qsos_raw, headers = adif_io.read_from_file(filepath, encoding=encoding)
        except Exception as exc:
            return Result(False, error=str(exc))
    else:
        try:
            with open(filepath, "rb") as raw_file:
                raw_data = raw_file.read()
            text = raw_data.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = raw_data.decode("cp1251")
            except UnicodeDecodeError:
                try:
                    text = _decode_mixed_adif(raw_data)
                except (UnicodeDecodeError, ValueError) as exc:
                    return Result(False, error=f"Cannot decode mixed-encoding ADIF file: {exc}")
                try:
                    qsos_raw, headers = adif_io.read_from_string(text)
                except Exception as exc:
                    return Result(False, error=str(exc))
            else:
                try:
                    qsos_raw, headers = adif_io.read_from_string(text)
                except Exception as exc:
                    return Result(False, error=str(exc))
        else:
            try:
                qsos_raw, headers = adif_io.read_from_string(text)
            except Exception as exc:
                return Result(False, error=str(exc))

    qsos = []
    for qso in qsos_raw:
        internal_qso = _map_adif_to_internal(qso)
        if internal_qso['call']:
            qsos.append(internal_qso)

    return Result(True, data={'qsos': qsos, 'headers': headers})


def is_adif_available():
    """Возвращает True если библиотека adif-io установлена и импорт доступен."""
    return adif_io is not None
