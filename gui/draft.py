"""Draft autosave and restoration behavior for the QSO form."""

import wx
import wx.adv

from constants import BANDS, MODES, DEFAULT_MODE_INDEX, DEFAULT_BAND_INDEX
from logger import log_error


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
        if not self._suppress_draft_changes and self.qso_manager.editing_index is None:
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
        fields = {}
        for key, control in self.controls.items():
            try:
                if isinstance(control, wx.TextCtrl):
                    fields[key] = control.GetValue()
                elif isinstance(control, wx.Choice):
                    selection = control.GetSelection()
                    fields[key] = control.GetString(selection) if selection != wx.NOT_FOUND else ""
                elif key == "date":
                    fields[key] = control.GetValue().FormatISODate()
                elif key == "time":
                    fields[key] = control.GetValue().Format("%H:%M:%S")
            except Exception as error:
                log_error(f"Unable to read draft field {key}: {error}")
        return fields

    def _save_draft_from_form(self):
        self._draft_save_call = None
        if self._suppress_draft_changes or self.qso_manager.editing_index is not None or not self._draft_dirty:
            return
        fields = self._read_form_fields_for_draft()
        meaningful = any(str(fields.get(key, "")).strip() for key in
                         ("call", "name", "city", "qth", "freq", "comment"))
        meaningful = meaningful or any(
            str(fields.get(key, "")).strip() not in ("", "59")
            for key in ("rst_received", "rst_sent")
        )
        meaningful = meaningful or fields.get("band", "") != BANDS[DEFAULT_BAND_INDEX]
        meaningful = meaningful or fields.get("mode", "") != MODES[DEFAULT_MODE_INDEX]
        if meaningful:
            result = self.qso_manager.save_draft(fields)
            if not result.success:
                self.speak("Не удалось сохранить черновик радиосвязи")
        else:
            self.qso_manager.clear_draft()
            self._draft_dirty = False

    def _restore_draft(self):
        draft = self.qso_manager.load_draft()
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

    def _clear_draft_after_add(self):
        if self._draft_save_call is not None:
            try:
                self._draft_save_call.Stop()
            except Exception:
                pass
            self._draft_save_call = None
        result = self.qso_manager.clear_draft()
        self._draft_dirty = False
        if not result.success:
            self.speak("Не удалось очистить черновик радиосвязи")

