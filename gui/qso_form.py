"""Construction of the add-QSO form and its accessible controls."""

import wx
import wx.adv

from common.constants import MODES, BANDS, DEFAULT_MODE_INDEX, DEFAULT_BAND_INDEX
from localization.i18n import tr


class QSOFormMixin:
    def _init_add_qso_ui(self, panel):
        # Build only visible controls. Sizers let text fields use the available
        # width, while FromDIP keeps minimum dimensions and spacing DPI-aware.
        self.controls = {}
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        visible = self.settings_manager.get_visible_fields()
        dip = panel.FromDIP
        label_width = dip(135)
        row_margin = dip(5)
        label_gap = dip(8)

        def add_labeled_row(key, label, control, min_width=None):
            label.SetMinSize((label_width, -1))
            if min_width is not None:
                control.SetMinSize((dip(min_width), -1))

            row_sizer = wx.BoxSizer(wx.HORIZONTAL)
            row_sizer.Add(
                label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, label_gap
            )
            row_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
            main_sizer.Add(
                row_sizer, 0,
                wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
                row_margin,
            )
            self.controls[key] = control

        field_definitions = [
            ('call', tr("label.callsign"), wx.TE_PROCESS_ENTER, 180),
            ('name', tr("label.name"), 0, 160),
            ('city', tr("label.city"), 0, 160),
            ('qth', tr("label.qth"), 0, 140),
            ('freq', tr("label.freq"), 0, 120),
            ('rst_received', tr("label.rst_received"), 0, 90),
            ('rst_sent', tr("label.rst_sent"), 0, 90),
        ]

        for key, label_text, style, min_width in field_definitions:
            if not visible.get(key, True):
                self.controls.pop(key, None)
                continue

            label = wx.StaticText(panel, label=label_text)
            ctrl = wx.TextCtrl(panel, style=style)
            add_labeled_row(key, label, ctrl, min_width)

        # Enter in the callsign field is handled by the existing accelerator.

        # Create labels before choices to preserve NVDA object navigation order.
        if visible.get('mode', True):
            mode_label = wx.StaticText(panel, label=tr("label.mode"))
        self.controls['mode'] = wx.Choice(panel, choices=MODES)
        self.controls['mode'].SetName(tr("label.mode").rstrip(":"))
        self.controls['mode'].SetSelection(DEFAULT_MODE_INDEX)
        if visible.get('mode', True):
            add_labeled_row('mode', mode_label, self.controls['mode'], 120)
        else:
            self.controls['mode'].Hide()

        if visible.get('band', True):
            band_label = wx.StaticText(panel, label=tr("label.band"))
        self.controls['band'] = wx.Choice(panel, choices=BANDS)
        self.controls['band'].SetName(tr("label.band").rstrip(":"))
        self.controls['band'].SetSelection(DEFAULT_BAND_INDEX)
        if visible.get('band', True):
            add_labeled_row('band', band_label, self.controls['band'], 120)
        else:
            self.controls['band'].Hide()

        if visible.get('comment', True):
            comment_label = wx.StaticText(panel, label=tr("label.comment"))
            self.controls['comment'] = wx.TextCtrl(
                panel,
                style=wx.TE_MULTILINE,
                size=(-1, dip(100)),
            )
            self.controls['comment'].SetMinSize((dip(240), dip(100)))
            main_sizer.Add(
                comment_label, 0,
                wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT | wx.TOP,
                row_margin,
            )
            main_sizer.Add(
                self.controls['comment'], 1,
                wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
                row_margin,
            )

        # Date and time controls are placed on separate adaptive rows so they
        # remain usable when the application window is narrow.
        show_date = visible.get('date', True)
        show_time = visible.get('time', True)
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
            add_labeled_row('date', date_label, date_control)

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
            add_labeled_row('time', time_label, time_control)

        if show_date or show_time:
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

        self.add_btn = wx.Button(panel, label=tr("button.add_qso"))
        main_sizer.Add(
            self.add_btn, 0,
            wx.ALIGN_CENTER_HORIZONTAL | wx.ALL,
            dip(10),
        )

        panel.SetSizer(main_sizer, True)
        panel.Layout()
        if isinstance(panel, wx.ScrolledWindow):
            panel.FitInside()

        self.add_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_add_qso())

        if 'rst_received' in self.controls:
            self.controls['rst_received'].SetValue("59")
        if 'rst_sent' in self.controls:
            self.controls['rst_sent'].SetValue("59")
