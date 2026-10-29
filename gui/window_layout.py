"""Main window menu bar, notebook and visible-field layout."""

import wx
from i18n import tr
from logger import log_error
from .ids import (
    ID_UPDATE, ID_CHANGELOG, ID_ADD_QSO, ID_EDIT_QSO, ID_DEL_QSO,
    ID_EXPORT_QSO, ID_IMPORT_ADIF, ID_FOCUS_CALL, ID_FOCUS_NAME,
    ID_FOCUS_CITY, ID_FOCUS_QTH, ID_FOCUS_FREQ, ID_FOCUS_RST_REC,
    ID_FOCUS_RST_SENT, ID_CYCLE_MODE, ID_CYCLE_BAND, ID_FOCUS_COMMENT,
    ID_FOCUS_DATE, ID_FOCUS_TIME, ID_CANCEL_EDIT, ID_LOOKUP_CALLSIGN,
    ID_FEEDBACK_EMAIL, ID_FEEDBACK_TELEGRAM,
)


class WindowLayoutMixin:
    def _init_ui(self):
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        file_menu.Append(ID_IMPORT_ADIF, tr("menu.import_adif") + "\tCtrl+O")
        file_menu.Append(wx.ID_PREFERENCES, tr("menu.settings") + "\tCtrl+P")
        file_menu.Append(wx.ID_EXIT, tr("menu.exit") + "\tCtrl+Q")
        menubar.Append(file_menu, tr("menu.file"))

        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, tr("menu.about") + "\tShift+F1")
        help_menu.Append(wx.ID_HELP, tr("menu.help") + "\tF1")
        help_menu.Append(ID_UPDATE, tr("menu.check_updates") + "\tCtrl+U")
        help_menu.Append(ID_CHANGELOG, tr("menu.changelog") + "\tCtrl+F1")
        feedback_menu = wx.Menu()
        feedback_menu.Append(ID_FEEDBACK_EMAIL, tr("menu.feedback.email"))
        feedback_menu.Append(ID_FEEDBACK_TELEGRAM, tr("menu.feedback.telegram"))
        help_menu.AppendSubMenu(feedback_menu, tr("menu.feedback"))
        menubar.Append(help_menu, tr("menu.help"))
        self.SetMenuBar(menubar)

        self.notebook = wx.Notebook(self, style=wx.NB_LEFT)
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_page_changed)

        self.add_panel = wx.Panel(self.notebook)
        self._init_add_qso_ui(self.add_panel)
        self.notebook.AddPage(self.add_panel, tr("tab.add_qso"))

        self.journal_panel = wx.Panel(self.notebook)
        self._init_journal_ui(self.journal_panel)
        self.notebook.AddPage(self.journal_panel, tr("tab.journal"))

        # Привязываем обработчики к правильным идентификаторам
        self.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.on_settings, id=wx.ID_PREFERENCES)
        self.Bind(wx.EVT_MENU, self.on_about, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.on_help, id=wx.ID_HELP)
        self.Bind(wx.EVT_MENU, self.on_feedback_email, id=ID_FEEDBACK_EMAIL)
        self.Bind(wx.EVT_MENU, self.on_feedback_telegram, id=ID_FEEDBACK_TELEGRAM)
        self.Bind(wx.EVT_MENU, self.on_check_updates, id=ID_UPDATE)
        self.Bind(wx.EVT_MENU, self.on_show_changelog, id=ID_CHANGELOG)
        # Привязка обработчиков для ускорителей QSO (используем controller вместо прямых вызовов)
        self.Bind(wx.EVT_MENU, lambda e: self.on_add_qso(), id=ID_ADD_QSO)
        self.Bind(wx.EVT_MENU, self.on_edit_qso, id=ID_EDIT_QSO)
        self.Bind(wx.EVT_MENU, self.on_delete_qso, id=ID_DEL_QSO)
        self.Bind(wx.EVT_MENU, lambda e: self.on_export(e), id=ID_EXPORT_QSO)
        self.Bind(wx.EVT_MENU, self.on_import_adif, id=ID_IMPORT_ADIF)

    def apply_visible_fields(self):
        # Preserve the unfinished form while settings rebuild the controls.
        restore_draft_after_rebuild = bool(getattr(self, "_draft_dirty", False))
        if restore_draft_after_rebuild:
            if self._draft_save_call is not None:
                try:
                    self._draft_save_call.Stop()
                except Exception:
                    pass
                self._draft_save_call = None
            self._save_draft_from_form()
        # Перестроить add_panel и журнал БЕЗ пересоздания столбцов (они должны быть всегда полные)
        try:
            self.add_panel.DestroyChildren()
        except Exception as e:
            log_error(f"Failed to destroy add_panel children: {e}")
        self._init_add_qso_ui(self.add_panel)
        self._bind_draft_events()
        try:
            self.journal_list.DeleteAllItems()
        except Exception as e:
            log_error(f"Failed to clear journal list items: {e}")
        # НЕ вызываем _init_journal_columns() - столбцы уже полные и не должны меняться
        try:
            self._update_journal_from_manager()
        except Exception as e:
            log_error(f"Failed to refresh journal after applying visible fields: {e}")
        # Переинициализируем ускорители после пересборки UI
        self._init_accelerator()
        self._init_time_timer()
        if restore_draft_after_rebuild:
            self._restore_draft()
