"""
QSO Manager — управление данными записей QSO (радиосвязей).

Отвечает за:
- Хранение и управление списком QSO
- Валидацию данных QSO
- Сохранение/загрузку temp-файлов
- Поиск по QRZ.ru

Не зависит от UI (wx). Все результаты возвращаются в виде (success, message) или exceptions.
"""

import logging
import os
import json
from datetime import datetime, timedelta
from qrz_lookup import QRZLookup
from transliterator import transliterate_russian
from utils import get_app_path, Result

logger = logging.getLogger(__name__)


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
            raise ValueError("SettingsManager не передан в QSOManager")
        
        self.settings_manager = settings_manager
        self.qso_list = []
        self.editing_index = None
        
        # автосохранение сеанса
        self.auto_temp = self.settings_manager.get_option('auto_temp', '0') == '1'
        base = os.path.join(get_app_path(), '')
        self.temp_file = os.path.join(base, 'blind_log_temp.json')
        
        # QRZ lookup инициализируется без UI
        self._init_qrz_lookup_silent()
    
    def _init_qrz_lookup_silent(self):
        """Инициализирует QRZ lookup без UI сообщений об ошибках."""
        qrz_username = self.settings_manager.settings.get("qrz_username", "")
        qrz_password = self.settings_manager.settings.get("qrz_password", "")
        use_qrz = self.settings_manager.settings.get("use_qrz_lookup", '1') == '1'
        
        self.qrz_lookup = None
        if use_qrz and qrz_username and qrz_password:
            try:
                self.qrz_lookup = QRZLookup(qrz_username, qrz_password)
            except Exception as e:
                logger.error(f"Ошибка инициализации QRZ: {e}")
                self.qrz_lookup = None

    def ensure_qrz_logged_in(self):
        """Выполнить авторизацию на QRZ.ru в фоновом потоке, если нужно."""
        if not self.qrz_lookup:
            return Result(False, data={}, error="Поиск по QRZ.ru отключён в настройках")
        if self.qrz_lookup.session_key:
            return Result(True, data=self.qrz_lookup.session_key)
        try:
            return self.qrz_lookup.login()
        except Exception as e:
            error_msg = f"Ошибка авторизации на QRZ.ru: {e}"
            logger.error(error_msg)
            return Result(False, data={}, error=error_msg)

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
                return Result(False, error="Заполните обязательное поле: Позывной")
            
            # Подготовка данных
            datetime_value = qso_data.get('datetime')
            if not datetime_value:
                datetime_value = self._get_current_datetime_str()

            processed_data = {
                'call': call,
                'name': transliterate_russian(qso_data.get('name', '').strip().title()),
                'city': transliterate_russian(qso_data.get('city', '').strip().title()),
                'qth': qso_data.get('qth', '').strip().upper(),
                'band': qso_data.get('band', '').strip(),
                'mode': qso_data.get('mode', '').strip(),
                'freq': qso_data.get('freq', '').strip().replace(",", "."),
                'rst_received': qso_data.get('rst_received', '').strip(),
                'rst_sent': qso_data.get('rst_sent', '').strip(),
                'comment': transliterate_russian(qso_data.get('comment', '').strip()),
                'datetime': datetime_value,
            }
            
            # Добавить или обновить
            if self.editing_index is not None:
                self.qso_list[self.editing_index] = processed_data
                self.editing_index = None
            else:
                self.qso_list.append(processed_data)
            
            # Автосохранение temp
            if self.auto_temp:
                self.save_temp()
            
            logger.info(f"QSO добавлено: {call}")
            return Result(True, data=processed_data)
        
        except Exception as e:
            error_msg = f"Ошибка при добавлении QSO: {str(e)}"
            logger.error(error_msg)
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
                return Result(False, error="Неверный индекс QSO")
            
            self.editing_index = index
            result = self.add_qso(qso_data)
            return result
        except Exception as e:
            error_msg = f"Ошибка при редактировании QSO: {str(e)}"
            logger.error(error_msg)
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
                return Result(False, error="Неверный индекс QSO")
            
            deleted_qso = self.qso_list.pop(index)
            
            if self.auto_temp:
                self.save_temp()
            
            logger.info(f"QSO удалено: индекс {index}")
            return Result(True, data=deleted_qso)
        
        except Exception as e:
            error_msg = f"Ошибка при удалении QSO: {str(e)}"
            logger.error(error_msg)
            return Result(False, error=error_msg)
    
    def get_qso(self, index):
        """Получить QSO по индексу."""
        try:
            if 0 <= index < len(self.qso_list):
                return self.qso_list[index]
            return None
        except Exception:
            return None
    
    def get_qso_list(self):
        """Получить полный список QSO."""
        return self.qso_list
    
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
                return Result(False, data={}, error="Введите позывной")
            
            callsign = callsign.strip().upper()
            
            if not self.qrz_lookup:
                return Result(False, data={}, error="Поиск по QRZ.ru отключён в настройках")
            
            result = self.qrz_lookup.lookup_call(callsign)
            if result.success:
                logger.info(f"QRZ: Данные найдены для {callsign}")
                return Result(True, data=result.data)
            else:
                logger.info(f"QRZ: Позывной {callsign} не найден")
                return Result(False, data={}, error=result.error)
        
        except Exception as e:
            error_msg = f"Ошибка при поиске позывного: {str(e)}"
            logger.error(error_msg)
            return Result(False, data={}, error=error_msg)
    
    def save_temp(self):
        """Сохранить текущий список QSO в temp-файл для восстановления сессии."""
        try:
            with open(self.temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.qso_list, f, ensure_ascii=False)
            logger.debug(f"Temp файл сохранён: {self.temp_file}")
        except Exception as e:
            logger.error(f"Ошибка сохранения temp: {e}")
    
    def load_temp(self):
        """Загрузить QSO из temp-файла."""
        if not os.path.exists(self.temp_file):
            return None
        try:
            with open(self.temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"Temp файл загружен: {len(data)} QSO")
                return data
        except Exception as e:
            logger.error(f"Ошибка загрузки temp: {e}")
            return None
    
    def clear_temp(self):
        """Удалить temp-файл."""
        if os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
                logger.debug(f"Temp файл удалён: {self.temp_file}")
            except Exception as e:
                logger.error(f"Ошибка удаления temp: {e}")
    
    def _get_timezone_offset(self):
        """Получить смещение часового пояса в часах."""
        timezone = self.settings_manager.settings.get('timezone', 'UTC')
        if timezone == 'UTC':
            return 0
        try:
            return int(self.settings_manager.settings.get('custom_timezone', '0'))
        except (ValueError, TypeError):
            logger.warning("Некорректное значение часового пояса. Используется UTC.")
            return 0
    
    def _get_current_time_with_timezone(self):
        """Получить текущее время с учётом часового пояса."""
        offset = self._get_timezone_offset()
        return datetime.utcnow() + timedelta(hours=offset)
    
    def _get_current_datetime_str(self):
        """Получить текущую дату/время в виде строки (YYYY-MM-DD HH:MM)."""
        now = self._get_current_time_with_timezone()
        return now.strftime('%Y-%m-%d %H:%M')
