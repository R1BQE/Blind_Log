"""ADIF import support for Blind_Log.

This module provides a minimal import scaffold using adif-io.
It parses .adi files into internal QSO dictionaries and returns
an operation Result for future integration.
"""

from datetime import datetime
from utils import Result

try:
    import adif_io
except ImportError:
    adif_io = None


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


def import_adif_file(filepath, encoding='utf-8'):
    """Read an ADIF file and return parsed QSOs in internal format."""
    if adif_io is None:
        return Result(False, error="Missing dependency: adif-io")

    try:
        qsos_raw, headers = adif_io.read_from_file(filepath, encoding=encoding)
    except Exception as e:
        return Result(False, error=str(e))

    qsos = []
    for qso in qsos_raw:
        internal_qso = _map_adif_to_internal(qso)
        if internal_qso['call']:
            qsos.append(internal_qso)

    return Result(True, data={'qsos': qsos, 'headers': headers})
