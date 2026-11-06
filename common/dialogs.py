"""Accessible replacement for simple OK-only message boxes."""

import wx

from common.theme import apply_theme
from localization.i18n import tr


def show_accessible_message(parent, message, title, style=wx.OK):
    """Show a readable message in a focused, read-only text control.

    The return value matches wx.MessageBox for an OK-only dialog.
    The style argument is accepted for call-site compatibility; message-box
    icons are intentionally omitted so the message itself is the first
    accessible control.
    """
    dialog = wx.Dialog(
        parent,
        title=title,
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )

    layout = wx.BoxSizer(wx.VERTICAL)
    message_text = wx.TextCtrl(
        dialog,
        value=str(message),
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        name=str(title or "Message"),
    )
    layout.Add(message_text, 1, wx.EXPAND | wx.ALL, 12)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    ok_button = wx.Button(dialog, id=wx.ID_OK, label=tr("button.ok"))
    ok_button.SetDefault()
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
    dialog.Bind(
        wx.EVT_CHAR_HOOK,
        lambda event: dialog.EndModal(wx.ID_OK)
        if event.GetKeyCode() == wx.WXK_ESCAPE
        else event.Skip(),
    )

    try:
        return dialog.ShowModal()
    finally:
        dialog.Destroy()
