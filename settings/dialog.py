"""Accessible wxPython dialog for editing application settings."""

import wx

from localization.i18n import tr, get_available_languages
from settings.manager import SettingsManager
from common.theme import apply_theme
from common.accessibility import install_checkbox_accessibility


class SettingsDialog(wx.Dialog):
    def __init__(self, *args, settings_manager=None, **kwds):
        super(SettingsDialog, self).__init__(*args, **kwds)
        self.settings_manager = settings_manager or SettingsManager()
        self.init_ui()
        self.load_settings()
        apply_theme(self, self.settings_manager.get_option("theme", "system"))

    def init_ui(self):
        # Используем Notebook для вкладок "Общие" и "Интерфейс"
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self)

        # --- General tab ---
        # A scrollable page keeps every setting reachable on small screens
        # and at increased Windows display scaling.
        general_panel = wx.ScrolledWindow(
            self.notebook, style=wx.VSCROLL | wx.TAB_TRAVERSAL
        )
        general_panel.SetScrollRate(0, 15)
        gen_sizer = wx.BoxSizer(wx.VERTICAL)

        # Create each native group box immediately before its own controls.
        # Windows exposes sibling HWNDs to MSAA in creation order, so creating
        # all group boxes up front makes NVDA announce every heading first.
        operator_box = wx.StaticBox(
            general_panel, label=tr("settings.group.operator")
        )
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
        qrz_box = wx.StaticBox(
            general_panel, label=tr("settings.group.qrz")
        )
        self.use_qrz_checkbox = wx.CheckBox(general_panel, label=tr("settings.checkbox.use_qrz"))
        install_checkbox_accessibility(self.use_qrz_checkbox, self)
        self.use_qrz_checkbox.Bind(wx.EVT_CHECKBOX, self.on_use_qrz_toggle)
        self.qrz_username_label = wx.StaticText(general_panel, label=tr("settings.label.qrz_username"))
        self.qrz_username_text = wx.TextCtrl(general_panel)
        self.qrz_password_label = wx.StaticText(general_panel, label=tr("settings.label.qrz_password"))
        self.qrz_password_text = wx.TextCtrl(general_panel, style=wx.TE_PASSWORD)
        self.qrz_password_visible_checkbox = wx.CheckBox(
            general_panel, label=tr("settings.checkbox.show_qrz_password")
        )
        install_checkbox_accessibility(self.qrz_password_visible_checkbox, self)
        self.qrz_password_visible_checkbox.Bind(
            wx.EVT_CHECKBOX, self.on_qrz_password_visibility_toggle
        )
        # Keep QRZ credentials on separate rows so labels and fields do not
        # become cramped when the dialog is narrowed.
        self.qrz_sizer = wx.BoxSizer(wx.VERTICAL)
        username_row = wx.BoxSizer(wx.HORIZONTAL)
        username_row.Add(
            self.qrz_username_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10
        )
        username_row.Add(self.qrz_username_text, 1, wx.EXPAND)
        password_row = wx.BoxSizer(wx.HORIZONTAL)
        password_row.Add(
            self.qrz_password_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10
        )
        password_row.Add(self.qrz_password_text, 1, wx.EXPAND)
        self.qrz_password_row = password_row
        self.qrz_sizer.Add(username_row, 0, wx.EXPAND | wx.BOTTOM, 6)
        self.qrz_sizer.Add(password_row, 0, wx.EXPAND)
        self.qrz_sizer.Add(self.qrz_password_visible_checkbox, 0, wx.TOP, 4)
        timezone_box = wx.StaticBox(
            general_panel, label=tr("settings.group.timezone")
        )
        self.timezone_label = wx.StaticText(general_panel, label=tr("settings.label.timezone"))
        self.timezone_codes = ['UTC', 'custom']
        self.timezone_choice = wx.RadioBox(
            general_panel, label="", choices=[tr("settings.timezone.utc"), tr("settings.timezone.custom")], majorDimension=1, style=wx.RA_SPECIFY_ROWS
        )
        self.custom_timezone_label = wx.StaticText(general_panel, label=tr("settings.label.custom_timezone"))
        self.custom_timezone_text = wx.TextCtrl(general_panel)
        other_box = wx.StaticBox(
            general_panel, label=tr("settings.group.other")
        )
        self.log_enabled_checkbox = wx.CheckBox(general_panel, label=tr("settings.checkbox.logging"))
        install_checkbox_accessibility(self.log_enabled_checkbox, self)
        self.transliterate_checkbox = wx.CheckBox(general_panel, label=tr("settings.checkbox.transliterate"))
        install_checkbox_accessibility(self.transliterate_checkbox, self)
        self.check_updates_checkbox = wx.CheckBox(general_panel, label=tr("settings.checkbox.check_updates"))
        install_checkbox_accessibility(self.check_updates_checkbox, self)
        # Keep related settings in named groups. StaticBoxSizer provides
        # a visible and accessible heading without changing checkbox controls.
        operator_group = wx.StaticBoxSizer(operator_box, wx.VERTICAL)
        operator_fields = [
            (self.call_label, self.call_text),
            (self.operator_name_label, self.operator_name_text),
            (self.my_city_label, self.my_city_text),
            (self.my_qth_label, self.my_qth_text),
            (self.my_rig_label, self.my_rig_text),
            (self.my_lat_label, self.my_lat_text),
            (self.my_lon_label, self.my_lon_text),
        ]
        for label, ctrl in operator_fields:
            row = wx.BoxSizer(wx.HORIZONTAL)
            row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
            row.Add(ctrl, 1, wx.EXPAND)
            operator_group.Add(row, 0, wx.EXPAND | wx.ALL, 5)
        gen_sizer.Add(operator_group, 0, wx.EXPAND | wx.ALL, 5)

        qrz_group = wx.StaticBoxSizer(qrz_box, wx.VERTICAL)
        qrz_group.Add(self.use_qrz_checkbox, 0, wx.ALL, 5)
        qrz_group.Add(self.qrz_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        gen_sizer.Add(qrz_group, 0, wx.EXPAND | wx.ALL, 5)

        timezone_group = wx.StaticBoxSizer(timezone_box, wx.VERTICAL)
        timezone_row = wx.BoxSizer(wx.HORIZONTAL)
        timezone_row.Add(self.timezone_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        timezone_row.Add(self.timezone_choice, 1, wx.EXPAND)
        timezone_group.Add(timezone_row, 0, wx.EXPAND | wx.ALL, 5)
        custom_timezone_row = wx.BoxSizer(wx.HORIZONTAL)
        custom_timezone_row.Add(
            self.custom_timezone_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10
        )
        custom_timezone_row.Add(self.custom_timezone_text, 1, wx.EXPAND)
        timezone_group.Add(custom_timezone_row, 0, wx.EXPAND | wx.ALL, 5)
        gen_sizer.Add(timezone_group, 0, wx.EXPAND | wx.ALL, 5)

        other_group = wx.StaticBoxSizer(other_box, wx.VERTICAL)
        other_group.Add(self.log_enabled_checkbox, 0, wx.ALL, 5)
        other_group.Add(self.transliterate_checkbox, 0, wx.ALL, 5)
        other_group.Add(self.check_updates_checkbox, 0, wx.ALL, 5)
        gen_sizer.Add(other_group, 0, wx.EXPAND | wx.ALL, 5)

        general_panel.SetSizer(gen_sizer)
        general_panel.FitInside()

        # --- Interface tab ---
        interface_panel = wx.ScrolledWindow(
            self.notebook, style=wx.VSCROLL | wx.TAB_TRAVERSAL
        )
        interface_panel.SetScrollRate(0, 15)
        iface_sizer = wx.BoxSizer(wx.VERTICAL)
        self.visible_checkboxes = {}


        # Language and theme are separate groups so their purpose is clear.
        language_group = wx.StaticBoxSizer(
            wx.VERTICAL, interface_panel, tr("settings.group.language")
        )
        lang_row = wx.BoxSizer(wx.HORIZONTAL)
        lang_label = wx.StaticText(interface_panel, label=tr("settings.language"))
        self._lang_codes = get_available_languages()
        lang_display = [
            tr("language.auto") if code == "auto" else code.upper()
            for code in self._lang_codes
        ]
        self.language_choice = wx.Choice(interface_panel, choices=lang_display)
        lang_row.Add(lang_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        lang_row.Add(self.language_choice, 1, wx.EXPAND)
        language_group.Add(lang_row, 0, wx.EXPAND | wx.ALL, 5)
        iface_sizer.Add(language_group, 0, wx.EXPAND | wx.ALL, 5)

        theme_group = wx.StaticBoxSizer(
            wx.VERTICAL, interface_panel, tr("settings.group.theme")
        )
        theme_row = wx.BoxSizer(wx.HORIZONTAL)
        theme_label = wx.StaticText(interface_panel, label=tr("settings.theme"))
        self.theme_values = ["system", "light", "dark"]
        self.theme_choice = wx.Choice(
            interface_panel,
            choices=[
                tr("settings.theme.system"),
                tr("settings.theme.light"),
                tr("settings.theme.dark"),
            ],
        )
        self.theme_choice.SetName(tr("settings.theme"))
        self.theme_choice.Bind(wx.EVT_CHOICE, self.on_theme_change)
        theme_row.Add(theme_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        theme_row.Add(self.theme_choice, 1, wx.EXPAND)
        theme_group.Add(theme_row, 0, wx.EXPAND | wx.ALL, 5)
        iface_sizer.Add(theme_group, 0, wx.EXPAND | wx.ALL, 5)

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
        # Create the visibility group box before its checkboxes so its
        # accessible heading precedes the controls in the Windows/MSAA tree.
        visible_fields_box = wx.StaticBox(
            interface_panel, label=tr("settings.visible_fields")
        )

        # Group optional QSO fields under an explicit heading so the purpose
        # of these checkboxes is clear visually and in screen-reader navigation.
        visible_fields_group = wx.StaticBoxSizer(
            visible_fields_box, wx.VERTICAL
        )
        for fname in getattr(self.settings_manager, 'visible_field_names', []):
            label = field_labels.get(fname, fname.capitalize())
            cb = wx.CheckBox(interface_panel, label=label)
            install_checkbox_accessibility(cb, self)
            visible_fields_group.Add(cb, 0, wx.ALL, 2)
            self.visible_checkboxes[fname] = cb
        iface_sizer.Add(visible_fields_group, 0, wx.EXPAND | wx.ALL, 5)

        interface_tab_order = [self.language_choice, self.theme_choice]
        interface_tab_order.extend(self.visible_checkboxes.values())
        for previous, current in zip(interface_tab_order, interface_tab_order[1:]):
            current.MoveAfterInTabOrder(previous)

        interface_panel.SetSizer(iface_sizer)
        interface_panel.FitInside()

        # Explicitly define keyboard traversal inside each settings page.
        general_tab_order = [
            self.call_text, self.operator_name_text, self.my_city_text,
            self.my_qth_text, self.my_rig_text, self.my_lat_text, self.my_lon_text,
            self.use_qrz_checkbox, self.qrz_username_text, self.qrz_password_text,
            self.qrz_password_visible_checkbox, self.timezone_choice,
            self.custom_timezone_text, self.log_enabled_checkbox,
            self.transliterate_checkbox, self.check_updates_checkbox,
        ]
        for previous, current in zip(general_tab_order, general_tab_order[1:]):
            current.MoveAfterInTabOrder(previous)

        # Добавляем вкладки в Notebook
        self.notebook.AddPage(general_panel, tr("settings.tab.general"))
        self.notebook.AddPage(interface_panel, tr("settings.tab.interface"))

        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 8)

        # Кнопки сохранения/отмены внизу диалога (видны с любой вкладки)
        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.save_btn = wx.Button(self, label=tr("button.save"))
        self.cancel_btn = wx.Button(self, label=tr("button.cancel"))
        bottom_sizer.Add(self.save_btn, 0, wx.RIGHT, 10)
        bottom_sizer.Add(self.cancel_btn, 0)
        main_sizer.Add(bottom_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.SetSizer(main_sizer)
        self.SetSize((760, 650))
        self.SetMinSize((620, 500))
        self.Centre()

        # Привязка событий
        self.save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.Bind(wx.EVT_CLOSE, self._on_close)
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
        except (TypeError, ValueError):
            pass

    def on_use_qrz_toggle(self, event):
        enabled = self.use_qrz_checkbox.GetValue()
        self.qrz_username_label.Enable(enabled)
        self.qrz_username_text.Enable(enabled)
        self.qrz_password_label.Enable(enabled)
        self.qrz_password_text.Enable(enabled)
        self.qrz_password_visible_checkbox.Enable(enabled)

    def on_qrz_password_visibility_toggle(self, event=None):
        """Show or mask the QRZ.ru API password without changing its value."""
        old_control = self.qrz_password_text
        value = old_control.GetValue()
        insertion_point = old_control.GetInsertionPoint()
        selection_start, selection_end = old_control.GetSelection()
        had_focus = old_control.HasFocus()
        style = 0 if self.qrz_password_visible_checkbox.GetValue() else wx.TE_PASSWORD

        # wxMSW cannot change TE_PASSWORD dynamically. Replace the native
        # control in the same sizer slot so the behavior also works on Windows.
        new_control = wx.TextCtrl(
            old_control.GetParent(), style=style, name="qrz_password"
        )
        new_control.SetValue(value)
        new_control.Enable(old_control.IsEnabled())
        self.qrz_password_row.Replace(old_control, new_control)
        self.qrz_password_text = new_control
        old_control.Destroy()
        new_control.MoveAfterInTabOrder(self.qrz_username_text)
        self.qrz_password_visible_checkbox.MoveAfterInTabOrder(new_control)

        new_control.SetInsertionPoint(min(insertion_point, len(value)))
        if selection_start != selection_end:
            new_control.SetSelection(
                min(selection_start, len(value)), min(selection_end, len(value))
            )
        # Replacing a native control changes the preferred size of its row.
        # Recalculate every containing layout and the scrolled page so the
        # following settings never remain clipped at the old virtual height.
        self.qrz_sizer.Layout()
        general_panel = new_control.GetParent()
        general_panel.Layout()
        if isinstance(general_panel, wx.ScrolledWindow):
            general_panel.FitInside()
        self.notebook.Layout()
        self.Layout()
        self.Refresh()

        # The replacement TextCtrl is created after the dialog's initial theme
        # pass, so apply the current palette to it and the surrounding dialog.
        apply_theme(self, self._get_selected_theme())
        if had_focus:
            wx.CallAfter(new_control.SetFocus)

    def _get_selected_theme(self):
        """Return the current preview theme, including unsaved selection."""
        selection = self.theme_choice.GetSelection()
        if 0 <= selection < len(self.theme_values):
            return self.theme_values[selection]
        return self.settings_manager.get_option("theme", "system")

    def on_theme_change(self, event=None):
        """Preview the selected theme immediately, without saving it yet."""
        theme = self._get_selected_theme()
        apply_theme(self, theme)
        parent = self.GetParent()
        if parent is not None:
            apply_theme(parent, theme)
        if event is not None:
            event.Skip()

    def load_settings(self):
        self.call_text.SetValue(self.settings_manager.get_option('call', ''))
        self.operator_name_text.SetValue(self.settings_manager.get_option('operator_name', ''))
        self.my_qth_text.SetValue(self.settings_manager.get_option('my_qth', ''))
        self.my_city_text.SetValue(self.settings_manager.get_option('my_city', ''))
        self.my_rig_text.SetValue(self.settings_manager.get_option('my_rig', ''))
        self.my_lat_text.SetValue(self.settings_manager.get_option('my_lat', ''))
        self.my_lon_text.SetValue(self.settings_manager.get_option('my_lon', ''))
        self.qrz_username_text.SetValue(self.settings_manager.get_option('qrz_username', ''))
        self.qrz_password_text.SetValue(self.settings_manager.get_option('qrz_password', ''))
        timezone_value = self.settings_manager.get_option('timezone', 'UTC')
        # Always use internal code 'custom' (not localized string) for comparison
        if timezone_value == self.timezone_codes[1]:
            self.timezone_choice.SetSelection(1)
        else:
            self.timezone_choice.SetSelection(0)
        self.custom_timezone_text.SetValue(self.settings_manager.get_option('custom_timezone', '+0'))
        self.custom_timezone_text.Enable(timezone_value == self.timezone_codes[1])
        self.use_qrz_checkbox.SetValue(self.settings_manager.get_bool('use_qrz_lookup'))
        self.log_enabled_checkbox.SetValue(self.settings_manager.get_bool('log_enabled'))
        self.transliterate_checkbox.SetValue(self.settings_manager.get_bool('transliterate_russian'))
        self.check_updates_checkbox.SetValue(self.settings_manager.get_bool('check_updates_on_start'))
        self.on_use_qrz_toggle(None)

        # Load language
        lang = self.settings_manager.get_option('language', 'auto')
        idx = self._lang_codes.index(lang) if lang in self._lang_codes else 0
        self.language_choice.SetSelection(idx)

        # Load the selected color theme. Unknown values fall back to system.
        theme = self.settings_manager.get_option("theme", "system")
        theme_idx = self.theme_values.index(theme) if theme in self.theme_values else 0
        self.theme_choice.SetSelection(theme_idx)

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
            'timezone': self.timezone_codes[self.timezone_choice.GetSelection()],
            'custom_timezone': self.custom_timezone_text.GetValue(),
            'use_qrz_lookup': '1' if self.use_qrz_checkbox.GetValue() else '0',
            'log_enabled': '1' if self.log_enabled_checkbox.GetValue() else '0',
            'transliterate_russian': '1' if self.transliterate_checkbox.GetValue() else '0',
            'check_updates_on_start': '1' if self.check_updates_checkbox.GetValue() else '0',
            'auto_temp': '1',  # Draft autosave is always enabled
            'language': self._lang_codes[self.language_choice.GetSelection()],
            'theme': self.theme_values[self.theme_choice.GetSelection()]
                if self.theme_choice.GetSelection() != wx.NOT_FOUND else "system",
        }
        self.settings_manager.save_settings(settings)
        from localization.i18n import load_translations
        load_translations(settings["language"])
        apply_theme(self, settings["theme"])
        parent = self.GetParent()
        if parent is not None:
            apply_theme(parent, settings["theme"])
        # Сохраняем видимость полей
        for fname, cb in getattr(self, 'visible_checkboxes', {}).items():
            # call всегда видим (игнорируем попытки скрыть)
            if fname == 'call':
                self.settings_manager.set_visible_field('call', True)
            else:
                self.settings_manager.set_visible_field(fname, bool(cb.GetValue()))
        self.EndModal(wx.ID_OK)

    def _restore_saved_theme(self):
        """Restore the persisted theme when the settings dialog is cancelled."""
        theme = self.settings_manager.get_option("theme", "system")
        apply_theme(self, theme)
        parent = self.GetParent()
        if parent is not None:
            apply_theme(parent, theme)

    def _cancel_settings(self):
        self._restore_saved_theme()
        if self.IsModal():
            self.EndModal(wx.ID_CANCEL)

    def _on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self._cancel_settings()
            return
        event.Skip()

    def _on_close(self, event):
        self._cancel_settings()

    def on_cancel(self, event):
        self._cancel_settings()

    def on_timezone_change(self, event):
        self.custom_timezone_text.Enable(self.timezone_choice.GetSelection() == 1)

    def _on_next_tab(self, event):
        try:
            sel = self.notebook.GetSelection()
            count = self.notebook.GetPageCount()
            self.notebook.SetSelection((sel + 1) % count)
        except AttributeError:
            pass

    def _on_prev_tab(self, event):
        try:
            sel = self.notebook.GetSelection()
            count = self.notebook.GetPageCount()
            self.notebook.SetSelection((sel - 1) % count)
        except AttributeError:
            pass
