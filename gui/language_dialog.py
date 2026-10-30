"""Первичный выбор языка перед созданием пользовательских настроек."""

import wx


class LanguageDialog(wx.Dialog):
    """Небольшой диалог выбора языка интерфейса."""

    def __init__(self, parent, languages, preferred_language="en"):
        super().__init__(parent, title="Choose language")
        self.languages = list(languages)
        self.selected_language = None

        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.language_label = wx.StaticText(
            panel,
            label="Select interface language:",
        )
        self.language_choice = wx.Choice(
            panel,
            choices=[code.upper() for code in self.languages],
        )

        if preferred_language in self.languages:
            self.language_choice.SetSelection(
                self.languages.index(preferred_language)
            )
        elif self.languages:
            self.language_choice.SetSelection(0)

        main_sizer.Add(self.language_label, 0, wx.ALL, 10)
        main_sizer.Add(
            self.language_choice,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            10,
        )

        button_sizer = wx.StdDialogButtonSizer()
        self.ok_button = wx.Button(panel, wx.ID_OK, label="OK")
        self.cancel_button = wx.Button(panel, wx.ID_CANCEL, label="Cancel")
        button_sizer.AddButton(self.ok_button)
        button_sizer.AddButton(self.cancel_button)
        button_sizer.Realize()
        main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(main_sizer)
        dialog_sizer = wx.BoxSizer(wx.VERTICAL)
        dialog_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizerAndFit(dialog_sizer)
        self.SetMinSize((320, -1))

        self.ok_button.Bind(wx.EVT_BUTTON, self._on_ok)
        self.cancel_button.Bind(wx.EVT_BUTTON, self._on_cancel)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.Bind(wx.EVT_SHOW, self._on_show)

    def _on_show(self, event):
        event.Skip()
        if event.IsShown():
            self.language_choice.SetFocus()

    def _on_ok(self, event):
        selection = self.language_choice.GetSelection()
        if 0 <= selection < len(self.languages):
            self.selected_language = self.languages[selection]
            self.EndModal(wx.ID_OK)

    def _on_cancel(self, event):
        self.selected_language = None
        self.EndModal(wx.ID_CANCEL)

    def _on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.selected_language = None
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()


def show_language_dialog(parent, languages, preferred_language="en"):
    """Возвращает код языка или None при отмене."""
    if not languages:
        return None

    dialog = LanguageDialog(parent, languages, preferred_language)
    dialog.ShowModal()
    selected_language = dialog.selected_language
    dialog.Destroy()
    return selected_language
