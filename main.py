"""
Основной модуль для приложения Blind_log.
"""

import wx

from gui import Blind_log
from journal.manager import QSOManager
from settings.manager import SettingsManager
from settings.storage import SettingsStorage
from settings.dialog import SettingsDialog
from services.updater import check_update
from gui.language_dialog import show_language_dialog
from gui.welcome_dialog import show_welcome_dialog
from localization.i18n import (
    load_translations,
    get_available_languages,
    get_resolved_language,
    tr,
)


class MyApp(wx.App):
    """Класс приложения Blind_log."""

    def _handle_startup_error(self, error):
        from accessibility import nvda_notify
        from logger import log_error

        log_error(f"Application startup error: {error}")
        nvda_notify.nvda_notify(str(error))
        wx.MessageBox(
            tr("error.startup").format(error=error),
            tr("error.title"),
            wx.OK | wx.ICON_ERROR,
        )

    def OnInit(self):
        """Инициализация приложения."""
        try:
            storage = SettingsStorage()
            first_run = not storage.file_exists()

            # При первом запуске сначала выбираем язык. До подтверждения
            # выбора SettingsManager не создаётся, поэтому settings.ini
            # не появится, если пользователь отменит запуск.
            if first_run:
                load_translations("auto")
                available_languages = [
                    code for code in get_available_languages()
                    if code != "auto"
                ]
                preferred_language = get_resolved_language()
                if preferred_language not in available_languages:
                    preferred_language = "en" if "en" in available_languages else (
                        available_languages[0] if available_languages else "en"
                    )

                selected_language = show_language_dialog(
                    None,
                    available_languages,
                    preferred_language,
                )
                if not selected_language:
                    return False

                load_translations(selected_language)

            self.settings_manager = SettingsManager(storage=storage)

            # Инициализация централизованного логгера.
            from logger import init_logger
            init_logger(self.settings_manager)

            if first_run:
                # Сохраняем выбор языка до приветственного окна. Это важно,
                # даже если пользователь решит заполнить настройки позже.
                settings = self.settings_manager.settings.copy()
                settings["language"] = selected_language
                self.settings_manager.save_settings(settings)

                # Показываем существующий диалог первого запуска целиком
                # на выбранном языке.
                open_settings = show_welcome_dialog(
                    None,
                    settings_manager=self.settings_manager,
                )
                if open_settings:
                    dialog = SettingsDialog(
                        parent=None,
                        title=tr("settings.title"),
                        settings_manager=self.settings_manager,
                    )
                    dialog.ShowModal()
                    dialog.Destroy()

                    # Подхватываем изменения настроек, включая язык.
                    self.settings_manager.load_settings()
                    lang = self.settings_manager.get_option("language", "auto")
                    load_translations(lang)
            else:
                # Для существующей установки используем сохранённый язык.
                lang = self.settings_manager.get_option("language", "auto")
                load_translations(lang)

            # Проверка обновлений при запуске.
            if self.settings_manager.get_option("check_updates_on_start") == "1":
                check_update(None, silent_if_latest=True)

            self.qso_manager = QSOManager(settings_manager=self.settings_manager)
            self.frame = Blind_log(
                None,
                settings_manager=self.settings_manager,
                qso_manager=self.qso_manager,
            )
            self.frame.Show()
            return True
        except Exception as e:
            self._handle_startup_error(e)
            return False


if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()
