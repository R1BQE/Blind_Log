"""Journal list rendering, record marks, and context-menu behavior."""

import json

import wx

from common.constants import JOURNAL_COLUMNS, QSO_FIELD_NAMES
from .journal_filters import JournalFilterDialog, SORT_FIELDS, TEXT_FILTERS, empty_filter_state, filter_qsos, sort_qsos
from localization.i18n import tr
from logger import log_error


class JournalViewMixin:
    def _init_journal_ui(self, panel):
        self._journal_search_query = ""
        self._journal_filters = empty_filter_state()
        self._journal_sort_key = self.settings_manager.get_option("journal_sort", "datetime_desc")
        self._sort_options = []
        sizer = wx.BoxSizer(wx.VERTICAL)
        # Create the list first: it is the first tab stop on the Journal page.
        self.journal_list = wx.ListCtrl(
            panel, style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES, size=(-1, 600)
        )
        self._marked_export_keys = set()
        self.journal_list.Bind(wx.EVT_CHAR, self.on_journal_char)
        self.journal_list.Bind(wx.EVT_CONTEXT_MENU, self.on_journal_context_menu)

        search_row = wx.BoxSizer(wx.HORIZONTAL)
        search_row.Add(wx.StaticText(panel, label=tr("journal.search")), 0,
                       wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.journal_search = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER, name="journal_search")
        self.journal_search.SetHint(tr("journal.search.hint"))
        search_row.Add(self.journal_search, 1, wx.EXPAND)
        sizer.Add(search_row, 0, wx.EXPAND | wx.ALL, 5)

        sort_row = wx.BoxSizer(wx.HORIZONTAL)
        sort_row.Add(wx.StaticText(panel, label=tr("journal.sort")), 0,
                     wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.journal_sort = wx.Choice(panel, choices=[])
        self._build_sort_choices()
        self.journal_sort.Bind(wx.EVT_CHOICE, self.on_journal_sort_changed)
        sort_row.Add(self.journal_sort, 1, wx.EXPAND | wx.RIGHT, 8)
        self.filter_button = wx.Button(panel, label=tr("journal.filters.button"))
        self.filter_button.Bind(wx.EVT_BUTTON, self.on_open_journal_filters)
        sort_row.Add(self.filter_button, 0, wx.EXPAND)
        sizer.Add(sort_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        sizer.Add(self.journal_list, 1, wx.EXPAND | wx.ALL, 5)
        panel.SetSizer(sizer)

        # The list was created first, followed by search, sort and filter controls.
        self.journal_search.MoveAfterInTabOrder(self.journal_list)
        self.journal_sort.MoveAfterInTabOrder(self.journal_search)
        self.filter_button.MoveAfterInTabOrder(self.journal_sort)
        self.journal_search.Bind(wx.EVT_TEXT_ENTER, self.on_journal_search_enter)
        if not hasattr(self, "journal_status_bar"):
            self.journal_status_bar = self.CreateStatusBar(1)
        self._update_filter_indicators()

    def _build_sort_choices(self):
        self._sort_options = []
        labels = []
        for field, label_key in SORT_FIELDS:
            for direction, suffix_key in (("asc", "journal.sort.ascending"),
                                          ("desc", "journal.sort.descending")):
                self._sort_options.append(f"{field}_{direction}")
                labels.append(f"{tr(label_key)} — {tr(suffix_key)}")
        self.journal_sort.SetItems(labels)
        if self._journal_sort_key not in self._sort_options:
            self._journal_sort_key = "datetime_desc"
        self.journal_sort.SetSelection(self._sort_options.index(self._journal_sort_key))

    def on_journal_sort_changed(self, event=None):
        index = self.journal_sort.GetSelection()
        if 0 <= index < len(self._sort_options):
            self._journal_sort_key = self._sort_options[index]
            try:
                settings = dict(self.settings_manager.settings)
                settings["journal_sort"] = self._journal_sort_key
                self.settings_manager.save_settings(settings)
            except Exception as error:
                log_error(f"Failed to save journal sort preference: {error}")
            self._update_journal_from_manager()
        if event is not None:
            event.Skip()

    def focus_journal_search(self, event=None):
        self.notebook.SetSelection(1)
        self.journal_search.SetFocus()
        self.journal_search.SetSelection(-1, -1)

    def focus_journal_sort(self, event=None):
        self.notebook.SetSelection(1)
        self.journal_sort.SetFocus()

    def on_journal_search_enter(self, event=None):
        self._journal_search_query = self.journal_search.GetValue().strip()
        self._update_journal_from_manager()
        self.journal_list.SetFocus()
        if self.journal_list.GetItemCount():
            self.journal_list.SetItemState(
                0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
            )
        self.gui_bridge.show_notification(
            tr("journal.search.results").format(count=self.journal_list.GetItemCount())
        )

    def clear_journal_search(self):
        self.journal_search.SetValue("")
        self._journal_search_query = ""
        self._update_journal_from_manager()
        self.journal_list.SetFocus()
        self.gui_bridge.show_notification(tr("journal.search.cleared"))

    def on_open_journal_filters(self, event=None):
        self.notebook.SetSelection(1)
        dialog = JournalFilterDialog(self, self._journal_filters)
        try:
            if dialog.ShowModal() == wx.ID_OK:
                self._journal_filters = dialog.get_result_state()
                self._update_journal_from_manager()
        finally:
            dialog.Destroy()
        self.journal_list.SetFocus()

    def _update_filter_indicators(self):
        if not hasattr(self, "filter_button"):
            return
        state = self._journal_filters
        labels = dict(TEXT_FILTERS)
        descriptions = []
        for key, enabled in state.get("enabled", {}).items():
            value = state.get("values", {}).get(key, "").strip()
            if enabled and value:
                descriptions.append(f"{tr(labels[key])} {value}")
        if state.get("bands"):
            descriptions.append(f"{tr('journal.filters.bands')}: {', '.join(state['bands'])}")
        if state.get("modes"):
            descriptions.append(f"{tr('journal.filters.modes')}: {', '.join(state['modes'])}")
        for enabled_key, label_key, value_keys in (
            ("date_enabled", "journal.filters.date", ("date",)),
            ("date_range_enabled", "journal.filters.date_range", ("date_from", "date_to")),
            ("time_enabled", "journal.filters.time", ("time",)),
            ("time_range_enabled", "journal.filters.time_range", ("time_from", "time_to")),
        ):
            if state.get(enabled_key):
                value = " — ".join(state.get(key, "") for key in value_keys)
                descriptions.append(f"{tr(label_key)}: {value}")
        self.filter_button.SetLabel(
            tr("journal.filters.button") + (f" ({len(descriptions)})" if descriptions else "")
        )
        summary = "; ".join(descriptions) if descriptions else tr("journal.filters.none")
        self.filter_button.SetToolTip(summary)
        try:
            self.SetStatusText(tr("journal.status").format(
                count=len(self.get_qsos_in_current_view()), filters=summary
            ))
        except Exception:
            pass

    def on_journal_char(self, event):
        """Handle keyboard shortcuts while the journal list has focus."""
        if event.GetKeyCode() == wx.WXK_SPACE:
            self.on_toggle_export_mark()
            return
        if event.ControlDown() and event.GetKeyCode() in (ord('Z'), ord('z'), 26):
            self.on_undo_journal()
            return
        event.Skip()

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
        clear_item = menu.Append(wx.ID_ANY, tr("journal.clear_export_marks"))

        menu.Bind(wx.EVT_MENU, self.on_edit_qso, edit_item)
        menu.Bind(wx.EVT_MENU, self.on_delete_qso, del_item)
        menu.Bind(wx.EVT_MENU, self.on_toggle_export_mark, mark_item)
        menu.Bind(wx.EVT_MENU, self.on_clear_export_marks, clear_item)

        if row == -1:
            mark_item.Enable(False)
        clear_item.Enable(bool(self._marked_export_keys))
        self.PopupMenu(menu)
        menu.Destroy()

    def _refresh_journal_preserving_saved_state(self):
        """Refresh mark indicators without treating them as journal edits."""
        saved_state = self._journal_saved
        self._update_journal_from_manager()
        self._journal_saved = saved_state

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
        self._refresh_journal_preserving_saved_state()
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
        self._refresh_journal_preserving_saved_state()
        self.gui_bridge.show_notification(tr("journal.export_marks_cleared"))
        self.journal_list.SetFocus()

    def get_qsos_in_current_view(self):
        """Return records in the active journal view; future filters plug in here."""
        filtered_getter = getattr(self, "_get_filtered_qsos", None)
        if callable(filtered_getter):
            return filtered_getter()
        return self.controller.get_qso_list()

    def get_marked_qsos(self, qsos=None):
        """Return marked records, optionally limited to the active view."""
        if qsos is None:
            qsos = self.get_qsos_in_current_view()
        keys = self._get_qso_keys(qsos)
        return [qso for qso, key in zip(qsos, keys) if key in self._marked_export_keys]

    def _update_journal_from_manager(self):
        """Refresh journal rows and keep marks associated with their records."""
        self._journal_saved = False
        self.journal_list.DeleteAllItems()
        qsos = self.controller.get_qso_list()
        keys = self._get_qso_keys(qsos)
        # Remove marks for records that were deleted or changed elsewhere.
        self._marked_export_keys.intersection_update(keys)
        for idx, (qso, key) in enumerate(zip(qsos, keys)):
            self.journal_list.InsertItem(idx, tr("journal.export_marked_yes") if key in self._marked_export_keys else "")
            for col, field in enumerate(getattr(self, "journal_columns", []), start=1):
                self.journal_list.SetItem(idx, col, str(qso.get(field, "") or ""))
