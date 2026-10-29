"""wxPython implementation of the controller-to-GUI bridge."""

import wx
from datetime import datetime
import nvda_notify
from controller import GUIBridge
from i18n import tr
from logger import log_error

class GUIBridgeImpl(GUIBridge):
    """Реализация интерфейса GUIBridge для взаимодействия controller с GUI."""
    
    def __init__(self, gui_frame):
        self.gui_frame = gui_frame
    
    def show_error(self, title, message):
        """Показать диалог ошибки."""
        wx.MessageBox(message, title, wx.OK | wx.ICON_ERROR)
    
    def show_notification(self, message):
        """Показать уведомление через NVDA."""
        nvda_notify.nvda_notify(message)

    def confirm(self, message, title, style=wx.YES_NO | wx.ICON_QUESTION):
        """Запросить подтверждение пользователя через диалог."""
        dlg = wx.MessageDialog(self.gui_frame, message, title, style)
        result = dlg.ShowModal()
        dlg.Destroy()
        return result == wx.ID_YES

    def show_settings_dialog(self, settings_manager):
        """Открыть диалог настроек через GUI."""
        from settings_dialog import SettingsDialog
        dialog = SettingsDialog(parent=self.gui_frame, title=tr("settings.title"), settings_manager=settings_manager)
        try:
            dialog.notebook.SetFocus()
        except AttributeError:
            pass
        result = dialog.ShowModal()
        dialog.Destroy()
        return result == wx.ID_OK

    def run_in_ui_thread(self, func, *args, **kwargs):
        """Запустить callback в UI-потоке."""
        wx.CallAfter(func, *args, **kwargs)
    
    def switch_tab(self, tab_index):
        """Переключиться на вкладку."""
        if hasattr(self.gui_frame, 'notebook'):
            self.gui_frame.notebook.SetSelection(tab_index)
    
    def set_focus(self, control_name):
        """Установить фокус на контрол."""
        if control_name in self.gui_frame.controls:
            self.gui_frame.controls[control_name].SetFocus()
    
    def get_control_value(self, control_name):
        """Получить значение из контрола."""
        if control_name not in self.gui_frame.controls:
            return ""
        
        ctrl = self.gui_frame.controls[control_name]
        try:
            if hasattr(ctrl, 'GetValue'):
                value = ctrl.GetValue()
                if isinstance(value, wx.DateTime):
                    if control_name == 'date':
                        return value.FormatISODate()
                    if control_name == 'time':
                        return value.Format('%H:%M:%S')
                    return value.FormatISODate()
                return value
            elif hasattr(ctrl, 'GetStringSelection'):
                return ctrl.GetStringSelection()
            elif hasattr(ctrl, 'GetSelection') and hasattr(ctrl, 'GetString'):
                sel = ctrl.GetSelection()
                return ctrl.GetString(sel) if sel != wx.NOT_FOUND else ''
            else:
                return ""
        except Exception as e:
            log_error(f"Error getting control value for {control_name}: {e}")
            return ""
    
    def set_control_value(self, control_name, value):
        """Установить значение в контрол."""
        if control_name not in self.gui_frame.controls:
            return
        
        ctrl = self.gui_frame.controls[control_name]
        try:
            if hasattr(ctrl, 'SetValue'):
                if control_name == 'time' and isinstance(value, str):
                    time_obj = wx.DateTime()
                    if time_obj.ParseTime(value):
                        ctrl.SetValue(time_obj)
                        return
                ctrl.SetValue(value)
            elif hasattr(ctrl, 'SetStringSelection'):
                ctrl.SetStringSelection(value)
        except Exception as e:
            log_error(f"Error setting control value for {control_name}: {e}")
    
    def clear_form(self):
        """Очистить форму добавления QSO."""
        controls_to_clear = ['call', 'name', 'city', 'qth', 'comment']
        for key in controls_to_clear:
            if key in self.gui_frame.controls:
                self.gui_frame.controls[key].SetValue("")
        
        # Установить дату/время
        if 'date' in self.gui_frame.controls or 'time' in self.gui_frame.controls:
            self.gui_frame._reset_datetime_override()
            self.gui_frame._set_datetime_change_suppression(True)
            try:
                if 'date' in self.gui_frame.controls:
                    try:
                        # Use controller to obtain timezone-aware current date/time if available
                        date_str, time_str = ('', '')
                        try:
                            if hasattr(self.gui_frame, 'controller') and self.gui_frame.controller:
                                date_str, time_str = self.gui_frame.controller.get_default_datetime_components()
                        except Exception:
                            date_str, time_str = ('', '')

                        if date_str:
                            date_obj = wx.DateTime()
                            if date_obj.ParseISODate(date_str):
                                self.gui_frame.controls['date'].SetValue(date_obj)
                        else:
                            now = datetime.now()
                            self.gui_frame.controls['date'].SetValue(
                                wx.DateTime.FromDMY(now.day, now.month - 1, now.year)
                            )
                    except Exception as e:
                        log_error(f"Failed to set default date in clear_form: {e}")
                if 'time' in self.gui_frame.controls:
                    try:
                        if 'time_str' in locals() and time_str:
                            time_obj = wx.DateTime()
                            if time_obj.ParseTime(time_str):
                                self.gui_frame.controls['time'].SetValue(time_obj)
                        else:
                            now = datetime.now()
                            self.gui_frame.controls['time'].SetValue(
                                wx.DateTime.FromHMS(now.hour, now.minute, now.second)
                            )
                    except Exception as e:
                        log_error(f"Failed to set default time in clear_form: {e}")
            finally:
                self.gui_frame._set_datetime_change_suppression(False)
    
    def populate_form(self, qso_data):
        """Заполнить форму данными QSO для редактирования."""
        field_mapping = {
            'call': qso_data.get('call', ''),
            'name': qso_data.get('name', ''),
            'city': qso_data.get('city', ''),
            'qth': qso_data.get('qth', ''),
            'band': qso_data.get('band', ''),
            'mode': qso_data.get('mode', ''),
            'freq': qso_data.get('freq', ''),
            'rst_received': qso_data.get('rst_received', ''),
            'rst_sent': qso_data.get('rst_sent', ''),
            'comment': qso_data.get('comment', ''),
        }
        
        for control_name, value in field_mapping.items():
            self.set_control_value(control_name, value)
        
        # Обработка date и time из datetime
        datetime_str = qso_data.get('datetime', '')
        if datetime_str and len(datetime_str) >= 16:  # YYYY-MM-DD HH:MM
            self.gui_frame._set_datetime_change_suppression(True)
            try:
                date_part = datetime_str[:10]  # YYYY-MM-DD
                time_part = datetime_str[11:16]  # HH:MM
                if 'date' in self.gui_frame.controls:
                    date_obj = wx.DateTime()
                    if date_obj.ParseISODate(date_part):
                        self.gui_frame.controls['date'].SetValue(date_obj)
                if 'time' in self.gui_frame.controls:
                    time_obj = wx.DateTime()
                    if time_obj.ParseTime(time_part):
                        self.gui_frame.controls['time'].SetValue(time_obj)
            except Exception as e:
                log_error(f"Error parsing datetime for editing: {e}")
            finally:
                self.gui_frame._set_datetime_change_suppression(False)
    
    def update_journal_display(self):
        """Обновить отображение журнала."""
        if hasattr(self.gui_frame, '_update_journal_from_manager'):
            self.gui_frame._update_journal_from_manager()
