"""
Основной модуль для приложения Blind_log.
"""

import wx

from gui import Blind_log
from qso_manager import QSOManager
from settings import SettingsManager
from updater import check_update
from i18n import load_translations, tr

# Инициализация локализации
# load_translations()  # Убрано, будет вызвано после загрузки настроек

class MyApp(wx.App):
    """
    Класс приложения для Blind_log.
    """
    def OnInit(self):
        """
        Инициализация приложения.
        """
        try:
            self.settings_manager = SettingsManager()
            # Проверка, был ли создан файл настроек (и показать уведомление если нужно)
            settings_file_created = self.settings_manager.load_settings()
            if settings_file_created:
                wx.MessageBox(
                    "Settings file was created with default values.\n"
                    "If you want to use QRZ.ru callsign lookup, check the corresponding box and fill in login and password.",
                    tr("settings.info.title"),
                    wx.OK | wx.ICON_INFORMATION
                )
            # Инициализация централизованного логгера
            from logger import init_logger
            init_logger(self.settings_manager)
            # Загружаем переводы с учетом выбранного языка
            lang = self.settings_manager.get_option('language', 'auto')
            load_translations(lang)
            # Настройка логирования теперь полностью управляется SettingsManager
            # Проверка обновлений при запуске
            if self.settings_manager.get_option('check_updates_on_start') == '1':
                check_update(None, silent_if_latest=True)
            # Создаём бизнес-менеджер отдельно от GUI
            self.qso_manager = QSOManager(settings_manager=self.settings_manager)
            self.frame = Blind_log(None, settings_manager=self.settings_manager, qso_manager=self.qso_manager)
            # автосохранение: предлагаем восстановить данные, если настройка включена
            if self.settings_manager.get_option('auto_temp', '0') == '1':
                temp_data = self.qso_manager.load_temp()
                if isinstance(temp_data, list) and len(temp_data) > 0:
                    dlg = wx.MessageDialog(
                        self.frame,
                        tr("dialog.unsaved_data").format(count=len(temp_data)),
                        tr("dialog.restore_session"),
                        wx.YES_NO | wx.ICON_QUESTION
                    )
                    if dlg.ShowModal() == wx.ID_YES:
                        self.qso_manager.set_qso_list(temp_data)
                        # Обновить отображение журнала через GUIBridge
                        self.frame.gui_bridge.update_journal_display()
                        # после восстановления больше не предлагать
                        try:
                            self.qso_manager.clear_temp()
                        except Exception:
                            pass
                    dlg.Destroy()
            self.frame.Show()
            return True
        except Exception as e:
            import nvda_notify
            nvda_notify.nvda_notify(f"Application startup error: {e}")
            print(f"Application startup error: {e}")
            from logger import log_error
            log_error(f"Application startup error: {e}")
            wx.MessageBox(tr("error.startup").format(error=e), tr("error.title"), wx.OK | wx.ICON_ERROR)
            return False

if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()  