"""Journal list rendering, record marks, and context-menu behavior."""

import json

import wx

from common.constants import JOURNAL_COLUMNS, QSO_FIELD_NAMES
from localization.i18n import tr
from logger import log_error


class JournalViewMixin:
    def _init_journal_ui(self, panel):
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.journal_list = wx.ListCtrl(
            panel,
            style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES,
            size=(-1, 600),
        )
        self._marked_export_keys = set()
        sizer.Add(self.journal_list, 1, wx.EXPAND | wx.ALL, 5)
        panel.SetSizer(sizer)

        # Context menu for journal list (Application key, Shift+F10, right click).
        self.journal_list.Bind(wx.EVT_CONTEXT_MENU, self.on_journal_context_menu)

    @staticmethod
    def _qso_signature(qso):
        """Create a stable signature for a QSO dictionary."""
        return json.dumps(qso, ensure_ascii=False, sort_keys=True, default=str)

    def _get_qso_keys(self, qsos):
        """Return stable keys, including occurrence numbers for identical records."""
        occurrences = {}
        keys = []
        for qso in qsos:
            signature = self._qso_signature(qso)
            occurrence = occurrences.get(signature, 0)
            occurrences[signature] = occurrence + 1
            keys.append((signature, occurrence))
        return keys

    def _init_journal_columns(self):
        # The first column explicitly reports whether a record is marked for export.
        try:
            while self.journal_list.GetColumnCount() > 0:
                self.journal_list.DeleteColumn(0)
        except Exception as error:
            log_error(f"Failed to reset journal columns: {error}")

        self.journal_list.InsertColumn(0, tr("journal.export_mark"), width=100)
        journal_columns = []
        idx = 1
        for field_name, (title_key, width) in zip(QSO_FIELD_NAMES, JOURNAL_COLUMNS):
            if field_name == "datetime":
                continue
            self.journal_list.InsertColumn(idx, tr(title_key), width=width)
            journal_columns.append(field_name)
            idx += 1

        dt_title_key, dt_width = JOURNAL_COLUMNS[-1]
        self.journal_list.InsertColumn(idx, tr(dt_title_key), width=dt_width)
        journal_columns.append("datetime")
        self.journal_columns = journal_columns

    def on_journal_context_menu(self, event):
        """Accessible context menu for editing, deleting, marking, and exporting QSO."""
        row = self.journal_list.GetFirstSelected()
        menu = wx.Menu()
        edit_item = menu.Append(wx.ID_ANY, tr("button.edit") + "\\tCtrl+E")
        del_item = menu.Append(wx.ID_ANY, tr("button.delete") + "\\tDel")
        menu.AppendSeparator()

        marked = False
        if row != -1:
            qsos = self.controller.get_qso_list()
            if row < len(qsos):
                marked = self._get_qso_keys(qsos)[row] in self._marked_export_keys

        mark_label = tr("journal.unmark_export") if marked else tr("journal.mark_export")
        mark_item = menu.Append(wx.ID_ANY, mark_label)
        export_item = menu.Append(wx.ID_ANY, tr("journal.export_marked"))
        clear_item = menu.Append(wx.ID_ANY, tr("journal.clear_export_marks"))

        menu.Bind(wx.EVT_MENU, self.on_edit_qso, edit_item)
        menu.Bind(wx.EVT_MENU, self.on_delete_qso, del_item)
        menu.Bind(wx.EVT_MENU, self.on_toggle_export_mark, mark_item)
        menu.Bind(wx.EVT_MENU, self.on_export_marked_qsos, export_item)
        menu.Bind(wx.EVT_MENU, self.on_clear_export_marks, clear_item)

        if row == -1:
            mark_item.Enable(False)
        export_item.Enable(bool(self._marked_export_keys))
        clear_item.Enable(bool(self._marked_export_keys))
        self.PopupMenu(menu)
        menu.Destroy()

    def on_toggle_export_mark(self, event=None):
        """Toggle the export mark for the currently selected QSO."""
        row = self.journal_list.GetFirstSelected()
        qsos = self.controller.get_qso_list()
        if row == -1 or row >= len(qsos):
            self.gui_bridge.show_notification(tr("journal.select_to_mark"))
            return

        key = self._get_qso_keys(qsos)[row]
        if key in self._marked_export_keys:
            self._marked_export_keys.remove(key)
            message = tr("journal.export_mark_removed")
        else:
            self._marked_export_keys.add(key)
            message = tr("journal.export_mark_added")
        self._update_journal_from_manager()
        if row < self.journal_list.GetItemCount():
            self.journal_list.SetItemState(
                row, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
            )
            self.journal_list.SetFocus()
        self.gui_bridge.show_notification(message)

    def on_clear_export_marks(self, event=None):
        """Clear all export marks without changing journal records."""
        if not self._marked_export_keys:
            return
        self._marked_export_keys.clear()
        self._update_journal_from_manager()
        self.gui_bridge.show_notification(tr("journal.export_marks_cleared"))
        self.journal_list.SetFocus()

    def get_marked_qsos(self):
        """Return copies of marked records in their current journal order."""
        qsos = self.controller.get_qso_list()
        keys = self._get_qso_keys(qsos)
        return [qso for qso, key in zip(qsos, keys) if key in self._marked_export_keys]

    def on_export_marked_qsos(self, event=None):
        """Export only records explicitly marked by the user."""
        qsos = self.get_marked_qsos()
        if not qsos:
            self.gui_bridge.show_notification(tr("journal.no_export_marks"))
            return
        result = self.on_export(event=None, qsos=qsos)
        if result and result.success:
            marked_keys = {key for key in self._marked_export_keys}
            self._marked_export_keys.difference_update(marked_keys)
            self._update_journal_from_manager()
            self.journal_list.SetFocus()
            self.gui_bridge.show_notification(tr("journal.export_marks_exported"))

    def _update_journal_from_manager(self):
        """Refresh journal rows and keep marks associated with their records."""
        self._journal_saved = False
        self.journal_list.DeleteAllItems()
        qsos = self.controller.get_qso_list()
        keys = self._get_qso_keys(qsos)
        for idx, (qso, key) in enumerate(zip(qsos, keys)):
            self.journal_list.InsertItem(idx, tr("journal.export_marked_yes") if key in self._marked_export_keys else "")
            for col, field in enumerate(getattr(self, "journal_columns", []), start=1):
                self.journal_list.SetItem(idx, col, str(qso.get(field, "") or ""))
