"""
Диалог первого запуска: показывается один раз, когда файл настроек
создаётся со значениями по умолчанию.

Текст намеренно двуязычный (сначала английский блок, затем русский) и
не зависит от системы переводов (i18n) - это самый ранний момент
работы программы, когда определение языка ещё не гарантированно
надёжно, поэтому показываем сразу оба варианта.
"""

import webbrowser

import wx

from utils import resource_path


TELEGRAM_URL = "https://t.me/R1BQE"
EMAIL_ADDRESS = "admin@blind-ham.ru"

WELCOME_TEXT = (
    "Welcome to Blind Log!\n"
    "\n"
    "A settings file has been created with default values.\n"
    "\n"
    "For the program to work correctly, please open Settings and "
    "fill in your information: callsign, operator name, QTH, and "
    "other details about your station.\n"
    "\n"
    "If you want to use callsign lookup, enter your QRZ.ru XML API "
    "login and password.\n"
    "\n"
    "Important! Please read the Help first. Press Tab to reach the "
    "\"Help\" button and activate it, or press F1 in the main "
    "program window.\n"
    "\n"
    "If you have questions, contact me on Telegram:\n"
    f"{TELEGRAM_URL}\n"
    "\n"
    "or by email:\n"
    f"{EMAIL_ADDRESS}\n"
    "\n"
    "Press \"Settings\" to open Settings now, or \"OK\" to continue "
    "and fill them in later.\n"
    "\n"
    "\n"
    "Добро пожаловать в Blind Log!\n"
    "\n"
    "Файл настроек был создан со значениями по умолчанию.\n"
    "\n"
    "Для корректной работы программы, пожалуйста, откройте "
    "настройки и заполните информацию о себе: позывной, имя "
    "оператора, QTH и другие данные о вашей станции.\n"
    "\n"
    "Если вы хотите использовать поиск позывных, введите логин и "
    "пароль от XML API QRZ.ru.\n"
    "\n"
    "Внимание! Ознакомьтесь сначала со справкой! При помощи "
    "клавиши Tab перейдите на кнопку «Справка» и нажмите её, или "
    "клавиша F1 в окне программы.\n"
    "\n"
    "Если возникнут вопросы, свяжитесь со мной в Телеграм:\n"
    f"{TELEGRAM_URL}\n"
    "\n"
    "или пишите на почту:\n"
    f"{EMAIL_ADDRESS}\n"
    "\n"
    "Нажмите «Settings / Настройки», чтобы открыть настройки "
    "сейчас, или «OK», чтобы продолжить и заполнить их позже."
)


def _resolve_help_file(settings_manager):
    """Определяет, какой файл справки открыть, той же логикой, что
    и обработчик F1 в основном окне программы (gui.py: on_help)."""
    from i18n import get_resolved_language
    return 'help.htm' if get_resolved_language() == 'ru' else 'help_en.htm'


class WelcomeDialog(wx.Dialog):
    """Диалог первого запуска со ссылками на справку, Telegram, email
    и кнопкой быстрого перехода в настройки."""

    def __init__(self, parent, settings_manager=None):
        super().__init__(parent, title="Blind Log", size=(640, 560))
        self.settings_manager = settings_manager
        self.open_settings_requested = False
        self._init_ui()

    def _init_ui(self):
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.text_ctrl = wx.TextCtrl(
            self,
            value=WELCOME_TEXT,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
        )
        vbox.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_help = wx.Button(self, label="Help / Справка")
        self.btn_telegram = wx.Button(self, label="Telegram / Телеграм")
        self.btn_email = wx.Button(self, label="Email / Почта")
        self.btn_settings = wx.Button(self, label="Settings / Настройки")
        self.btn_ok = wx.Button(self, label="OK")

        for b in (self.btn_help, self.btn_telegram, self.btn_email, self.btn_settings, self.btn_ok):
            btn_sizer.Add(b, 0, wx.RIGHT, 10)

        vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        self.SetSizer(vbox)

        self.btn_help.Bind(wx.EVT_BUTTON, self.on_help)
        self.btn_telegram.Bind(wx.EVT_BUTTON, self.on_telegram)
        self.btn_email.Bind(wx.EVT_BUTTON, self.on_email)
        self.btn_settings.Bind(wx.EVT_BUTTON, self.on_settings)
        self.btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)

        # Tab-порядок: поле текста -> Справка -> Телеграм -> Почта ->
        # Настройки -> OK. wx по умолчанию идёт в порядке создания
        # элементов, что уже соответствует нужному порядку.

        # Фокус сразу на текстовое поле, чтобы NVDA озвучила
        # содержимое сразу при открытии диалога.
        self.Bind(wx.EVT_SHOW, self._on_show)

    def _on_show(self, event):
        event.Skip()
        if event.IsShown():
            self.text_ctrl.SetFocus()

    def on_help(self, event):
        help_file = _resolve_help_file(self.settings_manager)
        help_path = resource_path(help_file)
        webbrowser.open(help_path)

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
    """Показывает диалог первого запуска. Возвращает True, если
    пользователь нажал "Settings / Настройки" (и нужно сразу открыть
    диалог настроек), иначе False."""
    dlg = WelcomeDialog(parent, settings_manager=settings_manager)
    dlg.ShowModal()
    open_settings = dlg.open_settings_requested
    dlg.Destroy()
    return open_settings
