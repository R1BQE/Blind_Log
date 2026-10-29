"""GUI handlers for importing and exporting ADIF files."""

from datetime import datetime

import wx
from common.utils import Result
from localization.i18n import tr
from logger import log_error


class ImportExportMixin:
    def on_export(self, event=None, qsos=None):
        """Export marked records, or the entire active journal view if none are marked."""
        full_qsos = self.controller.get_qso_list()
        view_qsos = self.get_qsos_in_current_view() if hasattr(self, "get_qsos_in_current_view") else full_qsos
        marks_exist = bool(getattr(self, "_marked_export_keys", set()))
        marked_keys_to_clear = set()

        if qsos is None:
            if marks_exist:
                qsos = self.get_marked_qsos(view_qsos)
                if not qsos:
                    self.gui_bridge.show_notification(tr("journal.no_export_marks_in_view"))
                    return Result(False)
                view_keys = self._get_qso_keys(view_qsos)
                marked_keys_to_clear = {
                    key for key in view_keys if key in self._marked_export_keys
                }
            elif view_qsos != full_qsos:
                # Future date/call/band filters export only the records currently shown.
                qsos = view_qsos
            else:
                # None means export the complete journal and preserves the existing saved-state behavior.
                qsos = None

        operator = self.settings_manager.get_option('call', '').strip().lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_name = f"{operator}_{timestamp}.adi" if operator else f"{timestamp}.adi"

        with wx.FileDialog(self, tr("export.save_adif"), wildcard="ADIF files (*.adi)|*.adi",
                           defaultFile=default_name,
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return Result(False)

            pathname = fileDialog.GetPath()
            result = self.controller.export_to_adif(pathname, qsos=qsos)
            if result.success:
                if qsos is None:
                    self._journal_saved = True
                if marked_keys_to_clear:
                    self._marked_export_keys.difference_update(marked_keys_to_clear)
                    self._refresh_journal_preserving_saved_state()
                    self.journal_list.SetFocus()
                self.gui_bridge.show_notification(tr("success.export"))
            elif result.error:
                self.gui_bridge.show_error(tr("error.title"), result.error)
            return result

    def on_import_adif(self, event=None):
        """Открыть файл ADIF и импортировать QSO в журнал.
        Шаги:
          1. Проверка наличия библиотеки adif-io.
          2. Диалог выбора файла.
          3. Диалог выбора режима (заменить / добавить / отмена).
          4. Вызов controller.import_adif_file.
          5. Восстановление фокуса на журнале.
        """
        # 1. Проверка наличия зависимости
        if not self.controller.is_adif_available():
            wx.MessageBox(
                tr("import.adif_unavailable"),
                tr("error.title"),
                wx.OK | wx.ICON_ERROR
            )
            return

        # 2. Выбор файла
        with wx.FileDialog(
 # type: ignore
            self,
            tr("import.open_adif"),
            wildcard="ADIF files (*.adi)|*.adi",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return Result(False)
            filepath = fileDialog.GetPath()

        # 2. Выбор режима импорта
        mode_dlg = wx.MessageDialog(
            self,
            tr("import.choose_mode"),
            tr("import.title"),
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
        )
        try:
            mode_dlg.SetYesNoCancelLabels(
                tr("import.replace_journal"),
                tr("import.append_journal"),
                tr("dialog.cancel"),
            )
            mode = mode_dlg.ShowModal()
        finally:
            mode_dlg.Destroy()

        if mode == wx.ID_CANCEL:
            return Result(False)
        import_mode = 'replace' if mode == wx.ID_YES else 'append'

        # 3. Импорт через контроллер (он же сделает update_journal_display + NVDA-уведомление)
        result = self.controller.import_adif_file(filepath, mode=import_mode)

        # 4. Восстановление фокуса на журнале (там, где пользователь был до импорта)
        if hasattr(self, 'notebook') and hasattr(self, 'journal_list'):
            try:
                self.notebook.SetSelection(1)
                self.journal_list.SetFocus()
            except Exception as e:
                log_error(f"Failed to restore focus after import: {e}")

        return result
