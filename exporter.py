from datetime import datetime
import adif_io
from i18n import tr
from utils import Result
from logger import log_user_action, log_error

class Exporter:
    def __init__(self, qso_manager, settings_manager):
        self.qso_manager = qso_manager
        self.settings_manager = settings_manager

    def _serialize_datetime(self, dt_raw):
        """Convert QSO datetime value to ADIF date and time strings."""
        qso_date = ''
        qso_time = ''
        if not dt_raw:
            return qso_date, qso_time

        raw = dt_raw.strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(raw, fmt)
                qso_date = parsed.strftime('%Y%m%d')
                if '%H' in fmt:
                    qso_time = parsed.strftime('%H%M%S')
                return qso_date, qso_time
            except ValueError:
                continue

        digits = ''.join(ch for ch in raw if ch.isdigit())
        if len(digits) >= 8:
            qso_date = digits[:8]
            if len(digits) >= 14:
                qso_time = digits[8:14]
        return qso_date, qso_time

    def _build_adif_qso(self, qso, visible):
        """Build an ADIF QSO record using adif_io conventions."""
        adif_qso = {}
        adif_qso['CALL'] = qso.get('call', '')
        qso_date, qso_time = self._serialize_datetime(qso.get('datetime', ''))
        if visible.get('date', True) and qso_date:
            adif_qso['QSO_DATE'] = qso_date
        if visible.get('time', True) and qso_time:
            adif_qso['TIME_ON'] = qso_time
        if visible.get('freq', True) and qso.get('freq'):
            adif_qso['FREQ'] = qso.get('freq')
        if visible.get('mode', True) and qso.get('mode'):
            adif_qso['MODE'] = qso.get('mode')
        if visible.get('rst_sent', True) and qso.get('rst_sent'):
            adif_qso['RST_SENT'] = qso.get('rst_sent')
        if visible.get('rst_received', True) and qso.get('rst_received'):
            adif_qso['RST_RCVD'] = qso.get('rst_received')
        if visible.get('qth', True) and qso.get('qth'):
            adif_qso['GRIDSQUARE'] = qso.get('qth')
        if visible.get('band', True) and qso.get('band'):
            adif_qso['BAND'] = qso.get('band')
        if visible.get('name', True) and qso.get('name'):
            adif_qso['NAME'] = qso.get('name').replace('<', '').replace('>', '')
        if visible.get('city', True) and qso.get('city'):
            adif_qso['QTH'] = qso.get('city').replace('<', '').replace('>', '')
        if visible.get('comment', True) and qso.get('comment'):
            adif_qso['COMMENT'] = qso.get('comment').replace('<', '').replace('>', '')

        return adif_io.qso_from_dict(adif_qso)

    def export_to_adif(self, filepath):
        """Экспортирует QSO в ADIF и возвращает Result."""
        log_user_action("Start ADIF export")
        if not hasattr(self.settings_manager, 'settings'):
            log_error("Settings not loaded")
            return Result(False, error=tr("error.settings_not_loaded"))

        visible = self.settings_manager.get_visible_fields()
        qso_records = [self._build_adif_qso(qso, visible) for qso in self.qso_manager.get_qso_list()]
        headers = {
            'ADIF_VER': '3.1.7',
        }
        operator = self.settings_manager.get_option('call', '').strip()
        if operator:
            headers['OPERATOR'] = operator
        if self.settings_manager.get_option('operator_name', ''):
            headers['MY_NAME'] = self.settings_manager.get_option('operator_name', '')
        if self.settings_manager.get_option('my_qth', ''):
            headers['MY_QTH'] = self.settings_manager.get_option('my_qth', '')
        if self.settings_manager.get_option('my_city', ''):
            headers['MY_CITY'] = self.settings_manager.get_option('my_city', '')
        if self.settings_manager.get_option('my_rig', ''):
            headers['MY_RIG'] = self.settings_manager.get_option('my_rig', '')
        if self.settings_manager.get_option('my_lat', ''):
            headers['MY_LAT'] = self.settings_manager.get_option('my_lat', '')
        if self.settings_manager.get_option('my_lon', ''):
            headers['MY_LON'] = self.settings_manager.get_option('my_lon', '')

        try:
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(f"#   Created:  {datetime.now().strftime('%d-%m-%Y  %H:%M:%S')}\n")
                file.write(adif_io.headers_to_adif(headers))
                for qso_record in qso_records:
                    file.write(adif_io.qso_to_adif(qso_record))

            try:
                if hasattr(self.qso_manager, 'auto_temp') and self.qso_manager.auto_temp:
                    self.qso_manager.clear_temp()
            except Exception as e:
                log_error(f"Failed to clear temp after export: {e}")
            log_user_action("ADIF export completed successfully")
            return Result(True, data=tr("success.export"))
        except Exception as e:
            log_error(f"ADIF export error: {e}")
            return Result(False, error=tr("error.export").format(error=e))
