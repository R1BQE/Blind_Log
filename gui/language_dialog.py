"""Первичный выбор языка перед созданием пользовательских настроек."""

import wx

from localization.i18n import tr


class LanguageDialog(wx.Dialog):
    """Небольшой диалог выбора языка интерфейса."""

    def __init__(self, parent, languages, preferred_language="en"):
        super().__init__(parent, title=tr("language.dialog.title"))
        self.languages = list(languages)
        self.selected_language = None

        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # A read-only text control makes the instruction a reliable initial
        # focus target for screen readers before the language choice.
        self.instruction_text = wx.TextCtrl(
            panel,
            value=tr("language.dialog.prompt"),
            style=wx.TE_READONLY,
        )
        self.language_choice = wx.Choice(
            panel,
            choices=[code.upper() for code in self.languages],
            name=tr("language.dialog.prompt"),
        )

        if preferred_language in self.languages:
            self.language_choice.SetSelection(
                self.languages.index(preferred_language)
            )
        elif self.languages:
            self.language_choice.SetSelection(0)

        main_sizer.Add(self.instruction_text, 0, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(
            self.language_choice,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            10,
        )

        button_sizer = wx.StdDialogButtonSizer()
        self.ok_button = wx.Button(panel, wx.ID_OK, label=tr("button.ok"))
        self.cancel_button = wx.Button(panel, wx.ID_CANCEL, label=tr("button.cancel"))
        button_sizer.AddButton(self.ok_button)
        button_sizer.AddButton(self.cancel_button)
        button_sizer.Realize()
        main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(main_sizer)
        dialog_sizer = wx.BoxSizer(wx.VERTICAL)
        dialog_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizerAndFit(dialog_sizer)
        self.SetMinSize((320, -1))

        self.ok_button.SetDefault()
        self.ok_button.Bind(wx.EVT_BUTTON, self._on_ok)
        self.cancel_button.Bind(wx.EVT_BUTTON, self._on_cancel)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.Bind(wx.EVT_SHOW, self._on_show)

    def _on_show(self, event):
        event.Skip()
        if event.IsShown():
            self.instruction_text.SetFocus()
            self.instruction_text.SetInsertionPoint(0)

    def _on_ok(self, event):
        selection = self.language_choice.GetSelection()
        if 0 <= selection < len(self.languages):
            self.selected_language = self.languages[selection]
            self.EndModal(wx.ID_OK)

    def _on_cancel(self, event):
        self.selected_language = None
        self.EndModal(wx.ID_CANCEL)

    def _on_char_hook(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            self.selected_language = None
            self.EndModal(wx.ID_CANCEL)
            return
        if key in (wx.WXK_RETURN, getattr(wx, "WXK_NUMPAD_ENTER", -1)):
            if wx.Window.FindFocus() in (self.instruction_text, self.language_choice):
                self._on_ok(None)
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
