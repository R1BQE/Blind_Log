"""Construction of the add-QSO form and its accessible controls."""

import wx
import wx.adv

from common.constants import MODES, BANDS, DEFAULT_MODE_INDEX, DEFAULT_BAND_INDEX
from localization.i18n import tr


class QSOFormMixin:
    def _init_add_qso_ui(self, panel):
        # Построение формы добавления QSO: создаём только видимые контролы.
        # Фиксированные размеры и центрирование не дают коротким полям
        # растягиваться на всю ширину большого окна.
        self.controls = {}
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        visible = self.settings_manager.get_visible_fields()
        label_width = 135

        field_definitions = [
            ('call', tr("label.callsign"), wx.TextCtrl,
             {'style': wx.TE_PROCESS_ENTER, 'size': (360, -1)}),
            ('name', tr("label.name"), wx.TextCtrl, {'size': (320, -1)}),
            ('city', tr("label.city"), wx.TextCtrl, {'size': (320, -1)}),
            ('qth', tr("label.qth"), wx.TextCtrl, {'size': (240, -1)}),
            ('freq', tr("label.freq"), wx.TextCtrl, {'size': (170, -1)}),
            ('rst_received', tr("label.rst_received"), wx.TextCtrl, {'size': (100, -1)}),
            ('rst_sent', tr("label.rst_sent"), wx.TextCtrl, {'size': (100, -1)}),
        ]

        for key, label_text, ctrl_class, styles in field_definitions:
            if not visible.get(key, True):
                self.controls.pop(key, None)
                continue

            row_sizer = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(panel, label=label_text)
            label.SetMinSize((label_width, -1))
            ctrl = ctrl_class(panel, **styles)
            self.controls[key] = ctrl
            row_sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            row_sizer.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
            main_sizer.Add(
                row_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5
            )

        # Enter в поле позывного не перехватываем — он добавляет QSO через акселератор.

        # Режим: подпись создаётся раньше списка для корректной объектной
        # навигации NVDA.
        if visible.get('mode', True):
            mode_label = wx.StaticText(panel, label=tr("label.mode"))
            mode_label.SetMinSize((label_width, -1))
        self.controls['mode'] = wx.Choice(panel, choices=MODES)
        self.controls['mode'].SetName(tr("label.mode").rstrip(":"))
        self.controls['mode'].SetSelection(DEFAULT_MODE_INDEX)
        if visible.get('mode', True):
            mode_sizer = wx.BoxSizer(wx.HORIZONTAL)
            mode_sizer.Add(
                mode_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8
            )
            mode_sizer.Add(self.controls['mode'], 0, wx.ALIGN_CENTER_VERTICAL)
            self.controls['mode'].SetMinSize((160, -1))
            main_sizer.Add(
                mode_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5
            )
        else:
            self.controls['mode'].Hide()

        # Диапазон.
        if visible.get('band', True):
            band_label = wx.StaticText(panel, label=tr("label.band"))
            band_label.SetMinSize((label_width, -1))
        self.controls['band'] = wx.Choice(panel, choices=BANDS)
        self.controls['band'].SetName(tr("label.band").rstrip(":"))
        self.controls['band'].SetSelection(DEFAULT_BAND_INDEX)
        if visible.get('band', True):
            band_sizer = wx.BoxSizer(wx.HORIZONTAL)
            band_sizer.Add(
                band_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8
            )
            band_sizer.Add(self.controls['band'], 0, wx.ALIGN_CENTER_VERTICAL)
            self.controls['band'].SetMinSize((160, -1))
            main_sizer.Add(
                band_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5
            )
        else:
            self.controls['band'].Hide()

        # Комментарий: широкое, но ограниченное по размеру поле.
        if visible.get('comment', True):
            comment_label = wx.StaticText(panel, label=tr("label.comment"))
            self.controls['comment'] = wx.TextCtrl(
                panel, style=wx.TE_MULTILINE, size=(620, 100)
            )
            main_sizer.Add(
                comment_label, 0,
                wx.ALIGN_CENTER_HORIZONTAL | wx.TOP | wx.LEFT, 5
            )
            main_sizer.Add(
                self.controls['comment'], 0,
                wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5
            )

        # Date and time controls are created only when enabled. Keeping hidden
        # native controls in self.controls makes timers and keyboard commands
        # treat disabled fields as active.
        show_date = visible.get('date', True)
        show_time = visible.get('time', True)
        if show_date or show_time:
            date_time_sizer = wx.BoxSizer(wx.HORIZONTAL)
            if show_date:
                date_label = wx.StaticText(panel, label=tr("label.date"))
                date_control = wx.adv.DatePickerCtrl(
                    panel, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY
                )
                self.controls['date'] = date_control
                date_control.Bind(
                    wx.adv.EVT_DATE_CHANGED, self.on_datetime_control_change
                )
                date_control.Bind(
                    wx.EVT_SET_FOCUS,
                    lambda event: self.on_datetime_control_focus(event, "date"),
                )
                date_time_sizer.Add(
                    date_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5
                )
                date_time_sizer.Add(
                    date_control, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10
                )

            if show_time:
                time_label = wx.StaticText(panel, label=tr("label.time"))
                time_control = wx.adv.TimePickerCtrl(panel)
                self.controls['time'] = time_control
                time_control.Bind(
                    wx.adv.EVT_TIME_CHANGED, self.on_datetime_control_change
                )
                time_control.Bind(
                    wx.EVT_SET_FOCUS,
                    lambda event: self.on_datetime_control_focus(event, "time"),
                )
                date_time_sizer.Add(
                    time_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5
                )
                date_time_sizer.Add(time_control, 0, wx.ALIGN_CENTER_VERTICAL)

            main_sizer.Add(
                date_time_sizer, 0,
                wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5
            )
            date_value, time_value = self.controller.get_default_datetime_components()
            self._set_datetime_change_suppression(True)
            self._reset_datetime_override()
            try:
                if show_date and date_value:
                    date_obj = wx.DateTime()
                    if date_obj.ParseISODate(date_value):
                        self.controls['date'].SetValue(date_obj)
                if show_time and time_value:
                    time_obj = wx.DateTime()
                    if time_obj.ParseTime(time_value):
                        self.controls['time'].SetValue(time_obj)
            except Exception:
                pass
            finally:
                self._set_datetime_change_suppression(False)

        # Кнопка находится сразу под формой и выровнена по её центру.
        self.add_btn = wx.Button(panel, label=tr("button.add_qso"))
        main_sizer.Add(
            self.add_btn, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10
        )

        panel.SetSizer(main_sizer, True)
        panel.Layout()
        if isinstance(panel, wx.ScrolledWindow):
            panel.FitInside()

        self.add_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_add_qso())

        # Значения RST по умолчанию.
        if 'rst_received' in self.controls:
            self.controls['rst_received'].SetValue("59")
        if 'rst_sent' in self.controls:
            self.controls['rst_sent'].SetValue("59")
