"""
Application Controller — контроллер приложения.

Отделяет GUI от бизнес-логики. Принимает вызовы от GUI, обрабатывает ошибки,
вызывает QSOManager и возвращает результаты/ошибки в GUI.

Это средний слой архитектуры:
  GUI -> Controller -> QSOManager
"""

from logger import log_error
from localization.i18n import tr as _
from services.qrz_lookup import QRZLookupService
from controller.imports import ControllerImportMixin
from controller.qso_actions import ControllerQSOActionsMixin
from controller.draft import ControllerDraftMixin
from controller.export import ControllerExportMixin


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
    
    def confirm(self, message, title, style=None):
        """Запросить подтверждение пользователя через диалог."""
        raise NotImplementedError

    def run_in_ui_thread(self, func, *args, **kwargs):
        """Выполнить callback в UI-потоке реализации GUI."""
        raise NotImplementedError


class ApplicationController(ControllerQSOActionsMixin, ControllerImportMixin, ControllerDraftMixin, ControllerExportMixin):
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
        self.qrz_service = QRZLookupService(
            settings_manager,
            gui_bridge=gui_bridge,
            run_in_ui_thread=self._run_in_ui_thread,
            notify_success=self._notify_success,
            notify_error=self._notify_error,
        )
    
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
        """Schedule a callback on the UI thread without unsafe cross-thread fallback.

        In headless/controller-only use there is no GUI thread to protect, so the
        callback can run directly. Once a GUI bridge exists, a failed or missing
        dispatcher must never cause a worker thread to touch GUI controls.
        """
        if self.gui_bridge is None:
            func(*args, **kwargs)
            return True

        dispatcher = getattr(self.gui_bridge, 'run_in_ui_thread', None)
        if not callable(dispatcher):
            log_error("Cannot schedule UI callback: GUI bridge has no UI-thread dispatcher")
            return False

        try:
            dispatcher(func, *args, **kwargs)
            return True
        except Exception as e:
            log_error(f"Failed to schedule UI callback: {e}")
            return False

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

    def lookup_callsign(self, callsign):
        """Delegate callsign lookup to the QRZ subsystem."""
        return self.qrz_service.lookup_callsign(callsign)

    def undo_last_change(self):
        """Undo the most recent successful QSO addition, edit, or deletion."""
        try:
            return self.qso_manager.undo_last_change()
        except Exception as error:
            log_error(f"Journal undo error: {error}")
            from common.utils import Result
            return Result(False, error=str(error))

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
            return self.qso_manager.get_qso(index)
        except Exception as e:
            log_error(f"Error getting QSO by index: {e}")
            return None
    
    def reload_settings(self):
        """Перезагрузить настройки."""
        try:
            self.qso_manager.reload_settings()
            self.qrz_service.reload_settings()
            self._notify_success(_("settings_reloaded"))
        except Exception as e:
            error_msg = f"{_('settings_load_error')}: {str(e)}"
            self._notify_error(_("error.title"), error_msg)
            log_error(f"Exception in reload_settings: {e}")
