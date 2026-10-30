"""Handlers for QSO actions initiated from the main window."""
import wx

from localization.i18n import tr


class QSOActionsMixin:
    """Keep journal actions thin and delegate business logic to the controller."""

    def on_cancel_edit(self, event=None):
        """Escape clears marks in the journal, or cancels form editing."""
        if hasattr(self, "notebook") and self.notebook.GetSelection() == 1:
            self.on_clear_export_marks()
            return
        if not self.controller.is_editing():
            return
        self.controller.cancel_edit()
        self.gui_bridge.show_notification(tr("edit.cancelled"))

    def on_add_qso(self):
        """Add the QSO to the permanent journal, then clear its form draft."""
        result = self.controller.add_qso_from_gui()
        if result and result.success:
            self._clear_draft_after_add()
        return result

    def on_edit_qso(self, event):
        """Open the selected journal entry for editing through the controller."""
        selected_row = self.journal_list.GetFirstSelected()
        selected_index = self._source_index_for_view_row(selected_row)
        if selected_index >= 0:
            self.controller.load_qso_for_edit(selected_index)

    def on_delete_qso(self, event=None):
        """Delete all marked records, or the focused record when no marks exist."""
        all_qsos = self.controller.get_qso_list()
        marked_keys = {key for key in self._get_qso_keys(all_qsos)
                       if key in self._marked_export_keys}
        if marked_keys:
            self.on_delete_marked_qsos(event)
            return

        focused_row = self.journal_list.GetFocusedItem()
        if focused_row < 0:
            focused_row = self.journal_list.GetFirstSelected()
        selected_index = self._source_index_for_view_row(focused_row)
        if selected_index >= 0:
            self.controller.delete_qso(selected_index)
            self._focus_journal_list_first()


    def on_delete_marked_qsos(self, event=None):
        """Delete all marked records in the journal, including records hidden by filters."""
        all_qsos = self.controller.get_qso_list()
        all_keys = self._get_qso_keys(all_qsos)
        marked_keys = {key for key in all_keys if key in self._marked_export_keys}
        if not marked_keys:
            self.gui_bridge.show_notification(tr("journal.no_marked_to_delete"))
            return
        answer = wx.MessageBox(
            tr("journal.confirm_delete_marked").format(count=len(marked_keys)),
            tr("button.delete"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            self,
        )
        if answer != wx.YES:
            self.journal_list.SetFocus()
            return
        source_indexes = [index for index, key in enumerate(all_keys) if key in marked_keys]
        for index in sorted(source_indexes, reverse=True):
            self.controller.delete_qso(index)
        self._marked_export_keys.difference_update(marked_keys)
        self._refresh_journal_preserving_saved_state()
        self._focus_journal_list_first()
