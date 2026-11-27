"""Accessible replacement for simple OK-only message boxes."""

import wx

from common.theme import apply_theme
from localization.i18n import tr


def show_accessible_message(message, title, style=wx.OK, parent=None):
    """Show a readable message in a focused, read-only text control.

    The return value matches wx.MessageBox for an OK-only dialog. A standard
    platform icon is retained when one is requested and available; keyboard
    focus always starts in the read-only message text.
    """
    dialog = wx.Dialog(
        parent,
        title=title,
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )

    layout = wx.BoxSizer(wx.VERTICAL)
    message_row = wx.BoxSizer(wx.HORIZONTAL)

    # Preserve the visual meaning of the original message-box icon when the
    # platform provides a matching standard bitmap.
    art_id = None
    if style & wx.ICON_ERROR:
        art_id = wx.ART_ERROR
    elif style & wx.ICON_WARNING:
        art_id = wx.ART_WARNING
    elif style & wx.ICON_INFORMATION:
        art_id = wx.ART_INFORMATION
    elif style & wx.ICON_QUESTION:
        art_id = wx.ART_QUESTION

    if art_id is not None:
        try:
            bitmap = wx.ArtProvider.GetBitmap(
                art_id, wx.ART_MESSAGE_BOX, wx.Size(32, 32)
            )
            if bitmap.IsOk():
                message_row.Add(
                    wx.StaticBitmap(dialog, bitmap=bitmap),
                    0,
                    wx.ALIGN_TOP | wx.RIGHT,
                    12,
                )
        except Exception:
            # The message remains fully usable if the OS has no stock icon.
            pass

    message_text = wx.TextCtrl(
        dialog,
        value=str(message),
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        name=str(title or "Message"),
    )
    message_row.Add(message_text, 1, wx.EXPAND)
    layout.Add(message_row, 1, wx.EXPAND | wx.ALL, 12)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    ok_button = wx.Button(dialog, id=wx.ID_OK, label=tr("button.ok"))
    ok_button.SetDefault()
    ok_button.Bind(wx.EVT_BUTTON, lambda event: dialog.EndModal(wx.ID_OK))
    buttons.AddStretchSpacer()
    buttons.Add(ok_button, 0, wx.ALL, 8)
    layout.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

    dialog.SetSizer(layout)
    dialog.SetSize((560, 280))
    dialog.SetMinSize((420, 220))
    dialog.Layout()
    dialog.Centre()

    settings_manager = getattr(parent, "settings_manager", None)
    if settings_manager is None:
        app = wx.GetApp()
        settings_manager = (
            getattr(app, "settings_manager", None) if app is not None else None
        )
    theme = (
        settings_manager.get_option("theme", "system")
        if settings_manager is not None
        else "system"
    )
    apply_theme(dialog, theme)

    def focus_message(event):
        if event.IsShown():
            wx.CallAfter(message_text.SetFocus)
            wx.CallAfter(message_text.SetInsertionPoint, 0)
        event.Skip()

    def close_as_ok(event):
        if dialog.IsModal():
            dialog.EndModal(wx.ID_OK)
        else:
            dialog.Destroy()

    dialog.Bind(wx.EVT_SHOW, focus_message)
    dialog.Bind(wx.EVT_CLOSE, close_as_ok)
    def on_char_hook(event):
        key = event.GetKeyCode()
        if key in (wx.WXK_ESCAPE, wx.WXK_RETURN) or key == getattr(wx, "WXK_NUMPAD_ENTER", -1):
            dialog.EndModal(wx.ID_OK)
            return
        event.Skip()

    dialog.Bind(wx.EVT_CHAR_HOOK, on_char_hook)

    try:
        return dialog.ShowModal()
    finally:
        dialog.Destroy()



class AccessibleProgressDialog:
    """Modal progress window with a screen-reader-readable status field."""

    def __init__(self, parent, title, message):
        self.dialog = wx.Dialog(parent, title=title,
                                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.error = None
        layout = wx.BoxSizer(wx.VERTICAL)
        self.message_text = wx.TextCtrl(
            self.dialog, value=str(message),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
            name=str(title or "Progress"),
        )
        layout.Add(self.message_text, 1, wx.EXPAND | wx.ALL, 12)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.ok_button = wx.Button(self.dialog, id=wx.ID_OK, label=tr("button.ok"))
        self.ok_button.SetDefault()
        self.ok_button.Disable()
        self.ok_button.Bind(wx.EVT_BUTTON, lambda event: self.dialog.EndModal(wx.ID_OK))
        buttons.AddStretchSpacer()
        buttons.Add(self.ok_button, 0, wx.ALL, 8)
        layout.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        self.dialog.SetSizer(layout)
        self.dialog.SetSize((560, 260))
        self.dialog.SetMinSize((420, 200))
        self.dialog.Layout()
        self.dialog.Centre()
        manager = getattr(parent, "settings_manager", None)
        apply_theme(self.dialog, manager.get_option("theme", "system") if manager else "system")
        self.dialog.Bind(wx.EVT_SHOW, self._on_show)
        self.dialog.Bind(wx.EVT_CLOSE, self._on_close)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

    def _on_show(self, event):
        if event.IsShown():
            wx.CallAfter(self.message_text.SetFocus)
            wx.CallAfter(self.message_text.SetInsertionPoint, 0)
        event.Skip()

    def _on_close(self, event):
        if self.ok_button.IsEnabled():
            if self.dialog.IsModal():
                self.dialog.EndModal(wx.ID_OK)
            else:
                self.dialog.Destroy()
        else:
            event.Veto()

    def _on_char_hook(self, event):
        key = event.GetKeyCode()
        enter_keys = (wx.WXK_RETURN, getattr(wx, "WXK_NUMPAD_ENTER", -1))
        if key in (wx.WXK_ESCAPE,) + enter_keys:
            if self.ok_button.IsEnabled():
                self.dialog.EndModal(wx.ID_OK)
            return
        event.Skip()

    def set_message(self, message):
        if self.dialog is None:
            return
        self.message_text.ChangeValue(str(message))
        self.message_text.SetInsertionPoint(0)

    def finish(self, message, error=None):
        if self.dialog is None:
            return
        self.error = error
        self.message_text.ChangeValue(str(message))
        self.message_text.SetInsertionPoint(0)
        self.ok_button.Enable()
        self.message_text.SetFocus()

    def show_modal(self):
        return self.dialog.ShowModal()

    def destroy(self):
        if self.dialog is not None:
            self.dialog.Destroy()
            self.dialog = None
