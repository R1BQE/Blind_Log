"""Keyboard shortcuts, focus helpers and accessible announcements."""

import wx
from i18n import tr
from logger import log_error
from .ids import (
    ID_ADD_QSO, ID_EDIT_QSO, ID_DEL_QSO, ID_EXPORT_QSO, ID_IMPORT_ADIF,
    ID_FOCUS_CALL, ID_FOCUS_NAME, ID_FOCUS_CITY, ID_FOCUS_QTH, ID_FOCUS_FREQ,
    ID_FOCUS_RST_REC, ID_FOCUS_RST_SENT, ID_CYCLE_MODE, ID_CYCLE_BAND,
    ID_FOCUS_COMMENT, ID_FOCUS_DATE, ID_FOCUS_TIME, ID_CANCEL_EDIT, ID_QRZ_LOOKUP,
    ID_CHANGELOG, ID_UPDATE,
)


class KeyboardMixin:
    def speak(self, text):
        """Озвучить текст через NVDA"""
        try:
            import nvda_notify
            nvda_notify.nvda_controller.speak(text)
        except Exception as e:
            log_error(f"Failed to speak text via NVDA: {e}")

    def focus_field(self, key, label_key):
        """Установить фокус на поле или озвучить, что оно скрыто"""
        if key not in self.controls:
            # Поле скрыто
            label = tr(label_key)
            self.speak(tr("field.hidden").format(field=label))
            return
        
        widget = self.controls[key]
        widget.SetFocus()

    def _init_accelerator(self):
        # Используем кастомные IDs для ускорителей, чтобы они работали даже после перестроения UI
        accel_entries = [
            (wx.ACCEL_NORMAL, wx.WXK_RETURN, ID_ADD_QSO),
            (wx.ACCEL_CTRL, ord('E'), ID_EDIT_QSO),
            (wx.ACCEL_CTRL, ord('S'), ID_EXPORT_QSO),
            (wx.ACCEL_CTRL, ord('O'), ID_IMPORT_ADIF),
            (wx.ACCEL_NORMAL, wx.WXK_DELETE, ID_DEL_QSO),
            (wx.ACCEL_SHIFT, wx.WXK_F1, wx.ID_ABOUT),
            (wx.ACCEL_NORMAL, wx.WXK_F1, wx.ID_HELP),
            (wx.ACCEL_CTRL, wx.WXK_F1, ID_CHANGELOG),
            (wx.ACCEL_CTRL, ord('U'), ID_UPDATE),
            # Новые горячие клавиши для полей
            (wx.ACCEL_ALT, ord('C'), ID_FOCUS_CALL),
            (wx.ACCEL_ALT, ord('N'), ID_FOCUS_NAME),
            (wx.ACCEL_ALT, ord('T'), ID_FOCUS_CITY),
            (wx.ACCEL_ALT, ord('Q'), ID_FOCUS_QTH),
            (wx.ACCEL_ALT, ord('F'), ID_FOCUS_FREQ),
            (wx.ACCEL_ALT, ord('R'), ID_FOCUS_RST_REC),
            (wx.ACCEL_ALT, ord('S'), ID_FOCUS_RST_SENT),
            (wx.ACCEL_ALT, ord('M'), ID_CYCLE_MODE),
            (wx.ACCEL_ALT, ord('B'), ID_CYCLE_BAND),
            (wx.ACCEL_ALT, ord('O'), ID_FOCUS_COMMENT),
            (wx.ACCEL_ALT, ord('D'), ID_FOCUS_DATE),
            (wx.ACCEL_ALT, ord('I'), ID_FOCUS_TIME),
            (wx.ACCEL_NORMAL, wx.WXK_ESCAPE, ID_CANCEL_EDIT),
            (wx.ACCEL_CTRL, wx.WXK_RETURN, ID_QRZ_LOOKUP),
        ]
        accel_tbl = wx.AcceleratorTable([wx.AcceleratorEntry(*entry) for entry in accel_entries])
        self.SetAcceleratorTable(accel_tbl)

        # Unbind старые binds перед новыми
        for id_ in [ID_FOCUS_CALL, ID_FOCUS_NAME, ID_FOCUS_CITY, ID_FOCUS_QTH, ID_FOCUS_FREQ,
                    ID_FOCUS_RST_REC, ID_FOCUS_RST_SENT, ID_CYCLE_MODE, ID_CYCLE_BAND,
                    ID_FOCUS_COMMENT, ID_FOCUS_DATE, ID_FOCUS_TIME]:
            self.Unbind(wx.EVT_MENU, id=id_)

        # Binds для горячих клавиш полей
        # Обычные поля: проверяем видимость и озвучиваем "скрыто"
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('call', "label.callsign"), id=ID_FOCUS_CALL)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('name', "label.name"), id=ID_FOCUS_NAME)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('city', "label.city"), id=ID_FOCUS_CITY)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('qth', "label.qth"), id=ID_FOCUS_QTH)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('freq', "label.freq"), id=ID_FOCUS_FREQ)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('rst_received', "label.rst_received"), id=ID_FOCUS_RST_REC)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('rst_sent', "label.rst_sent"), id=ID_FOCUS_RST_SENT)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('comment', "label.comment"), id=ID_FOCUS_COMMENT)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('date', "label.date"), id=ID_FOCUS_DATE)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('time', "label.time"), id=ID_FOCUS_TIME)
        
        # Отмена редактирования по Escape
        self.Bind(wx.EVT_MENU, self.on_cancel_edit, id=ID_CANCEL_EDIT)
        # Поиск по QRZ по Ctrl+Enter
        self.Bind(wx.EVT_MENU, self._on_qrz_lookup_accel, id=ID_QRZ_LOOKUP)

        # ComboBox: всегда работают, независимо от видимости
        self.Bind(wx.EVT_MENU, lambda evt: self.cycle_choice('mode'), id=ID_CYCLE_MODE)
        self.Bind(wx.EVT_MENU, lambda evt: self.cycle_choice('band'), id=ID_CYCLE_BAND)

    def cycle_choice(self, key):
        choice = self.controls[key]
        current = choice.GetSelection()
        count = choice.GetCount()
        if count > 0:
            new_index = (current + 1) % count
            choice.SetSelection(new_index)
            # Озвучиваем новое значение через NVDA
            value = choice.GetString(new_index)
            label_key = f"field.{key}"
            label = tr(label_key)
            import nvda_notify
            nvda_notify.nvda_controller.speak(f"{label}: {value}")
