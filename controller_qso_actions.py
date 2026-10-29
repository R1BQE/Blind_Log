"""QSO form and journal commands for the application controller."""

from utils import Result
from logger import log_user_action, log_ui_state, log_error
from i18n import tr as _


class ControllerQSOActionsMixin:
    def _read_qso_from_gui(self):
        """Прочитать данные QSO из GUI контролов."""
        if not self.gui_bridge:
            return {}
        
        try:
            date_value = self.gui_bridge.get_control_value('date') or ''
            time_value = self.gui_bridge.get_control_value('time') or ''
            if date_value or time_value:
                if not date_value or not time_value:
                    _now_date, _now_time = self.qso_manager.get_current_datetime_components()
                if not date_value:
                    date_value = _now_date
                if not time_value:
                    time_value = _now_time[:5]  # HH:MM
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
            self._notify_error(_("error.critical"), error_msg)
            log_error(f"Exception in add_qso_from_gui: {e}")
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
                self._notify_error(_("error.title"), _("error.select_to_delete"))
                return Result(False, error=_("error.select_to_delete"))
            
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
            self._notify_error(_("error.critical"), error_msg)
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
                self._notify_error(_("error.title"), _("error.select_to_edit"))
                return False
            
            qso = self.qso_manager.get_qso(index)
            if qso is None:
                self._notify_error(_("error.title"), _("error.select_to_edit"))
                return False
            if self.gui_bridge:
                self.gui_bridge.switch_tab(0)  # Переключиться на вкладку "Добавить"
                self.gui_bridge.populate_form(qso)
                self.gui_bridge.set_focus('call')
            
            begin_result = self.qso_manager.begin_edit(index)
            if not begin_result.success:
                self._notify_error(_("error.title"), begin_result.error)
                return False
            return True
        except Exception as e:
            log_error(f"Error loading QSO for edit: {e}")
            return False
    
    def cancel_edit(self):
        """Отменить редактирование: сбросить editing_index и очистить форму."""
        self.qso_manager.cancel_edit()
        if self.gui_bridge:
            self.gui_bridge.clear_form()

