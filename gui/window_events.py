"""Window date handling, tab events and live time updates."""

import wx
from localization.i18n import tr
from logger import log_ui_state, log_error


class WindowEventsMixin:
    def _reset_datetime_override(self):
        """Reset manual datetime override state."""
        self._datetime_manual_override = False
        self._journal_saved = False  # True after successful export, reset on any journal change

    def _set_datetime_change_suppression(self, enabled):
        """Suppress or allow programmatic datetime control changes."""
        self._suppress_datetime_change_events = bool(enabled)

    def on_datetime_control_change(self, event):
        """Mark manual datetime entry so auto-update will stop."""
        if not self._suppress_datetime_change_events:
            self._datetime_manual_override = True
        event.Skip()

    def on_page_changed(self, event):
        selected_page = self.notebook.GetSelection()
        if (selected_page == 0):
            log_ui_state("Switched to QSO addition tab")
            if not self.controller.is_editing():
                self._reset_datetime_override()
                self._set_datetime_change_suppression(True)
                try:
                    date_value, time_value = self.controller.get_default_datetime_components()
                    if date_value:
                        date_obj = wx.DateTime()
                        if date_obj.ParseISODate(date_value):
                            self.controls['date'].SetValue(date_obj)
                    if time_value:
                        time_obj = wx.DateTime()
                        if time_obj.ParseTime(time_value):
                            self.controls['time'].SetValue(time_obj)
                except Exception:
                    pass
                finally:
                    self._set_datetime_change_suppression(False)
            self.controls['call'].SetFocus()
        elif (selected_page == 1):
            log_ui_state("Switched to journal tab")
            # Reset editing state if user manually switched to journal tab
            # This prevents accidental overwrite of a record being edited
            if self.controller.is_editing():
                self.controller.cancel_edit()
            self.journal_list.SetFocus()
        event.Skip()

    def _init_time_timer(self):
        """Инициализировать таймер обновления текущего времени в форме QSO."""
        if hasattr(self, '_time_update_timer'):
            try:
                self._time_update_timer.Stop()
            except Exception:
                pass
        else:
            self._time_update_timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self._on_time_tick, self._time_update_timer)

        if 'time' in self.controls:
            self._time_update_timer.Start(1000)
        else:
            self._time_update_timer.Stop()

    def _on_time_tick(self, event):
        if 'time' not in self.controls:
            return

        # Не обновляем время, когда редактируется существующая запись.
        if self.controller.is_editing():
            return

        # Не обновляем время, если пользователь вручную изменял дату/время.
        if self._datetime_manual_override:
            return

        # Только обновляем время, если добавление нового QSO активно
        if self.notebook.GetSelection() != 0:
            return

        try:
            date_value, time_value = self.controller.get_default_datetime_components()
            self._suppress_draft_changes = True
            if time_value:
                time_obj = wx.DateTime()
                if time_obj.ParseTime(time_value):
                    self.controls['time'].SetValue(time_obj)
            if 'date' in self.controls and date_value:
                date_obj = wx.DateTime()
                if date_obj.ParseISODate(date_value):
                    self.controls['date'].SetValue(date_obj)
        except Exception as e:
            log_error(f"Failed to update current time tick: {e}")
        finally:
            self._suppress_draft_changes = False
