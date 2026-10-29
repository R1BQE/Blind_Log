"""Keyboard shortcuts, focus helpers and accessible announcements."""

import wx
from localization.i18n import tr
from logger import log_debug, log_error
from .ids import (
    ID_ADD_QSO, ID_EDIT_QSO, ID_DEL_QSO, ID_EXPORT_QSO, ID_IMPORT_ADIF,
    ID_FOCUS_CALL, ID_FOCUS_NAME, ID_FOCUS_CITY, ID_FOCUS_QTH, ID_FOCUS_FREQ,
    ID_FOCUS_RST_REC, ID_FOCUS_RST_SENT, ID_CYCLE_MODE, ID_CYCLE_BAND,
    ID_FOCUS_COMMENT, ID_FOCUS_DATE, ID_FOCUS_TIME, ID_CANCEL_EDIT, ID_LOOKUP_CALLSIGN,
    ID_CHANGELOG, ID_UPDATE, ID_CLEAR_DRAFT,
    ID_JOURNAL_SEARCH, ID_JOURNAL_SORT, ID_JOURNAL_FILTER,
)


class KeyboardMixin:
    def speak(self, text):
        """Озвучить текст через NVDA"""
        try:
            self.gui_bridge.show_notification(text)
        except Exception as e:
            log_error(f"Failed to announce text via GUI bridge: {e}")

    def focus_field(self, key, label_key):
        """Установить фокус на поле или озвучить, что оно скрыто."""
        if key not in self.controls:
            label = tr(label_key)
            self.speak(tr("field.hidden").format(field=label))
            return

        widget = self.controls[key]
        widget.SetFocus()

    def _init_accelerator(self):
        # Используем кастомные IDs для ускорителей, чтобы они работали даже после перестроения UI
        accel_entries = [
            (wx.ACCEL_CTRL, ord('E'), ID_EDIT_QSO),
            (wx.ACCEL_CTRL, ord('S'), ID_EXPORT_QSO),
            (wx.ACCEL_CTRL, ord('O'), ID_IMPORT_ADIF),
            (wx.ACCEL_NORMAL, wx.WXK_DELETE, ID_DEL_QSO),
            (wx.ACCEL_SHIFT, wx.WXK_F1, wx.ID_ABOUT),
            (wx.ACCEL_NORMAL, wx.WXK_F1, wx.ID_HELP),
            (wx.ACCEL_CTRL, wx.WXK_F1, ID_CHANGELOG),
            (wx.ACCEL_CTRL, ord('U'), ID_UPDATE),
            (wx.ACCEL_CTRL, ord('F'), ID_JOURNAL_SEARCH),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('S'), ID_JOURNAL_SORT),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('F'), ID_JOURNAL_FILTER),
            # Новые горячие клавиши для полей
            (wx.ACCEL_ALT, ord('C'), ID_FOCUS_CALL),
            (wx.ACCEL_ALT, ord('N'), ID_FOCUS_NAME),
            (wx.ACCEL_ALT, ord('T'), ID_FOCUS_CITY),
            (wx.ACCEL_ALT, ord('Q'), ID_FOCUS_QTH),
            (wx.ACCEL_ALT, ord('F'), ID_FOCUS_FREQ),
            (wx.ACCEL_ALT, ord('R'), ID_FOCUS_RST_REC),
            (wx.ACCEL_ALT, ord('S'), ID_FOCUS_RST_SENT),
            (wx.ACCEL_ALT, ord('M'), ID_CYCLE_MODE),
            (wx.ACCEL_ALT, ord('B'), ID_CYCLE_BAND),
            (wx.ACCEL_ALT, ord('O'), ID_FOCUS_COMMENT),
            (wx.ACCEL_ALT, ord('D'), ID_FOCUS_DATE),
            (wx.ACCEL_ALT, ord('I'), ID_FOCUS_TIME),
            (wx.ACCEL_NORMAL, wx.WXK_ESCAPE, ID_CANCEL_EDIT),
            (wx.ACCEL_CTRL, wx.WXK_RETURN, ID_LOOKUP_CALLSIGN),
        ]
        accel_tbl = wx.AcceleratorTable([wx.AcceleratorEntry(*entry) for entry in accel_entries])
        self.SetAcceleratorTable(accel_tbl)

        # Ctrl+Delete must be intercepted before wx.TextCtrl handles it as
        # "delete next word". A frame-level char hook sees the key first.
        self.Unbind(wx.EVT_CHAR_HOOK, handler=self._on_char_hook)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

        # Unbind старые binds перед новыми
        for id_ in [ID_FOCUS_CALL, ID_FOCUS_NAME, ID_FOCUS_CITY, ID_FOCUS_QTH, ID_FOCUS_FREQ,
                    ID_FOCUS_RST_REC, ID_FOCUS_RST_SENT, ID_CYCLE_MODE, ID_CYCLE_BAND,
                    ID_FOCUS_COMMENT, ID_FOCUS_DATE, ID_FOCUS_TIME, ID_CLEAR_DRAFT,
                    ID_JOURNAL_SEARCH, ID_JOURNAL_SORT, ID_JOURNAL_FILTER]:
            self.Unbind(wx.EVT_MENU, id=id_)

        # Binds для горячих клавиш полей
        # Обычные поля: проверяем видимость и озвучиваем "скрыто"
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('call', "label.callsign"), id=ID_FOCUS_CALL)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('name', "label.name"), id=ID_FOCUS_NAME)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('city', "label.city"), id=ID_FOCUS_CITY)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('qth', "label.qth"), id=ID_FOCUS_QTH)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('freq', "label.freq"), id=ID_FOCUS_FREQ)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('rst_received', "label.rst_received"), id=ID_FOCUS_RST_REC)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('rst_sent', "label.rst_sent"), id=ID_FOCUS_RST_SENT)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('comment', "label.comment"), id=ID_FOCUS_COMMENT)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('date', "label.date"), id=ID_FOCUS_DATE)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('time', "label.time"), id=ID_FOCUS_TIME)
        
        # Отмена редактирования по Escape
        self.Bind(wx.EVT_MENU, self.on_cancel_edit, id=ID_CANCEL_EDIT)
        # Поиск позывного по Ctrl+Enter
        self.Bind(wx.EVT_MENU, self._on_lookup_shortcut, id=ID_LOOKUP_CALLSIGN)
        self.Bind(wx.EVT_MENU, self.on_clear_draft_shortcut, id=ID_CLEAR_DRAFT)
        self.Bind(wx.EVT_MENU, self.focus_journal_search, id=ID_JOURNAL_SEARCH)
        self.Bind(wx.EVT_MENU, self.focus_journal_sort, id=ID_JOURNAL_SORT)
        self.Bind(wx.EVT_MENU, self.on_open_journal_filters, id=ID_JOURNAL_FILTER)

        # ComboBox: всегда работают, независимо от видимости
        self.Bind(wx.EVT_MENU, lambda evt: self.cycle_choice('mode'), id=ID_CYCLE_MODE)
        self.Bind(wx.EVT_MENU, lambda evt: self.cycle_choice('band'), id=ID_CYCLE_BAND)

    def cycle_choice(self, key):
        choice = self.controls[key]
        current = choice.GetSelection()
        count = choice.GetCount()
        if count > 0:
            new_index = (current + 1) % count
            choice.SetSelection(new_index)
            # Озвучиваем новое значение через NVDA
            value = choice.GetString(new_index)
            label_key = f"field.{key}"
            label = tr(label_key)
            self.gui_bridge.show_notification(f"{label}: {value}")

    def on_undo_journal(self, event=None):
        """Undo one of the last five successful journal mutations."""
        if self.notebook.GetSelection() != 1:
            return
        result = self.controller.undo_last_change()
        if not result.success:
            self.gui_bridge.show_notification(tr("journal.nothing_to_undo"))
            return
        self._journal_saved = False
        self._update_journal_from_manager()
        if self.journal_list.GetItemCount():
            self.journal_list.SetItemState(
                0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
            )
        self.journal_list.SetFocus()
        self.gui_bridge.show_notification(tr("journal.undo_success"))

    def _on_char_hook(self, event):
        """Route Enter and Ctrl+Delete according to the active tab and focused control."""
        focus = wx.Window.FindFocus()
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            if self.notebook.GetSelection() == 1 and focus is getattr(self, "journal_search", None):
                self.on_journal_search_enter()
                return
            if self.notebook.GetSelection() == 0:
                self.on_add_qso()
                return
        if event.GetKeyCode() == wx.WXK_DELETE and event.ControlDown():
            focus = wx.Window.FindFocus()
            if self.notebook.GetSelection() == 1 and focus is getattr(self, "journal_search", None):
                self.clear_journal_search()
                return
            if self.notebook.GetSelection() == 0:
                self.clear_draft_form()
                return
        event.Skip()

    def on_clear_draft_shortcut(self, event=None):
        """Ctrl+Delete clears only the unsaved form draft on the add tab."""
        if self.notebook.GetSelection() == 0:
            self.clear_draft_form()

    def _on_lookup_shortcut(self, event=None):
        """Run the configured callsign lookup command from the keyboard."""
        callsign = self.gui_bridge.get_control_value("call")
        if callsign:
            self.controller.lookup_callsign(callsign)
