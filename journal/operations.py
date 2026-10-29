"""QSO normalization and journal mutation operations."""

from common.transliterator import transliterate_russian
from common.utils import Result
from localization.i18n import tr as _
from logger import log_user_action, log_error


class QSOOperationsMixin:
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
            
            if self.editing_index == index:
                return Result(False, error=_("error.edit_in_progress"))

            deleted_qso = self.qso_list[index]
            self.qso_list = self.qso_list[:index] + self.qso_list[index + 1:]
            if self.editing_index is not None and index < self.editing_index:
                self.editing_index -= 1
            log_user_action(f"QSO deleted: {deleted_qso['call']}")
            return Result(True, data=deleted_qso)
        
        except Exception as e:
            error_msg = f"QSO deletion error: {str(e)}"
            log_error(error_msg)
            return Result(False, error=error_msg)
    
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
            if self.editing_index is not None:
                return Result(False, error=_("error.edit_in_progress"))

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
    
