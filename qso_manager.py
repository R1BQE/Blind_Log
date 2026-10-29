"""
QSO Manager — управление данными записей QSO (радиосвязей).

Отвечает за:
- Хранение и управление списком QSO
- Валидацию данных QSO
- Сохранение/загрузку temp-файлов

Не зависит от UI (wx). Все результаты возвращаются в виде (success, message) или exceptions.
"""

import os
import json
from datetime import datetime, timedelta, timezone
from transliterator import transliterate_russian
from utils import get_app_path, get_data_dir, Result
from journal_storage import JournalDatabase
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
        data_dir = get_data_dir()
        self.database_path = os.path.join(data_dir, "blind_log.db")
        self.draft_file = os.path.join(data_dir, "qso_draft.json")
        self._journal_db = JournalDatabase(self.database_path)
        stored_qsos = self._journal_db.get_all()
        self._qso_list = self._sort_qsos(stored_qsos)
        if self._qso_list != stored_qsos:
            self._journal_db.replace_all(self._qso_list)
        self.editing_index = None

        # Keep the legacy path for one-time migration; new journal data is stored in SQLite.
        self.auto_temp = self.settings_manager.get_bool('auto_temp')
        self.transliterate_enabled = self.settings_manager.get_bool('transliterate_russian')
        self.temp_file = os.path.join(get_app_path(), 'blind_log_temp.json')
        self._migrate_legacy_temp()
        
    
    @property
    def qso_list(self):
        return self._qso_list

    @qso_list.setter
    def qso_list(self, values):
        values = self._sort_qsos(list(values))
        previous = getattr(self, "_qso_list", None)
        self._qso_list = values
        database = getattr(self, "_journal_db", None)
        if database is not None:
            try:
                database.replace_all(values)
            except Exception:
                self._qso_list = previous if previous is not None else []
                raise

    @staticmethod
    def _qso_datetime_key(qso):
        """Return a sortable datetime; invalid or missing dates sort last."""
        raw = str(qso.get("datetime", "") or "").strip()
        if not raw:
            return (False, datetime.min)
        parsed = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                    "%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d"):
            try:
                parsed = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            try:
                parsed = datetime.fromisoformat(raw)
            except (TypeError, ValueError):
                return (False, datetime.min)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return (True, parsed)

    @classmethod
    def _sort_qsos(cls, qsos):
        """Sort newest first and preserve source order for equal timestamps."""
        return sorted(qsos, key=cls._qso_datetime_key, reverse=True)

    def _persist_qsos(self):
        self._journal_db.replace_all(self.qso_list)

    def _migrate_legacy_temp(self):
        """Preserve old temporary QSO records by migrating them to SQLite once."""
        if self.qso_list or not os.path.isfile(self.temp_file):
            return
        try:
            with open(self.temp_file, "r", encoding="utf-8") as stream:
                legacy = json.load(stream)
            if isinstance(legacy, list) and legacy:
                valid = [qso for qso in legacy if isinstance(qso, dict) and qso.get("call")]
                if valid:
                    self.qso_list = [self._normalize_qso(qso) for qso in valid]
                    log_debug(f"Migrated {len(valid)} legacy QSO records into SQLite")
        except Exception as error:
            log_error(f"Legacy journal migration failed; original file preserved: {error}")

    def save_draft(self, fields):
        """Persist the unfinished form independently from saved QSO records."""
        try:
            self._journal_db.save_draft(self.draft_file, {"version": 1, "fields": fields})
            return Result(True)
        except Exception as error:
            log_error(f"QSO draft save error: {error}")
            return Result(False, error=str(error))

    def load_draft(self):
        try:
            return self._journal_db.load_draft(self.draft_file)
        except Exception as error:
            log_error(f"QSO draft load error: {error}")
            return None

    def clear_draft(self):
        try:
            self._journal_db.clear_draft(self.draft_file)
            return Result(True)
        except Exception as error:
            log_error(f"QSO draft clear error: {error}")
            return Result(False, error=str(error))

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
            if rst_received and not rst_received.isalnum():
                log_error("Validation error: received RST is not a number")
                return Result(False, error=_("error.rst_received_digits"))
            if rst_sent and not rst_sent.isalnum():
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
            
            if self.editing_index is not None:
                index = self.editing_index
                updated = list(self.qso_list)
                updated[index] = processed_data
                self.qso_list = updated
                self.editing_index = None
                log_user_action(f"QSO edited: {call}")
            else:
                # New records lead when timestamps are identical.
                self.qso_list = [processed_data, *self.qso_list]
                log_user_action(f"QSO added: {call}")
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
            
            deleted_qso = self.qso_list[index]
            self.qso_list = self.qso_list[:index] + self.qso_list[index + 1:]
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

    def cancel_edit(self):
        """Отменить режим редактирования, сбросив editing_index.
        Данные QSO в списке не изменяются.
        """
        self.editing_index = None

    def save_temp(self):
        """Compatibility method: QSO records are now persisted in SQLite."""
        try:
            self._persist_qsos()
            return Result(True)
        except Exception as e:
            log_error(f"Journal save error: {e}")
            return Result(False, error=str(e))
    
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
        tz_setting = self.settings_manager.get_option('timezone', 'UTC')
        if tz_setting == 'UTC':
            return 0
        try:
            return int(self.settings_manager.get_option('custom_timezone', '0'))
        except (ValueError, TypeError):
            log_debug("Incorrect timezone value. Using UTC.")
            return 0
    
    def _get_current_time_with_timezone(self):
        """Получить текущее время с учётом часового пояса."""
        offset = self._get_timezone_offset()
        return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=offset)
    
    def _get_current_datetime_str(self):
        """Получить текущую дату/время в виде строки (YYYY-MM-DD HH:MM:SS)."""
        now = self._get_current_time_with_timezone()
        return now.strftime('%Y-%m-%d %H:%M:%S')

    def get_current_datetime_components(self):
        """Вернуть текущие дату и время с учётом настроек часового пояса."""
        now = self._get_current_time_with_timezone()
        return now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S')

    def set_qso_list(self, qso_list):
        """Replace the journal atomically, persisting it to SQLite."""
        if not isinstance(qso_list, list):
            raise ValueError("qso_list must be a list")
        self.qso_list = qso_list

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

            if mode == 'replace':
                self._journal_db.create_backup()
            self.qso_list = new_list
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
