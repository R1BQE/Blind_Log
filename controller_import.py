"""ADIF import commands for the application controller."""

from importer import import_adif_file as _do_import, is_adif_available
from utils import Result
from logger import log_error
from i18n import tr as _


class ControllerImportMixin:
    def is_adif_available(self):
        """Возвращает True если библиотека adif-io установлена."""
        return is_adif_available()

    def import_adif_file(self, filepath, mode='replace'):
        """Импортировать QSO из ADIF-файла.

        Args:
            filepath: путь к .adi файлу.
            mode: 'replace' — заменить текущий журнал;
                  'append'  — добавить к существующему (с дедупликацией).

        Returns:
            Result: success, data={'imported': int, 'skipped': int, 'total': int}, error.
        """
        try:
            parse_result = _do_import(filepath) # Call the pre-imported function
        except (ModuleNotFoundError) as e: # ImportError is covered by ModuleNotFoundError in Python 3.6+
            error_msg = f"Importer module not available: {e}"
            log_error(error_msg)
            return Result(False, error=error_msg)
        except (OSError, IOError) as e:
            error_msg = f"ADIF file read error: {e}"
            log_error(error_msg)
            return Result(False, error=error_msg)

        if not parse_result.success:
            return parse_result

        qsos = parse_result.data.get('qsos', []) if parse_result.data else []
        if not qsos:
            return Result(False, error=_("import.empty_file")) # Localized message

        import_result = self.qso_manager.import_qso_list(qsos, mode=mode)
        if not import_result.success:
            return import_result

        # Обновить UI журнала
        if self.gui_bridge:
            try:
                self.gui_bridge.update_journal_display()
            except Exception as e:
                log_error(f"UI update error after import: {e}")

        # Уведомление пользователю через NVDA
        data = import_result.data or {}
        imported = data.get('imported', 0)
        skipped = data.get('skipped', 0)
        if skipped > 0:
            self._notify_success(_("import.success_with_skipped").format(imported=imported, skipped=skipped))
        else:
            self._notify_success(_("import.success").format(count=imported))

        return import_result

