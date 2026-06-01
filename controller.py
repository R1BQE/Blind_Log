"""
Application Controller — контроллер приложения.

Отделяет GUI от бизнес-логики. Принимает вызовы от GUI, обрабатывает ошибки,
вызывает QSOManager и возвращает результаты/ошибки в GUI.

Это средний слой архитектуры:
  GUI -> Controller -> QSOManager
"""

import threading
import logger
import wx
from datetime import datetime, timedelta
from utils import Result
from logger import log_user_action, log_ui_state, log_feedback, log_error
from i18n import tr as _


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
    
    def show_settings_dialog(self, settings_manager):
        """Открыть диалог настроек через UI."""
        raise NotImplementedError
    
    def confirm(self, message, title, style=wx.YES_NO | wx.ICON_QUESTION):
        """Запросить подтверждение пользователя через диалог."""
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
        try:
            log_error(f"{title}: {message}")
        except NameError:
            # Fallback if logging not available
            pass
    
    def _notify_success(self, message):
        """Helper для показа успешных сообщений."""
        if self.gui_bridge:
            self.gui_bridge.show_notification(message)
        # log_feedback убираем - он уже вызывается в nvda_notify

    def _run_in_ui_thread(self, func, *args, **kwargs):
        """Run callback in UI thread if GUI bridge supports it."""
        if self.gui_bridge and hasattr(self.gui_bridge, 'run_in_ui_thread'):
            try:
                self.gui_bridge.run_in_ui_thread(func, *args, **kwargs)
                return
            except Exception as e:
                log_error(f"Failed to schedule UI callback: {e}")
        func(*args, **kwargs)

    def open_settings_dialog(self):
        """Open settings dialog through GUI bridge and reload settings."""
        if not self.gui_bridge:
            return False
        try:
            dialog_result = self.gui_bridge.show_settings_dialog(self.settings_manager)
            if dialog_result:
                self.settings_manager.load_settings()
                self.reload_settings()
                return True
        except Exception as e:
            log_error(f"Failed to open settings dialog: {e}")
        return False

    def import_adif_file(self, filepath):
        """Import ADIF from file and replace current QSO list."""
        try:
            from importer import import_adif_file
            result = import_adif_file(filepath)
            if not result.success:
                return result

            qsos = result.data.get('qsos', []) if result.data else []
            self.qso_manager.set_qso_list(qsos)
            if self.gui_bridge:
                self.gui_bridge.update_journal_display()
            return Result(True, data=result.data)
        except Exception as e:
            error_msg = f"Failed to import ADIF: {e}"
            log_error(error_msg)
            return Result(False, error=error_msg)

    def _handle_qrz_result(self, result, callsign):
        """Обработать результат QRZ в UI-потоке."""
        if result.success:
            self._notify_success(_("qrz_data_loaded").format(callsign=callsign))
            if self.gui_bridge:
                if 'name' in result.data:
                    self.gui_bridge.set_control_value('name', result.data['name'])
                if 'city' in result.data:
                    self.gui_bridge.set_control_value('city', result.data['city'])
        else:
            self._notify_error(_("qrz_error"), result.error or _("qrz_load_failed"))

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
            log_error(f"Error reading QSO from GUI: {e}")
            return {}
    
    def add_qso_from_gui(self):
        """
        Добавить QSO, прочитав данные из UI контролов.
        
        Returns:
            (success: bool, message: str)
        """
        log_user_action("Add QSO from form")
        try:
            qso_data = self._read_qso_from_gui()
            result = self.qso_manager.add_qso(qso_data)
            
            if result.success:
                if self.gui_bridge:
                    try:
                        self.gui_bridge.clear_form()
                        self.gui_bridge.update_journal_display()
                        self.gui_bridge.set_focus('call')
                        self._notify_success(_("qso_added"))
                    except Exception as e:
                        log_error(f"UI update error after adding QSO: {e}")
                        # QSO добавлен, но UI не синхронизирован - критическая ошибка
                        self._notify_error(_("error.title"), _("ui_update_error"))
                else:
                    self._notify_success(_("qso_added"))
            else:
                self._notify_error(_("input_error"), result.error)
            
            return result
        except Exception as e:
            error_msg = f"QSO addition error: {str(e)}"
            self._notify_error("Critical error", error_msg)
            log_error(f"Exception in add_qso_from_gui: {e}")
            return Result(False, error=error_msg)
    
    def edit_qso_from_gui(self, index):
        """
        Редактировать QSO по индексу, используя данные из UI.
        
        Args:
            index: индекс QSO в списке
            
        Returns:
            (success: bool, message: str)
        """
        log_user_action(f"Edit QSO index {index}")
        try:
            if index < 0 or index >= self.qso_manager.get_qso_count():
                error_msg = _("select_record")
                self._notify_error(_("error.title"), error_msg)
                return Result(False, error=error_msg)
            
            qso_data = self._read_qso_from_gui()
            result = self.qso_manager.edit_qso(index, qso_data)
            
            if result.success:
                self._notify_success(_("qso_updated"))
                if self.gui_bridge:
                    try:
                        self.gui_bridge.clear_form()
                        self.gui_bridge.update_journal_display()
                        self.gui_bridge.set_focus('call')
                    except Exception as e:
                        log_error(f"UI update error after editing QSO: {e}")
                        self._notify_error(_("error.title"), _("ui_update_error"))
            else:
                self._notify_error(_("input_error"), result.error)
            
            return result
        except Exception as e:
            error_msg = f"QSO editing error: {str(e)}"
            self._notify_error("Critical error", error_msg)
            log_error(f"Exception in edit_qso_from_gui: {e}")
            return Result(False, error=error_msg)
    
    def delete_qso(self, index):
        """
        Удалить QSO.
        
        Args:
            index: индекс QSO в списке
            
        Returns:
            (success: bool, message: str)
        """
        log_user_action(f"Delete QSO index {index}")
        try:
            if index < 0 or index >= self.qso_manager.get_qso_count():
                error_msg = "Select record to delete"
                self._notify_error("Error", error_msg)
                return Result(False, error=error_msg)
            
            result = self.qso_manager.delete_qso(index)
            
            if result.success:
                self._notify_success(_("qso_deleted"))
                if self.gui_bridge:
                    try:
                        self.gui_bridge.update_journal_display()
                    except Exception as e:
                        log_error(f"UI update error after deleting QSO: {e}")
                        self._notify_error(_("error.title"), _("ui_update_error"))
            else:
                self._notify_error(_("error.title"), result.error)
            
            return result
        except Exception as e:
            error_msg = f"QSO deletion error: {str(e)}"
            self._notify_error("Critical error", error_msg)
            log_error(f"Exception in delete_qso: {e}")
            return Result(False, error=error_msg)
    
    def load_qso_for_edit(self, index):
        """
        Загрузить QSO для редактирования в UI.
        
        Args:
            index: индекс QSO в списке
        """
        log_ui_state("Switched to QSO editing mode")
        try:
            if index < 0 or index >= self.qso_manager.get_qso_count():
                self._notify_error("Error", "Select record to edit")
                return False
            
            qso = self.qso_manager.get_qso_by_index(index)
            if qso is None:
                self._notify_error("Error", "Select record to edit")
                return False
            if self.gui_bridge:
                self.gui_bridge.switch_tab(0)  # Переключиться на вкладку "Добавить"
                self.gui_bridge.populate_form(qso)
                self.gui_bridge.set_focus('call')
            
            begin_result = self.qso_manager.begin_edit(index)
            if not begin_result.success:
                self._notify_error("Error", begin_result.error)
                return False
            return True
        except Exception as e:
            log_error(f"Error loading QSO for edit: {e}")
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
            return Result(False, data={}, error="Enter callsign")

        callsign = callsign.strip().upper()

        if not self.qso_manager.qrz_lookup:
            return Result(False, data={}, error="Поиск по QRZ.ru отключён или не настроен")

        def worker():
            try:
                if not self.qso_manager.qrz_lookup.session_key:
                    login_result = self.qso_manager.ensure_qrz_logged_in()
                    if not login_result.success:
                        self._run_in_ui_thread(self._notify_error, "Ошибка авторизации QRZ", login_result.error or "Не удалось авторизоваться на QRZ.ru")
                        return

                result = self.qso_manager.lookup_callsign(callsign)
                self._run_in_ui_thread(self._handle_qrz_result, result, callsign)
            except Exception as e:
                logger.exception("Exception in background QRZ lookup")
                self._run_in_ui_thread(self._notify_error, "Ошибка поиска", f"Ошибка при поиске позывного: {e}")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return Result(True, data={}, error=None)
    
    def get_qso_list(self):
        """Получить список всех QSO."""
        return self.qso_manager.get_qso_list()
    
    def get_default_datetime_components(self):
        """Получить текущие дату и время для заполнения формы QSO."""
        try:
            return self.qso_manager.get_current_datetime_components()
        except Exception as e:
            log_error(f"Error getting default datetime components: {e}")
            return ('', '')
    
    def get_qso_by_index(self, index):
        """Получить QSO по индексу."""
        try:
            return self.qso_manager.get_qso_by_index(index)
        except Exception as e:
            log_error(f"Error getting QSO by index: {e}")
            return None
    
    def reload_settings(self):
        """Перезагрузить настройки."""
        try:
            self.qso_manager.reload_settings()
            self._notify_success(_("settings_reloaded"))
        except Exception as e:
            error_msg = f"{_('settings_load_error')}: {str(e)}"
            self._notify_error(_("error.title"), error_msg)
            logger.exception("Exception in reload_settings")
