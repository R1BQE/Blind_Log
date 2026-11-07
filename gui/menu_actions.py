"""Menu commands, help dialogs, application exit and feedback actions."""

import wx
import webbrowser
from services.updater import check_update
from common.utils import resource_path, get_version_info
from common.theme import apply_theme
from localization.i18n import tr, get_resolved_language
from logger import log_ui_state, log_error
from gui import welcome_dialog
from .ids import ID_UPDATE, ID_CHANGELOG, ID_FEEDBACK_EMAIL, ID_FEEDBACK_TELEGRAM


class MenuActionsMixin:
    def on_show_changelog(self, event):
        log_ui_state("Changelog opened")
        lang = get_resolved_language()
        changelog_path = resource_path(f"changelog-{lang}.txt")
        try:
            with open(changelog_path, "r", encoding="utf-8") as f:
                changelog_text = f.read()
        except Exception as e:
            self.gui_bridge.show_error(tr("error.title"), f"Failed to open changelog: {e}")
            return

        dlg = wx.Dialog(
            self,
            title=tr("changelog.title"),
            size=(760, 600),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        vbox = wx.BoxSizer(wx.VERTICAL)
        text_ctrl = wx.TextCtrl(
            dlg,
            value=changelog_text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        vbox.Add(text_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        button_sizer = wx.StdDialogButtonSizer()
        close_button = wx.Button(dlg, wx.ID_OK, label=tr("changelog.button.close"))
        close_button.Bind(wx.EVT_BUTTON, lambda evt: dlg.EndModal(wx.ID_OK))
        close_button.SetDefault()
        button_sizer.AddButton(close_button)
        button_sizer.Realize()
        vbox.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        dlg.SetSizer(vbox)
        dlg.SetMinSize((520, 400))
        apply_theme(dlg, self.settings_manager.get_option("theme", "system"))
        dlg.Bind(
            wx.EVT_CHAR_HOOK,
            lambda evt: dlg.EndModal(wx.ID_CANCEL)
            if evt.GetKeyCode() == wx.WXK_ESCAPE else evt.Skip(),
        )
        def focus_changelog_text():
            text_ctrl.SetFocus()
            text_ctrl.SetInsertionPoint(0)

        dlg.Bind(
            wx.EVT_SHOW,
            lambda evt: wx.CallAfter(focus_changelog_text) if evt.IsShown() else None,
        )
        dlg.ShowModal()
        dlg.Destroy()

    def on_settings(self, event):
        # Remember the logical form control before settings can rebuild it.
        focused = wx.Window.FindFocus()
        focused_name = next(
            (name for name, control in self.controls.items() if control is focused),
            None,
        )
        focused_add_button = focused is self.add_btn
        log_ui_state("Settings dialog opened")
        if self.controller.open_settings_dialog():
            try:
                self.refresh_language()
            self.apply_visible_fields()
            except Exception as e:
                log_error(f"Failed to apply visible fields after settings change: {e}")
            else:
                # The old native control may have been destroyed during rebuild.
                # Restore focus to its replacement when that field is still visible.
                replacement = self.controls.get(focused_name)
                if replacement is not None and replacement.IsShown():
                    wx.CallAfter(replacement.SetFocus)
                elif focused_name is not None:
                    # The field may have been hidden by the settings just applied.
                    # Return focus to the notebook instead of a hidden native control.
                    wx.CallAfter(self.notebook.SetFocus)
                elif focused_add_button:
                    # The add button is recreated with the form, so restore focus
                    # to its replacement rather than leaving focus on a destroyed control.
                    wx.CallAfter(self.add_btn.SetFocus)

    def on_exit(self, event):
        """
        Обработчик для пункта меню "Выход".
        Завершает приложение без вызова проверки обновлений.
        """
        self.Close()  # Закрываем главное окно, завершая приложение

    def on_close(self, event):
        """Persist the unfinished form and close; ADIF export is never required."""
        if self._draft_save_call is not None:
            try:
                self._draft_save_call.Stop()
            except Exception:
                pass
            self._draft_save_call = None
        self._save_draft_from_form()
        self.Destroy()

    def on_about(self, event):
        """Show accessible application information and navigation buttons."""
        log_ui_state("About dialog opened")
        version_info = get_version_info()

        about_dialog = wx.Dialog(
            self,
            title=tr("about.title"),
            size=(480, 320),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        about_sizer = wx.BoxSizer(wx.VERTICAL)

        # A read-only multiline control gives NVDA a predictable text-reading
        # target and receives focus when the dialog opens.
        about_text = wx.TextCtrl(
            about_dialog,
            value=(
                f"{tr('about.description')}\n\n"
                f"{tr('about.author')}: {version_info['author']}\n"
                f"{tr('about.version')}: {version_info['version']}"
            ),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        about_sizer.Add(about_text, 1, wx.ALL | wx.EXPAND, 10)

        # Keep the requested keyboard order: information, website, close.
        site_button = wx.Button(about_dialog, label=tr("about.button.site"))
        site_button.Bind(
            wx.EVT_BUTTON,
            lambda evt: webbrowser.open("https://github.com/r1oaz/Blind_Log"),
        )
        close_button = wx.Button(about_dialog, wx.ID_OK, label=tr("about.button.close"))
        close_button.Bind(wx.EVT_BUTTON, lambda evt: about_dialog.EndModal(wx.ID_OK))
        close_button.SetDefault()

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.AddStretchSpacer()
        button_sizer.Add(site_button, 0, wx.RIGHT, 8)
        button_sizer.Add(close_button, 0)
        about_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        about_dialog.SetSizer(about_sizer)
        about_dialog.Bind(
            wx.EVT_CHAR_HOOK,
            lambda evt: about_dialog.EndModal(wx.ID_CANCEL)
            if evt.GetKeyCode() == wx.WXK_ESCAPE else evt.Skip(),
        )
        about_dialog.SetMinSize((420, 280))
        about_dialog.Layout()
        apply_theme(about_dialog, self.settings_manager.get_option("theme", "system"))
        def focus_about_text():
            about_text.SetFocus()
            about_text.SetInsertionPoint(0)

        about_dialog.Bind(
            wx.EVT_SHOW,
            lambda evt: wx.CallAfter(focus_about_text) if evt.IsShown() else None,
        )
        about_dialog.ShowModal()
        about_dialog.Destroy()

    def on_help(self, event):
        # Открытие файла справки в зависимости от выбранного языка
        help_file = 'help.htm' if get_resolved_language() == 'ru' else 'help_en.htm'
        help_path = resource_path(f"help/{help_file}")
        webbrowser.open(help_path)

    def on_feedback_email(self, event):
        webbrowser.open(f"mailto:{welcome_dialog.EMAIL_ADDRESS}")

    def on_feedback_telegram(self, event):
        webbrowser.open(welcome_dialog.TELEGRAM_URL)

    def on_check_updates(self, event):
        check_update(self)  # вызываем функцию и передаём главное окно
