import wx
import configparser
import os
import logging
from i18n import tr

class SettingsManager:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = 'settings.ini'
        self.default_settings = {
            'call': 'R1OAZ',
            'operator_name': 'Иван',
            'my_qth': 'KP50DB',
            'my_city': 'Архангельск',
            'my_rig': 'baofeng',
            'my_lat': '',
            'my_lon': '',
            'timezone': 'UTC',
            'custom_timezone': '+0',
            'qrz_username': '',
            'qrz_password': '',
            'use_qrz_lookup': '0',  # По умолчанию все флажки сняты
            'check_updates_on_start': '0',
            'auto_temp': '0',  # автосохранение сессии
            'log_enabled': '0',
            'language': 'auto',
        }
        # Visible fields defaults (1 = visible, 0 = hidden). CALL always visible.
        self.visible_field_names = [
            'call', 'name', 'city', 'qth', 'freq', 'band', 'mode',
            'rst_received', 'rst_sent', 'comment', 'date', 'time'
        ]
        for fname in self.visible_field_names:
            key = f'visible_{fname}'
            # default: call visible, others visible by default
            self.default_settings.setdefault(key, '1' if fname != 'call' else '1')
        self.settings = {}
        self.load_settings()
        self.apply_logging()

    def load_settings(self):
        if not os.path.exists(self.config_file):
            self.create_default_settings()
            self.show_info_message(
                "Файл настроек был создан со значениями по умолчанию.\n"
                "Если вы хотите использовать поиск позывных на QRZ.ru, отметьте соответствующий флажок и заполните логин и пароль."
            )
        try:
            with open(self.config_file, 'r', encoding='utf-8') as configfile:
                self.config.read_file(configfile)
        except UnicodeDecodeError:
            with open(self.config_file, 'r', encoding='cp1251') as configfile:
                self.config.read_file(configfile)
        if 'Settings' not in self.config:
            self.create_default_settings()
        self.settings = {key: self.config.get('Settings', key, fallback=value)
                         for key, value in self.default_settings.items()}
        self.apply_logging()

    def get_option(self, key, default=None):
        return self.settings.get(key, default)

    def get_visible_fields(self):
        """Вернуть словарь видимости полей: { 'call': True, 'name': False, ... }"""
        res = {}
        for fname in getattr(self, 'visible_field_names', []):
            key = f'visible_{fname}'
            res[fname] = (self.settings.get(key, '1') == '1')
        # Ensure call always visible
        res['call'] = True
        return res

    def set_visible_field(self, field_name: str, visible: bool):
        if not self.config.has_section('Settings'):
            self.config.add_section('Settings')
        key = f'visible_{field_name}'
        val = '1' if visible else '0'
        self.config.set('Settings', key, val)
        with open(self.config_file, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)
        # refresh in-memory settings
        self.settings[key] = val

    def create_default_settings(self):
        self.config['Settings'] = self.default_settings
        with open(self.config_file, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def save_settings(self, settings):
        if not self.config.has_section('Settings'):
            self.config.add_section('Settings')
        for key, value in settings.items():
            self.config.set('Settings', key, value)
        with open(self.config_file, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)
        self.settings = settings.copy()
        self.apply_logging()

    def apply_logging(self):
        # Используем force=True (для Python 3.8+), чтобы перенастроить logging.
        # Это позволяет централизованно управлять логированием из этого класса.
        if self.get_option('log_enabled') == '1':
            logging.basicConfig(filename='blind_log.log', level=logging.INFO,
                                format='%(asctime)s - %(levelname)s - %(message)s',
                                force=True, encoding='utf-8')
        else:
            # Отключаем логирование, удаляя все обработчики из корневого логгера
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)

    def show_info_message(self, message):
        dlg = wx.MessageDialog(None, message, tr("settings.info.title"), wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def show_settings(self, parent=None):
        dialog = SettingsDialog(parent=parent, title=tr("settings.title"), settings_manager=self)
        # гарантируем, что фокус попадёт в список вкладок
        try:
            dialog.notebook.SetFocus()
        except Exception:
            pass
        if dialog.ShowModal() == wx.ID_OK:
            self.load_settings()
        dialog.Destroy()

class SettingsDialog(wx.Dialog):
    def __init__(self, *args, settings_manager=None, **kwds):
        super(SettingsDialog, self).__init__(*args, **kwds)
        self.settings_manager = settings_manager or SettingsManager()
        self.settings = self.settings_manager.settings
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        # Используем Notebook для вкладок "Общие" и "Интерфейс"
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self)

        # --- General tab ---
        general_panel = wx.Panel(self.notebook)
        gen_sizer = wx.BoxSizer(wx.VERTICAL)

        self.call_label = wx.StaticText(general_panel, label=tr("settings.label.operator_callsign"))
        self.call_text = wx.TextCtrl(general_panel)
        self.operator_name_label = wx.StaticText(general_panel, label=tr("settings.label.operator_name"))
        self.operator_name_text = wx.TextCtrl(general_panel)
        self.my_qth_label = wx.StaticText(general_panel, label=tr("settings.label.my_qth"))
        self.my_qth_text = wx.TextCtrl(general_panel)
        self.my_city_label = wx.StaticText(general_panel, label=tr("settings.label.my_city"))
        self.my_city_text = wx.TextCtrl(general_panel)
        self.my_rig_label = wx.StaticText(general_panel, label=tr("settings.label.my_rig"))
        self.my_rig_text = wx.TextCtrl(general_panel)
        self.my_lat_label = wx.StaticText(general_panel, label=tr("settings.label.latitude"))
        self.my_lat_text = wx.TextCtrl(general_panel)
        self.my_lon_label = wx.StaticText(general_panel, label=tr("settings.label.longitude"))
        self.my_lon_text = wx.TextCtrl(general_panel)
        self.use_qrz_checkbox = wx.CheckBox(general_panel, label=tr("settings.checkbox.use_qrz"))
        self.use_qrz_checkbox.Bind(wx.EVT_CHECKBOX, self.on_use_qrz_toggle)
        gen_sizer.Add(self.use_qrz_checkbox, 0, wx.ALL, 5)
        self.qrz_username_label = wx.StaticText(general_panel, label=tr("settings.label.qrz_username"))
        self.qrz_username_text = wx.TextCtrl(general_panel)
        self.qrz_password_label = wx.StaticText(general_panel, label=tr("settings.label.qrz_password"))
        self.qrz_password_text = wx.TextCtrl(general_panel, style=wx.TE_PASSWORD)
        # Группа для логина/пароля QRZ.ru
        self.qrz_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.qrz_sizer.Add(self.qrz_username_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.qrz_sizer.Add(self.qrz_username_text, 1, wx.EXPAND | wx.RIGHT, 10)
        self.qrz_sizer.Add(self.qrz_password_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.qrz_sizer.Add(self.qrz_password_text, 1, wx.EXPAND)
        gen_sizer.Add(self.qrz_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.timezone_label = wx.StaticText(general_panel, label=tr("settings.label.timezone"))
        self.timezone_choice = wx.RadioBox(
            general_panel, label="", choices=[tr("settings.timezone.utc"), tr("settings.timezone.custom")], majorDimension=1, style=wx.RA_SPECIFY_ROWS
        )
        self.custom_timezone_label = wx.StaticText(general_panel, label=tr("settings.label.custom_timezone"))
        self.custom_timezone_text = wx.TextCtrl(general_panel)
        self.log_enabled_checkbox = wx.CheckBox(general_panel, label=tr("settings.checkbox.logging"))
        gen_sizer.Add(self.log_enabled_checkbox, 0, wx.ALL, 5)
        self.check_updates_checkbox = wx.CheckBox(general_panel, label=tr("settings.checkbox.check_updates"))
        gen_sizer.Add(self.check_updates_checkbox, 0, wx.ALL, 5)
        self.auto_temp_checkbox = wx.CheckBox(general_panel, label=tr("settings.checkbox.auto_save"))
        gen_sizer.Add(self.auto_temp_checkbox, 0, wx.ALL, 5)
        fields = [
            (self.call_label, self.call_text),
            (self.operator_name_label, self.operator_name_text),
            (self.my_qth_label, self.my_qth_text),
            (self.my_city_label, self.my_city_text),
            (self.my_rig_label, self.my_rig_text),
            (self.my_lat_label, self.my_lat_text),
            (self.my_lon_label, self.my_lon_text),
            (self.timezone_label, self.timezone_choice),
            (self.custom_timezone_label, self.custom_timezone_text)
        ]
        for label, ctrl in fields:
            row_sizer = wx.BoxSizer(wx.HORIZONTAL)
            row_sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
            row_sizer.Add(ctrl, 1, wx.EXPAND)
            gen_sizer.Add(row_sizer, 0, wx.EXPAND | wx.ALL, 5)
        # кнопки перенесены ниже, чтобы быть общими для всех вкладок
        general_panel.SetSizer(gen_sizer)

        # --- Interface tab ---
        interface_panel = wx.Panel(self.notebook)
        iface_sizer = wx.BoxSizer(wx.VERTICAL)
        self.visible_checkboxes = {}

        # Language selection
        lang_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lang_label = wx.StaticText(interface_panel, label=tr("settings.language"))
        self.language_choice = wx.Choice(interface_panel, choices=[
            tr("language.auto"),
            "English",
            "Русский"
        ])
        self.language_choice.Bind(wx.EVT_CHOICE, self.on_language_change)
        lang_sizer.Add(lang_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        lang_sizer.Add(self.language_choice, 1, wx.EXPAND)
        iface_sizer.Add(lang_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Словарь для перевода названий полей на русский
        field_labels = {
            'call': tr("label.callsign").rstrip(':'),
            'name': tr("label.name").rstrip(':'),
            'city': tr("label.city").rstrip(':'),
            'qth': tr("label.qth"),
            'freq': tr("label.freq").rstrip(':'),
            'band': tr("label.band").rstrip(':'),
            'mode': tr("label.mode").rstrip(':'),
            'rst_received': tr("label.rst_received").rstrip(':'),
            'rst_sent': tr("label.rst_sent").rstrip(':'),
            'comment': tr("label.comment").rstrip(':'),
            'date': tr("label.date").rstrip(':'),
            'time': tr("label.time").rstrip(':'),
        }
        for fname in getattr(self.settings_manager, 'visible_field_names', []):
            label = field_labels.get(fname, fname.capitalize())
            cb = wx.CheckBox(interface_panel, label=label)
            iface_sizer.Add(cb, 0, wx.ALL, 2)
            self.visible_checkboxes[fname] = cb

        interface_panel.SetSizer(iface_sizer)

        # Добавляем вкладки в Notebook
        self.notebook.AddPage(general_panel, tr("settings.tab.general"))
        self.notebook.AddPage(interface_panel, tr("settings.tab.interface"))

        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)

        # Кнопки сохранения/отмены внизу диалога (видны с любой вкладки)
        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.save_btn = wx.Button(self, label=tr("button.save"))
        self.cancel_btn = wx.Button(self, label=tr("button.cancel"))
        bottom_sizer.Add(self.save_btn, 0, wx.RIGHT, 10)
        bottom_sizer.Add(self.cancel_btn, 0)
        main_sizer.Add(bottom_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.SetSizer(main_sizer)

        # Привязка событий
        self.save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.timezone_choice.Bind(wx.EVT_RADIOBOX, self.on_timezone_change)

        # Добавим ускорители Ctrl+Tab / Ctrl+Shift+Tab для переключения вкладок
        self.ID_NEXT = wx.NewIdRef()
        self.ID_PREV = wx.NewIdRef()
        accel_entries = [
            (wx.ACCEL_CTRL, wx.WXK_TAB, self.ID_NEXT),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, wx.WXK_TAB, self.ID_PREV),
        ]
        try:
            accel_tbl = wx.AcceleratorTable([wx.AcceleratorEntry(*entry) for entry in accel_entries])
            self.SetAcceleratorTable(accel_tbl)
            self.Bind(wx.EVT_MENU, self._on_next_tab, id=self.ID_NEXT)
            self.Bind(wx.EVT_MENU, self._on_prev_tab, id=self.ID_PREV)
        except Exception:
            pass

    def on_use_qrz_toggle(self, event):
        enabled = self.use_qrz_checkbox.GetValue()
        self.qrz_username_label.Enable(enabled)
        self.qrz_username_text.Enable(enabled)
        self.qrz_password_label.Enable(enabled)
        self.qrz_password_text.Enable(enabled)

    def on_language_change(self, event):
        selection = self.language_choice.GetSelection()
        lang_codes = ['auto', 'en', 'ru']
        lang = lang_codes[selection]
        from i18n import load_translations
        load_translations(lang)
        # Показать сообщение о перезапуске
        wx.MessageBox(tr("settings.restart_required"), tr("settings.title"), wx.OK | wx.ICON_INFORMATION)

    def load_settings(self):
        self.call_text.SetValue(self.settings['call'])
        self.operator_name_text.SetValue(self.settings['operator_name'])
        self.my_qth_text.SetValue(self.settings['my_qth'])
        self.my_city_text.SetValue(self.settings['my_city'])
        self.my_rig_text.SetValue(self.settings['my_rig'])
        self.my_lat_text.SetValue(self.settings['my_lat'])
        self.my_lon_text.SetValue(self.settings['my_lon'])
        self.qrz_username_text.SetValue(self.settings['qrz_username'])
        self.qrz_password_text.SetValue(self.settings['qrz_password'])
        self.timezone_choice.SetStringSelection(self.settings['timezone'])
        self.custom_timezone_text.SetValue(self.settings['custom_timezone'])
        self.custom_timezone_text.Enable(self.settings['timezone'] == "Задать свой часовой пояс")
        self.use_qrz_checkbox.SetValue(self.settings.get('use_qrz_lookup', '0') == '1')
        self.log_enabled_checkbox.SetValue(self.settings.get('log_enabled', '0') == '1')
        self.check_updates_checkbox.SetValue(self.settings.get('check_updates_on_start', '0') == '1')
        self.auto_temp_checkbox.SetValue(self.settings.get('auto_temp', '0') == '1')
        self.on_use_qrz_toggle(None)

        # Load language
        lang = self.settings.get('language', 'auto')
        if lang == 'auto':
            self.language_choice.SetSelection(0)
        elif lang == 'en':
            self.language_choice.SetSelection(1)
        elif lang == 'ru':
            self.language_choice.SetSelection(2)
        else:
            self.language_choice.SetSelection(0)

        # Устанавливаем состояния чекбоксов видимости полей
        visible = self.settings_manager.get_visible_fields()
        for fname, cb in getattr(self, 'visible_checkboxes', {}).items():
            # ensure CALL always visible and checkbox reflects settings
            if fname == 'call':
                cb.SetValue(True)
                cb.Disable()
            else:
                cb.SetValue(visible.get(fname, True))

    def on_save(self, event):
        settings = {
            'call': self.call_text.GetValue(),
            'operator_name': self.operator_name_text.GetValue(),
            'my_qth': self.my_qth_text.GetValue(),
            'my_city': self.my_city_text.GetValue(),
            'my_rig': self.my_rig_text.GetValue(),
            'my_lat': self.my_lat_text.GetValue(),
            'my_lon': self.my_lon_text.GetValue(),
            'qrz_username': self.qrz_username_text.GetValue(),
            'qrz_password': self.qrz_password_text.GetValue(),
            'timezone': self.timezone_choice.GetStringSelection(),
            'custom_timezone': self.custom_timezone_text.GetValue(),
            'use_qrz_lookup': '1' if self.use_qrz_checkbox.GetValue() else '0',
            'log_enabled': '1' if self.log_enabled_checkbox.GetValue() else '0',
            'check_updates_on_start': '1' if self.check_updates_checkbox.GetValue() else '0',
            'auto_temp': '1' if self.auto_temp_checkbox.GetValue() else '0',
            'language': ['auto', 'en', 'ru'][self.language_choice.GetSelection()],
        }
        self.settings_manager.save_settings(settings)
        # Сохраняем видимость полей
        for fname, cb in getattr(self, 'visible_checkboxes', {}).items():
            # call всегда видим (игнорируем попытки скрыть)
            if fname == 'call':
                self.settings_manager.set_visible_field('call', True)
            else:
                self.settings_manager.set_visible_field(fname, bool(cb.GetValue()))
        self.EndModal(wx.ID_OK)

    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def on_timezone_change(self, event):
        self.custom_timezone_text.Enable(self.timezone_choice.GetSelection() == 1)

    def _on_next_tab(self, event):
        try:
            sel = self.notebook.GetSelection()
            count = self.notebook.GetPageCount()
            self.notebook.SetSelection((sel + 1) % count)
        except Exception:
            pass

    def _on_prev_tab(self, event):
        try:
            sel = self.notebook.GetSelection()
            count = self.notebook.GetPageCount()
            self.notebook.SetSelection((sel - 1) % count)
        except Exception:
            pass