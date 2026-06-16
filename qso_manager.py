"""
QSO Manager — управление данными записей QSO (радиосвязей).

Отвечает за:
- Хранение и управление списком QSO
- Валидацию данных QSO
- Сохранение/загрузку temp-файлов
- Поиск по QRZ.ru

Не зависит от UI (wx). Все результаты возвращаются в виде (success, message) или exceptions.
"""

import os
import json
from datetime import datetime, timedelta
from qrz_lookup import QRZLookup
from transliterator import transliterate_russian
from utils import get_app_path, Result
from i18n import tr as _
from logger import log_user_action, log_error, log_debug


class QSOManager:
    """
    Менеджер записей QSO (радиосвязей).
    
    Управляет списком QSO, валидацией данных и сохранением/загрузкой.
    НЕ зависит от UI (wx).
    """
    
    def __init__(self, settings_manager=None):
        """
        Args:
            settings_manager: SettingsManager instance
        """
        if settings_manager is None:
            raise ValueError("SettingsManager not passed to QSOManager")
        
        self.settings_manager = settings_manager
        self.qso_list = []
        self.editing_index = None
        
        # автосохранение сеанса
        self.auto_temp = self.settings_manager.get_option('auto_temp', '0') == '1'
        # транслитерация русского текста (управляется настройкой)
        self.transliterate_enabled = self.settings_manager.get_bool('transliterate_russian')
        base = os.path.join(get_app_path(), '')
        self.temp_file = os.path.join(base, 'blind_log_temp.json')
        
        # QRZ lookup инициализируется без UI
        self._init_qrz_lookup_silent()
    
    def _init_qrz_lookup_silent(self):
        """Инициализирует QRZ lookup без UI сообщений об ошибках."""
        qrz_username = self.settings_manager.get_option("qrz_username", "")
        qrz_password = self.settings_manager.get_option("qrz_password", "")
        use_qrz = self.settings_manager.get_bool("use_qrz_lookup")
        
        self.qrz_lookup = None
        if use_qrz and qrz_username and qrz_password:
            try:
                self.qrz_lookup = QRZLookup(qrz_username, qrz_password)
            except Exception as e:
                log_error(f"QRZ initialization error: {e}")
                self.qrz_lookup = None

    def ensure_qrz_logged_in(self):
        """Выполнить авторизацию на QRZ.ru в фоновом потоке, если нужно."""
        if not self.qrz_lookup:
            return Result(False, data={}, error=_("error.qrz_disabled"))
        if self.qrz_lookup.session_key:
            return Result(True, data=self.qrz_lookup.session_key)
        try:
            return self.qrz_lookup.login()
        except Exception as e:
            error_msg = f"QRZ.ru authorization error: {e}"
            log_error(error_msg)
            return Result(False, data={}, error=error_msg)

    def _transliterate_or_passthrough(self, value):
        """Применить транслитерацию, если она включена в настройках; иначе вернуть значение как есть."""
        if not value:
            return value
        if self.transliterate_enabled:
            return transliterate_russian(value)
        return value

    def _normalize_qso(self, qso_data):
        """Привести произвольный dict с QSO-полями к каноническому внутреннему виду.
        Используется и при ручном добавлении, и при импорте из ADIF.
        Не выполняет валидацию — только нормализацию формата и опциональную транслитерацию.
        """
        freq = (qso_data.get('freq', '') or '').strip()
        return {
            'call': (qso_data.get('call', '') or '').strip().upper(),
            'name': self._transliterate_or_passthrough((qso_data.get('name', '') or '').strip().title()),
            'city': self._transliterate_or_passthrough((qso_data.get('city', '') or '').strip().title()),
            'qth': (qso_data.get('qth', '') or '').strip().upper(),
            'band': (qso_data.get('band', '') or '').strip(),
            'mode': (qso_data.get('mode', '') or '').strip(),
            'freq': freq.replace(',', '.') if freq else '',
            'rst_received': (qso_data.get('rst_received', '') or '').strip(),
            'rst_sent': (qso_data.get('rst_sent', '') or '').strip(),
            'comment': self._transliterate_or_passthrough((qso_data.get('comment', '') or '').strip()),
            'datetime': (qso_data.get('datetime', '') or '').strip(),
        }

    def add_qso(self, qso_data):
        """
        Добавить новое QSO.

        Args:
            qso_data: dict с полями QSO {
                'call': str (обязательно),
                'name': str,
                'city': str,
                'qth': str,
                'band': str,
                'mode': str,
                'freq': str,
                'rst_received': str,
                'rst_sent': str,
                'comment': str,
                'datetime': str,
            }

        Returns:
            Result: unified operation result with success, data and error fields.
        """
        try:
            # Валидация
            call = qso_data.get('call', '').strip().upper()
            if not call:
                log_error("Validation error: callsign not filled")
                return Result(False, error=_("error.callsign_required"))

            # Валидация freq
            freq = qso_data.get('freq', '').strip()
            if freq:
                try:
                    float(freq.replace(",", "."))
                except ValueError:
                    log_error("Validation error: invalid frequency")
                    return Result(False, error=_("error.frequency_number"))

            # Валидация RST
            rst_received = qso_data.get('rst_received', '').strip()
            rst_sent = qso_data.get('rst_sent', '').strip()
            if rst_received and not rst_received.isdigit():
                log_error("Validation error: received RST is not a number")
                return Result(False, error=_("error.rst_received_digits"))
            if rst_sent and not rst_sent.isdigit():
                log_error("Validation error: sent RST is not a number")
                return Result(False, error=_("error.rst_sent_digits"))

            # Подготовка данных через общий нормализатор
            datetime_value = qso_data.get('datetime')
            if not datetime_value:
                datetime_value = self._get_current_datetime_str()

            normalized = dict(qso_data)
            normalized['call'] = call
            normalized['datetime'] = datetime_value
            processed_data = self._normalize_qso(normalized)
            # _normalize_qso транслитерирует только при включённой настройке;
            # если настройка выключена, передаём оригиналы (но всё равно прогоняем
            # через .title() и .strip() внутри _normalize_qso).
            if not self.transliterate_enabled:
                processed_data['name'] = (qso_data.get('name', '') or '').strip().title()
                processed_data['city'] = (qso_data.get('city', '') or '').strip().title()
                processed_data['comment'] = (qso_data.get('comment', '') or '').strip()
            
            # Добавить или обновить
            if self.editing_index is not None:
                self.qso_list[self.editing_index] = processed_data
                self.editing_index = None
                log_user_action(f"QSO edited: {call}")
            else:
                self.qso_list.append(processed_data)
                log_user_action(f"QSO added: {call}")
            
            # Автосохранение temp
            if self.auto_temp:
                self.save_temp()
            
            return Result(True, data=processed_data)
        
        except Exception as e:
            error_msg = f"QSO addition error: {str(e)}"
            log_error(error_msg)
            return Result(False, error=error_msg)
    
    def edit_qso(self, index, qso_data):
        """
        Редактировать существующее QSO.
        
        Args:
            index: индекс QSO в списке
            qso_data: dict с новыми полями
        
        Returns:
            Result: unified operation result with success, data and error fields.
        """
        result = None
        try:
            if index < 0 or index >= len(self.qso_list):
                return Result(False, error=_("error.invalid_qso_index"))
            
            self.editing_index = index
            result = self.add_qso(qso_data)
            return result
        except Exception as e:
            error_msg = f"QSO editing error: {str(e)}"
            log_error(error_msg)
            return Result(False, error=error_msg)
        finally:
            if result is None or not result.success:
                self.editing_index = None
    
    def delete_qso(self, index):
        """
        Удалить QSO по индексу.
        
        Args:
            index: индекс QSO в списке
        
        Returns:
            Result: unified operation result with success, data and error fields.
        """
        try:
            if index < 0 or index >= len(self.qso_list):
                return Result(False, error=_("error.invalid_qso_index"))
            
            deleted_qso = self.qso_list.pop(index)
            
            if self.auto_temp:
                self.save_temp()
            
            log_user_action(f"QSO deleted: {deleted_qso['call']}")
            return Result(True, data=deleted_qso)
        
        except Exception as e:
            error_msg = f"QSO deletion error: {str(e)}"
            log_error(error_msg)
            return Result(False, error=error_msg)
    
    def get_qso(self, index):
        """Получить QSO по индексу."""
        try:
            if 0 <= index < len(self.qso_list):
                return self.qso_list[index].copy()
            return None
        except Exception:
            return None

    def get_qso_by_index(self, index):
        """Получить QSO по индексу (alias)."""
        return self.get_qso(index)

    def get_qso_list(self):
        """Получить полный список QSO."""
        return [qso.copy() for qso in self.qso_list]

    def get_qso_count(self):
        """Получить количество записей QSO."""
        return len(self.qso_list)

    def begin_edit(self, index):
        """Установить индекс редактирования перед изменением записи."""
        if 0 <= index < len(self.qso_list):
            self.editing_index = index
            return Result(True)
        return Result(False, error=_("error.invalid_qso_index"))

    def lookup_callsign(self, callsign):
        """
        Поискать информацию по позывному через QRZ.ru.
        
        Args:
            callsign: позывной (CALL)
        
        Returns:
            Result: unified operation result with success, data and error fields.
        """
        try:
            if not callsign or not callsign.strip():
                return Result(False, data={}, error=_("error.enter_callsign"))
            
            callsign = callsign.strip().upper()
            
            if not self.qrz_lookup:
                return Result(False, data={}, error=_("error.qrz_disabled"))
            
            result = self.qrz_lookup.lookup_call(callsign)
            if result.success:
                log_user_action(f"QRZ: Data found for {callsign}")
                return Result(True, data=result.data)
            else:
                log_user_action(f"QRZ: Callsign {callsign} not found")
                return Result(False, data={}, error=result.error)
        
        except Exception as e:
            error_msg = f"Callsign search error: {str(e)}"
            log_error(error_msg)
            return Result(False, data={}, error=error_msg)
    
    def save_temp(self):
        """Сохранить текущий список QSO в temp-файл для восстановления сессии."""
        try:
            with open(self.temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.qso_list, f, ensure_ascii=False)
            log_debug(f"Temp file saved: {self.temp_file}")
        except Exception as e:
            log_error(f"Temp save error: {e}")
    
    def load_temp(self):
        """Загрузить QSO из temp-файла.

        Returns:
            list: восстановленные QSO, если temp-файл существует и корректен.
            None: если temp-файл не найден или не удалось прочитать.
        """
        if not os.path.exists(self.temp_file):
            return None
        try:
            with open(self.temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                log_debug(f"Temp file loaded: {len(data)} QSO")
                return data
        except Exception as e:
            log_error(f"Temp file loading error: {e}")
            return None
    
    def clear_temp(self):
        """Удалить temp-файл."""
        if os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
                log_debug(f"Temp file deleted: {self.temp_file}")
            except Exception as e:
                log_error(f"Temp deletion error: {e}")
    
    def _get_timezone_offset(self):
        """Получить смещение часового пояса в часах."""
        timezone = self.settings_manager.get_option('timezone', 'UTC')
        if timezone == 'UTC':
            return 0
        try:
            return int(self.settings_manager.get_option('custom_timezone', '0'))
        except (ValueError, TypeError):
            log_debug("Incorrect timezone value. Using UTC.")
            return 0
    
    def _get_current_time_with_timezone(self):
        """Получить текущее время с учётом часового пояса."""
        offset = self._get_timezone_offset()
        return datetime.utcnow() + timedelta(hours=offset)
    
    def _get_current_datetime_str(self):
        """Получить текущую дату/время в виде строки (YYYY-MM-DD HH:MM:SS)."""
        now = self._get_current_time_with_timezone()
        return now.strftime('%Y-%m-%d %H:%M:%S')

    def get_current_datetime_components(self):
        """Вернуть текущие дату и время с учётом настроек часового пояса."""
        now = self._get_current_time_with_timezone()
        return now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S')

    def set_qso_list(self, qso_list):
        """Установить список QSO, например при восстановлении из temp-файла."""
        if isinstance(qso_list, list):
            self.qso_list = qso_list
            if self.auto_temp:
                self.save_temp()
        else:
            raise ValueError("qso_list must be a list")

    def import_qso_list(self, qsos, mode='replace'):
        """Импортировать список QSO в журнал.

        Args:
            qsos: iterable of dicts в каноническом внутреннем формате
                  (call, name, city, qth, band, mode, freq, rst_received, rst_sent, comment, datetime).
            mode: 'replace' — заменить весь журнал;
                  'append'  — добавить к существующему (с дедупликацией по (call, datetime)).

        Returns:
            Result: success, data={'imported': int, 'skipped': int, 'total': int}, error.
        """
        try:
            if mode not in ('replace', 'append'):
                return Result(False, error=_("error.unknown_import_mode"))

            # Дедупликация при append: ключ — (call, datetime).
            existing_keys = set()
            if mode == 'append':
                for q in self.qso_list:
                    existing_keys.add((q.get('call', ''), q.get('datetime', '')))

            new_list = [] if mode == 'replace' else list(self.qso_list)
            imported = 0
            skipped = 0
            for raw in qsos:
                if not isinstance(raw, dict):
                    skipped += 1
                    continue
                if not raw.get('call'):
                    skipped += 1
                    continue
                normalized = self._normalize_qso(raw)
                key = (normalized['call'], normalized['datetime'])
                if mode == 'append' and key in existing_keys:
                    skipped += 1
                    continue
                new_list.append(normalized)
                if mode == 'append':
                    existing_keys.add(key)
                imported += 1

            self.qso_list = new_list
            if self.auto_temp:
                self.save_temp()
            log_user_action(f"ADIF import: mode={mode}, imported={imported}, skipped={skipped}")
            return Result(True, data={'imported': imported, 'skipped': skipped, 'total': imported + skipped})
        except Exception as e:
            error_msg = f"QSO import error: {str(e)}"
            log_error(error_msg)
            return Result(False, error=error_msg)
    
    def reload_settings(self):
        """Перезагрузить настройки из settings_manager."""
        # Обновить auto_temp
        self.auto_temp = self.settings_manager.get_bool('auto_temp')
        # Обновить флаг транслитерации
        self.transliterate_enabled = self.settings_manager.get_bool('transliterate_russian')
        # Обновить QRZ lookup если нужно
        if self.settings_manager.get_bool('use_qrz_lookup'):
            username = self.settings_manager.get_option('qrz_username', '')
            password = self.settings_manager.get_option('qrz_password', '')
            if username and password:
                self.qrz_lookup = QRZLookup(username, password)
            else:
                self.qrz_lookup = None
        else:
            self.qrz_lookup = None
