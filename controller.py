"""
Application Controller — контроллер приложения.

Отделяет GUI от бизнес-логики. Принимает вызовы от GUI, обрабатывает ошибки,
вызывает QSOManager и возвращает результаты/ошибки в GUI.

Это средний слой архитектуры:
  GUI -> Controller -> QSOManager
"""

import logging
import threading
import wx
from datetime import datetime, timedelta
from utils import Result

logger = logging.getLogger(__name__)


class GUIBridge:
    """
    Интерфейс для взаимодействия Controller с GUI.
    GUI реализует этот интерфейс и передаёт экземпляр в Controller.
    """
    
    def show_error(self, title, message):
        """Показать диалог ошибки."""
        raise NotImplementedError
    
    def show_notification(self, message):
        """Показать уведомление (например, через NVDA)."""
        raise NotImplementedError
    
    def switch_tab(self, tab_index):
        """Переключиться на вкладку (0 = Add, 1 = Journal)."""
        raise NotImplementedError
    
    def set_focus(self, control_name):
        """Установить фокус на контрол."""
        raise NotImplementedError
    
    def get_control_value(self, control_name):
        """Получить значение из UI контрола."""
        raise NotImplementedError
    
    def set_control_value(self, control_name, value):
        """Установить значение в UI контрол."""
        raise NotImplementedError
    
    def clear_form(self):
        """Очистить форму добавления QSO."""
        raise NotImplementedError
    
    def populate_form(self, qso_data):
        """Заполнить форму данными QSO для редактирования."""
        raise NotImplementedError
    
    def update_journal_display(self):
        """Обновить отображение журнала."""
        raise NotImplementedError


class ApplicationController:
    """
    Контроллер приложения.
    
    Обрабатывает действия пользователя от GUI и делегирует их QSOManager.
    Обрабатывает исключения и ошибки, вызывает GUI для уведомлений и обновлений.
    """
    
    def __init__(self, qso_manager, settings_manager, gui_bridge=None):
        """
        Args:
            qso_manager: QSOManager instance (без wx зависимостей)
            settings_manager: SettingsManager instance
            gui_bridge: GUIBridge instance (может быть None для тестов)
        """
        self.qso_manager = qso_manager
        self.settings_manager = settings_manager
        self.gui_bridge = gui_bridge
    
    def _notify_error(self, title, message):
        """Helper для показа ошибок."""
        if self.gui_bridge:
            self.gui_bridge.show_error(title, message)
        logger.error(f"{title}: {message}")
    
    def _notify_success(self, message):
        """Helper для показа успешных сообщений."""
        if self.gui_bridge:
            self.gui_bridge.show_notification(message)
        logger.info(message)

    def _handle_qrz_result(self, result, callsign):
        """Обработать результат QRZ в UI-потоке."""
        if result.success:
            self._notify_success(f"Данные для {callsign} загружены из QRZ.ru")
            if self.gui_bridge:
                if 'name' in result.data:
                    self.gui_bridge.set_control_value('name', result.data['name'])
                if 'city' in result.data:
                    self.gui_bridge.set_control_value('city', result.data['city'])
        else:
            self._notify_error("Ошибка QRZ", result.error or "Не удалось получить данные из QRZ.ru")

    def _read_qso_from_gui(self):
        """Прочитать данные QSO из GUI контролов."""
        if not self.gui_bridge:
            return {}
        
        try:
            date_value = self.gui_bridge.get_control_value('date') or ''
            time_value = self.gui_bridge.get_control_value('time') or ''
            if date_value or time_value:
                if not date_value:
                    date_value = datetime.now().strftime('%Y-%m-%d')
                if not time_value:
                    time_value = datetime.now().strftime('%H:%M')
                datetime_value = f"{date_value} {time_value}"
            else:
                datetime_value = self.gui_bridge.get_control_value('datetime') or ''

            return {
                'call': self.gui_bridge.get_control_value('call') or '',
                'name': self.gui_bridge.get_control_value('name') or '',
                'city': self.gui_bridge.get_control_value('city') or '',
                'qth': self.gui_bridge.get_control_value('qth') or '',
                'band': self.gui_bridge.get_control_value('band') or '',
                'mode': self.gui_bridge.get_control_value('mode') or '',
                'freq': self.gui_bridge.get_control_value('freq') or '',
                'rst_received': self.gui_bridge.get_control_value('rst_received') or '',
                'rst_sent': self.gui_bridge.get_control_value('rst_sent') or '',
                'comment': self.gui_bridge.get_control_value('comment') or '',
                'datetime': datetime_value,
            }
        except Exception as e:
            logger.error(f"Error reading QSO from GUI: {e}")
            return {}
    
    def add_qso_from_gui(self):
        """
        Добавить QSO, прочитав данные из UI контролов.
        
        Returns:
            (success: bool, message: str)
        """
        try:
            qso_data = self._read_qso_from_gui()
            result = self.qso_manager.add_qso(qso_data)
            
            if result.success:
                self._notify_success("QSO добавлен в журнал")
                if self.gui_bridge:
                    self.gui_bridge.clear_form()
                    self.gui_bridge.update_journal_display()
                    self.gui_bridge.set_focus('call')
            else:
                self._notify_error("Ошибка ввода", result.error)
            
            return result
        except Exception as e:
            error_msg = f"Ошибка при добавлении QSO: {str(e)}"
            self._notify_error("Критическая ошибка", error_msg)
            logger.exception("Exception in add_qso_from_gui")
            return Result(False, error=error_msg)
    
    def edit_qso_from_gui(self, index):
        """
        Редактировать QSO по индексу, используя данные из UI.
        
        Args:
            index: индекс QSO в списке
            
        Returns:
            (success: bool, message: str)
        """
        try:
            if index < 0 or index >= len(self.qso_manager.qso_list):
                error_msg = "Неверный индекс QSO для редактирования"
                self._notify_error("Ошибка", error_msg)
                return Result(False, error=error_msg)
            
            qso_data = self._read_qso_from_gui()
            result = self.qso_manager.edit_qso(index, qso_data)
            
            if result.success:
                self._notify_success("QSO отредактирован")
                if self.gui_bridge:
                    self.gui_bridge.clear_form()
                    self.gui_bridge.update_journal_display()
                    self.gui_bridge.set_focus('call')
            else:
                self._notify_error("Ошибка ввода", result.error)
            
            return result
        except Exception as e:
            error_msg = f"Ошибка при редактировании QSO: {str(e)}"
            self._notify_error("Критическая ошибка", error_msg)
            logger.exception("Exception in edit_qso_from_gui")
            return Result(False, error=error_msg)
    
    def delete_qso(self, index):
        """
        Удалить QSO.
        
        Args:
            index: индекс QSO в списке
            
        Returns:
            (success: bool, message: str)
        """
        try:
            if index < 0 or index >= len(self.qso_manager.qso_list):
                error_msg = "Выберите запись для удаления"
                self._notify_error("Ошибка", error_msg)
                return Result(False, error=error_msg)
            
            result = self.qso_manager.delete_qso(index)
            
            if result.success:
                self._notify_success("QSO удален из журнала")
                if self.gui_bridge:
                    self.gui_bridge.update_journal_display()
            else:
                self._notify_error("Ошибка", result.error)
            
            return result
        except Exception as e:
            error_msg = f"Ошибка при удалении QSO: {str(e)}"
            self._notify_error("Критическая ошибка", error_msg)
            logger.exception("Exception in delete_qso")
            return Result(False, error=error_msg)
    
    def load_qso_for_edit(self, index):
        """
        Загрузить QSO для редактирования в UI.
        
        Args:
            index: индекс QSO в списке
        """
        try:
            if index < 0 or index >= len(self.qso_manager.qso_list):
                self._notify_error("Ошибка", "Выберите запись для редактирования")
                return False
            
            qso = self.qso_manager.qso_list[index]
            if self.gui_bridge:
                self.gui_bridge.switch_tab(0)  # Переключиться на вкладку "Добавить"
                self.gui_bridge.populate_form(qso)
                self.gui_bridge.set_focus('call')
            
            # Установить индекс редактирования в менеджере
            self.qso_manager.editing_index = index
            return True
        except Exception as e:
            logger.error(f"Error loading QSO for edit: {e}")
            return False
    
    def lookup_callsign(self, callsign):
        """
        Поискать информацию по позывному через QRZ.
        
        Args:
            callsign: позывной (CALL)
            
        Returns:
            Result: если запуск успешен, возвращает Result(True) сразу.
        """
        if not callsign or not callsign.strip():
            return Result(False, data={}, error="Введите позывной")

        callsign = callsign.strip().upper()

        if not self.qso_manager.qrz_lookup:
            return Result(False, data={}, error="Поиск по QRZ.ru отключён или не настроен")

        def worker():
            try:
                if not self.qso_manager.qrz_lookup.session_key:
                    login_result = self.qso_manager.ensure_qrz_logged_in()
                    if not login_result.success:
                        wx.CallAfter(self._notify_error, "Ошибка авторизации QRZ", login_result.error or "Не удалось авторизоваться на QRZ.ru")
                        return

                result = self.qso_manager.lookup_callsign(callsign)
                wx.CallAfter(self._handle_qrz_result, result, callsign)
            except Exception as e:
                logger.exception("Exception in background QRZ lookup")
                wx.CallAfter(self._notify_error, "Ошибка поиска", f"Ошибка при поиске позывного: {e}")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return Result(True, data={}, error=None)
    
    def get_qso_list(self):
        """Получить список всех QSO."""
        return self.qso_manager.qso_list
    
    def get_qso_by_index(self, index):
        """Получить QSO по индексу."""
        try:
            if 0 <= index < len(self.qso_manager.qso_list):
                return self.qso_manager.qso_list[index]
            return None
        except Exception as e:
            logger.error(f"Error getting QSO by index: {e}")
            return None
    
    def reload_settings(self):
        """Перезагрузить настройки."""
        try:
            self.qso_manager.reload_settings()
            self._notify_success("Настройки перезагружены")
        except Exception as e:
            error_msg = f"Ошибка при загрузке настроек: {str(e)}"
            self._notify_error("Ошибка", error_msg)
            logger.exception("Exception in reload_settings")
