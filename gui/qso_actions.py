"""Handlers for QSO actions initiated from the main window."""
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
        selected_index = self.journal_list.GetFirstSelected()
        self.controller.load_qso_for_edit(selected_index)

    def on_delete_qso(self, event):
        """Delete the selected journal entry through the controller."""
        selected_index = self.journal_list.GetFirstSelected()
        self.controller.delete_qso(selected_index)

