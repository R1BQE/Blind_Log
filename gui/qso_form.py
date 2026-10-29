"""Construction of the add-QSO form and its accessible controls."""

import wx
import wx.adv

from common.constants import MODES, BANDS, DEFAULT_MODE_INDEX, DEFAULT_BAND_INDEX
from localization.i18n import tr


class QSOFormMixin:
    def _init_add_qso_ui(self, panel):
        # Построение формы добавления QSO: создаём только видимые контролы
        self.controls = {}
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        visible = self.settings_manager.get_visible_fields()

        field_definitions = [
            ('call', tr("label.callsign"), wx.TextCtrl, {'style': wx.TE_PROCESS_ENTER}),
            ('name', tr("label.name"), wx.TextCtrl, {}),
            ('city', tr("label.city"), wx.TextCtrl, {}),
            ('qth', tr("label.qth"), wx.TextCtrl, {}),
            ('freq', tr("label.freq"), wx.TextCtrl, {}),
            ('rst_received', tr("label.rst_received"), wx.TextCtrl, {}),
            ('rst_sent', tr("label.rst_sent"), wx.TextCtrl, {}),
        ]

        for key, label_text, ctrl_class, styles in field_definitions:
            if not visible.get(key, True):
                # remove any existing control reference
                if key in self.controls:
                    del self.controls[key]
                continue
            row_sizer = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(panel, label=label_text)
            ctrl = ctrl_class(panel, **styles)
            self.controls[key] = ctrl
            row_sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            row_sizer.Add(ctrl, 1, wx.EXPAND)
            main_sizer.Add(row_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Enter в поле позывного не перехватываем — он добавляет QSO через акселератор

        # Режим: создаём подпись раньше списка, чтобы объектная навигация
        # NVDA встречала подпись перед соответствующим элементом управления.
        if visible.get('mode', True):
            mode_label = wx.StaticText(panel, label=tr("label.mode"))
        self.controls['mode'] = wx.Choice(panel, choices=MODES)
        self.controls['mode'].SetName(tr("label.mode").rstrip(":"))
        self.controls['mode'].SetSelection(DEFAULT_MODE_INDEX)
        if visible.get('mode', True):
            mode_sizer = wx.BoxSizer(wx.HORIZONTAL)
            mode_sizer.Add(mode_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            mode_sizer.Add(self.controls['mode'], 1, wx.EXPAND)
            main_sizer.Add(mode_sizer, 0, wx.EXPAND | wx.ALL, 5)
        else:
            self.controls['mode'].Hide()

        # Диапазон: тот же порядок создания подписи и списка.
        if visible.get('band', True):
            band_label = wx.StaticText(panel, label=tr("label.band"))
        self.controls['band'] = wx.Choice(panel, choices=BANDS)
        self.controls['band'].SetName(tr("label.band").rstrip(":"))
        self.controls['band'].SetSelection(DEFAULT_BAND_INDEX)
        if visible.get('band', True):
            band_sizer = wx.BoxSizer(wx.HORIZONTAL)
            band_sizer.Add(band_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            band_sizer.Add(self.controls['band'], 1, wx.EXPAND)
            main_sizer.Add(band_sizer, 0, wx.EXPAND | wx.ALL, 5)
        else:
            self.controls['band'].Hide()

        # Комментарий
        if visible.get('comment', True):
            comment_label = wx.StaticText(panel, label=tr("label.comment"))
            self.controls['comment'] = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
            main_sizer.Add(comment_label, 0, wx.TOP | wx.LEFT, 5)
            main_sizer.Add(self.controls['comment'], 1, wx.EXPAND | wx.ALL, 5)

        # Дата и время
        if visible.get('date', True) or visible.get('time', True):
            date_time_sizer = wx.BoxSizer(wx.HORIZONTAL)
            date_label = wx.StaticText(panel, label=tr("label.date"))
            self.controls['date'] = wx.adv.DatePickerCtrl(panel, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY)
            time_label = wx.StaticText(panel, label=tr("label.time"))
            self.controls['time'] = wx.adv.TimePickerCtrl(panel)
            self.controls['date'].Bind(wx.adv.EVT_DATE_CHANGED, self.on_datetime_control_change)
            self.controls['time'].Bind(wx.adv.EVT_TIME_CHANGED, self.on_datetime_control_change)
            date_time_sizer.Add(date_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            date_time_sizer.Add(self.controls['date'], 1, wx.EXPAND | wx.RIGHT, 10)
            date_time_sizer.Add(time_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            date_time_sizer.Add(self.controls['time'], 1, wx.EXPAND)
            main_sizer.Add(date_time_sizer, 0, wx.EXPAND | wx.ALL, 5)
            date_value, time_value = self.controller.get_default_datetime_components()
            self._set_datetime_change_suppression(True)
            self._reset_datetime_override()
            try:
                if date_value:
                    date_obj = wx.DateTime()
                    if date_obj.ParseISODate(date_value):
                        self.controls['date'].SetValue(date_obj)
                if time_value:
                    time_obj = wx.DateTime()
                    if time_obj.ParseTime(time_value):
                        self.controls['time'].SetValue(time_obj)
            except Exception:
                pass
            finally:
                self._set_datetime_change_suppression(False)

        # Кнопка добавления
        self.add_btn = wx.Button(panel, label=tr("button.add_qso"))
        main_sizer.Add(self.add_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(main_sizer)
        # Привязка обработчика кнопки добавления QSO через контроллер
        self.add_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_add_qso())
        if 'call' in self.controls:
            self.controls['call'].SetFocus()
        
        # Установить значения по умолчанию для RST полей
        if 'rst_received' in self.controls:
            self.controls['rst_received'].SetValue("59")
        if 'rst_sent' in self.controls:
            self.controls['rst_sent'].SetValue("59")

