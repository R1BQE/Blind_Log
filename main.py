"""
Основной модуль для приложения Blind_log.
"""

import wx

from gui import Blind_log
from journal.manager import QSOManager
from settings.manager import SettingsManager
from settings.dialog import SettingsDialog
from services.updater import check_update
from gui.welcome_dialog import show_welcome_dialog
from localization.i18n import load_translations, tr

# Инициализация локализации

class MyApp(wx.App):
    """
    Класс приложения для Blind_log.
"""             
    def _handle_startup_error(self, error):
        from accessibility import nvda_notify
        from logger import log_error

        log_error(f"Application startup error: {error}")
        nvda_notify.nvda_notify(str(error))
        wx.MessageBox(tr("error.startup").format(error=error), tr("error.title"), wx.OK | wx.ICON_ERROR)

    def OnInit(self):
        """
        Инициализация приложения.
        """
        try:
            self.settings_manager = SettingsManager()
            # Инициализация централизованного логгера
            from logger import init_logger
            init_logger(self.settings_manager)
            # Загружаем переводы с учетом выбранного языка
            lang = self.settings_manager.get_option('language', 'auto')
            load_translations(lang)
            # Проверка, был ли создан файл настроек (флаг сохранён в
            # SettingsManager при инициализации - см. settings.py).
            # Повторный вызов load_settings() здесь не нужен и был бы
            # ошибочным: к этому моменту файл уже существует, и такой
            # вызов всегда вернул бы False.
            if getattr(self.settings_manager, "was_just_created", False):
                open_settings = show_welcome_dialog(None, settings_manager=self.settings_manager)
                if open_settings:
                    dialog = SettingsDialog(
                        parent=None,
                        title=tr("settings.title"),
                        settings_manager=self.settings_manager,
                    )
                    dialog.ShowModal()
                    dialog.Destroy()
                    # Подхватываем то, что пользователь мог изменить
                    # (включая язык) перед созданием основного окна.
                    self.settings_manager.load_settings()
                    lang = self.settings_manager.get_option('language', 'auto')
                    load_translations(lang)
            # Настройка логирования теперь полностью управляется SettingsManager
            # Проверка обновлений при запуске
            if self.settings_manager.get_option('check_updates_on_start') == '1':
                check_update(None, silent_if_latest=True)
            # Создаём бизнес-менеджер отдельно от GUI
            self.qso_manager = QSOManager(settings_manager=self.settings_manager)
            self.frame = Blind_log(None, settings_manager=self.settings_manager, qso_manager=self.qso_manager)
            # QSO records load from SQLite; the GUI restores only the unfinished form.
            self.frame.Show()
            return True
        except Exception as e:
            self._handle_startup_error(e)
            return False

if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()  