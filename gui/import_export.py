"""GUI handlers for importing and exporting ADIF files."""

from datetime import datetime

import wx
from updater import Result
from i18n import tr
from logger import log_error


class ImportExportMixin:
    def on_export(self, event=None):
        """Запустить диалог экспорта и сохранить ADIF через Exporter."""
        # Generate default filename: callsign_date_time.adi
        operator = self.settings_manager.get_option('call', '').strip().lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_name = f"{operator}_{timestamp}.adi" if operator else f"{timestamp}.adi"

        with wx.FileDialog(self, tr("export.save_adif"), wildcard="ADIF files (*.adi)|*.adi",
                           defaultFile=default_name,
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return Result(False)

            pathname = fileDialog.GetPath()
            result = self.controller.export_to_adif(pathname)
            if result.success:
                self._journal_saved = True
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
