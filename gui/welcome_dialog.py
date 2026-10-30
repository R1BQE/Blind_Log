"""
Диалог первого запуска. Все надписи берутся из текущей локализации,
которая выбирается отдельным окном до показа этого диалога.
"""

import webbrowser

import wx

from common.utils import resource_path
from localization.i18n import tr


TELEGRAM_URL = "https://t.me/R1BQE"
EMAIL_ADDRESS = "admin@blind-ham.ru"


def _resolve_help_file(settings_manager):
    """Определяет файл справки по текущему языку интерфейса."""
    from localization.i18n import get_resolved_language
    return "help.htm" if get_resolved_language() == "ru" else "help_en.htm"


class WelcomeDialog(wx.Dialog):
    """Диалог первого запуска со ссылками и переходом в настройки."""

    def __init__(self, parent, settings_manager=None):
        super().__init__(parent, title=tr("welcome.title"), size=(640, 560))
        self.settings_manager = settings_manager
        self.open_settings_requested = False
        self._init_ui()

    def _init_ui(self):
        vbox = wx.BoxSizer(wx.VERTICAL)

        message = tr("welcome.message").format(
            telegram=TELEGRAM_URL,
            email=EMAIL_ADDRESS,
        )
        self.text_ctrl = wx.TextCtrl(
            self,
            value=message,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
        )
        vbox.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_help = wx.Button(self, label=tr("welcome.help"))
        self.btn_telegram = wx.Button(self, label=tr("welcome.telegram"))
        self.btn_email = wx.Button(self, label=tr("welcome.email"))
        self.btn_settings = wx.Button(self, label=tr("welcome.settings"))
        self.btn_ok = wx.Button(self, label=tr("welcome.later"))

        for button in (
            self.btn_help,
            self.btn_telegram,
            self.btn_email,
            self.btn_settings,
            self.btn_ok,
        ):
            btn_sizer.Add(button, 0, wx.RIGHT, 10)

        vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        self.SetSizer(vbox)

        self.btn_help.Bind(wx.EVT_BUTTON, self.on_help)
        self.btn_telegram.Bind(wx.EVT_BUTTON, self.on_telegram)
        self.btn_email.Bind(wx.EVT_BUTTON, self.on_email)
        self.btn_settings.Bind(wx.EVT_BUTTON, self.on_settings)
        self.btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)

        # Tab-порядок: текст -> Справка -> Telegram -> Email ->
        # Настройки -> Позже. При открытии NVDA получает фокус на тексте.
        self.Bind(wx.EVT_SHOW, self._on_show)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

    def _on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.open_settings_requested = False
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()

    def _on_show(self, event):
        event.Skip()
        if event.IsShown():
            self.text_ctrl.SetFocus()

    def on_help(self, event):
        help_file = _resolve_help_file(self.settings_manager)
        webbrowser.open(resource_path(f"help/{help_file}"))

    def on_telegram(self, event):
        webbrowser.open(TELEGRAM_URL)

    def on_email(self, event):
        webbrowser.open(f"mailto:{EMAIL_ADDRESS}")

    def on_settings(self, event):
        self.open_settings_requested = True
        self.EndModal(wx.ID_OK)

    def on_ok(self, event):
        self.open_settings_requested = False
        self.EndModal(wx.ID_OK)


def show_welcome_dialog(parent, settings_manager=None):
    """Возвращает True, если пользователь запросил открытие настроек."""
    dialog = WelcomeDialog(parent, settings_manager=settings_manager)
    dialog.ShowModal()
    open_settings = dialog.open_settings_requested
    dialog.Destroy()
    return open_settings
