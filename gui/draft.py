"""GUI-only autosave and restoration behavior for the QSO form."""

import wx
import wx.adv

from logger import log_error
from localization.i18n import tr


class DraftMixin:
    def _bind_draft_events(self):
        """Bind autosave handlers to every currently available form control."""
        for control in self.controls.values():
            if isinstance(control, wx.TextCtrl):
                control.Bind(wx.EVT_TEXT, self._on_draft_change)
            elif isinstance(control, wx.Choice):
                control.Bind(wx.EVT_CHOICE, self._on_draft_change)
        if "date" in self.controls:
            self.controls["date"].Bind(wx.adv.EVT_DATE_CHANGED, self._on_draft_change)
        if "time" in self.controls:
            self.controls["time"].Bind(wx.adv.EVT_TIME_CHANGED, self._on_draft_change)

    def _on_draft_change(self, event=None):
        if not self._suppress_draft_changes and not self.controller.is_editing():
            self._draft_dirty = True
            if self._draft_save_call is not None:
                try:
                    self._draft_save_call.Stop()
                except Exception:
                    pass
            self._draft_save_call = wx.CallLater(250, self._save_draft_from_form)
        if event is not None:
            event.Skip()

    def _read_form_fields_for_draft(self):
        """Read wx controls; persistence and draft policy belong to the controller."""
        fields = {}
        for key in self.controls:
            try:
                fields[key] = self.gui_bridge.get_control_value(key)
            except Exception as error:
                log_error(f"Unable to read draft field {key}: {error}")
        return fields

    def _save_draft_from_form(self):
        self._draft_save_call = None
        if self._suppress_draft_changes or self.controller.is_editing() or not self._draft_dirty:
            return
        result = self.controller.save_draft(self._read_form_fields_for_draft())
        if not result.success:
            self.speak("Не удалось сохранить черновик радиосвязи")
            return
        if not (result.data or {}).get("saved", True):
            self._draft_dirty = False

    def _restore_draft(self):
        draft = self.controller.load_draft()
        if not draft:
            return
        self._suppress_draft_changes = True
        try:
            for key, value in draft.get("fields", {}).items():
                control = self.controls.get(key)
                if control is None:
                    continue
                if isinstance(control, wx.Choice):
                    control.SetStringSelection(str(value))
                elif key == "date":
                    date_value = wx.DateTime()
                    if date_value.ParseISODate(str(value)):
                        control.SetValue(date_value)
                elif key == "time":
                    time_value = wx.DateTime()
                    if time_value.ParseTime(str(value)):
                        control.SetValue(time_value)
                elif hasattr(control, "SetValue"):
                    control.SetValue(value)
            self._draft_dirty = True
            self.speak("Восстановлен незавершённый черновик радиосвязи")
        except Exception as error:
            log_error(f"Unable to restore QSO draft: {error}")
        finally:
            self._suppress_draft_changes = False

    def clear_draft_form(self):
        """Clear the unfinished form without touching saved journal records."""
        if self.controller.is_editing():
            self.controller.cancel_edit()
        if self._draft_save_call is not None:
            try:
                self._draft_save_call.Stop()
            except Exception:
                pass
            self._draft_save_call = None

        self._suppress_draft_changes = True
        try:
            for key, control in self.controls.items():
                if isinstance(control, wx.TextCtrl):
                    control.SetValue("")
                elif isinstance(control, wx.Choice):
                    control.SetSelection(wx.NOT_FOUND)

            # Native date/time pickers always contain a value; reset them to now.
            date_value, time_value = self.controller.get_default_datetime_components()
            if "date" in self.controls and date_value:
                date_obj = wx.DateTime()
                if date_obj.ParseISODate(date_value):
                    self.controls["date"].SetValue(date_obj)
            if "time" in self.controls and time_value:
                time_obj = wx.DateTime()
                if time_obj.ParseTime(time_value):
                    self.controls["time"].SetValue(time_obj)
            self._datetime_manual_override = False
            self.controller.clear_draft()
            self._draft_dirty = False
        finally:
            self._suppress_draft_changes = False

        if "call" in self.controls:
            self.controls["call"].SetFocus()
        self.gui_bridge.show_notification(tr("draft.cleared"))

    def _clear_draft_after_add(self):
        if self._draft_save_call is not None:
            try:
                self._draft_save_call.Stop()
            except Exception:
                pass
            self._draft_save_call = None
        result = self.controller.clear_draft()
        self._draft_dirty = False
        if not result.success:
            self.speak("Не удалось очистить черновик радиосвязи")
