"""Main window menu bar, notebook and visible-field layout."""

import wx
from localization.i18n import tr, get_resolved_language
from logger import log_error
from common.theme import apply_theme
from common.constants import JOURNAL_COLUMNS, QSO_FIELD_NAMES
from .ids import (
    ID_UPDATE, ID_CHANGELOG, ID_ADD_QSO, ID_EDIT_QSO, ID_DEL_QSO,
    ID_EXPORT_QSO, ID_IMPORT_ADIF, ID_FOCUS_CALL, ID_FOCUS_NAME,
    ID_FOCUS_CITY, ID_FOCUS_QTH, ID_FOCUS_FREQ, ID_FOCUS_RST_REC,
    ID_FOCUS_RST_SENT, ID_CYCLE_MODE, ID_CYCLE_BAND, ID_FOCUS_COMMENT,
    ID_FOCUS_DATE, ID_FOCUS_TIME, ID_CANCEL_EDIT, ID_LOOKUP_CALLSIGN,
    ID_FEEDBACK_EMAIL, ID_FEEDBACK_TELEGRAM,
)


_MENU_MNEMONICS = {
    "ru": {
        "menu.file": "Ф", "menu.help": "П",
        "menu.export_adif": "Э", "menu.import_adif": "И",
        "menu.settings": "Н", "menu.exit": "В",
        "menu.about": "О", "menu.help_item": "Р", "menu.check_updates": "П",
        "menu.changelog": "Ч", "menu.feedback": "С",
        "menu.feedback.email": "Н", "menu.feedback.telegram": "Т",
    },
    "en": {
        "menu.file": "F", "menu.help": "H",
        "menu.export_adif": "E", "menu.import_adif": "I",
        "menu.settings": "S", "menu.exit": "X",
        "menu.about": "A", "menu.help_item": "H", "menu.check_updates": "C",
        "menu.changelog": "N", "menu.feedback": "F",
        "menu.feedback.email": "E", "menu.feedback.telegram": "T",
    },
}


def _menu_label(key):
    """Add a menu-only mnemonic without polluting translated text values."""
    label = tr(key)
    mnemonic = _MENU_MNEMONICS.get(get_resolved_language(), {}).get(key)
    if not mnemonic:
        return label
    index = label.casefold().find(mnemonic.casefold())
    if index < 0:
        return label
    return label[:index] + "&" + label[index:]


class WindowLayoutMixin:
    def _build_menu_bar(self):
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        file_menu.Append(ID_EXPORT_QSO, _menu_label("menu.export_adif") + "\tCtrl+S")
        file_menu.AppendSeparator()
        file_menu.Append(ID_IMPORT_ADIF, _menu_label("menu.import_adif") + "\tCtrl+O")
        file_menu.Append(wx.ID_PREFERENCES, _menu_label("menu.settings") + "\tCtrl+P")
        file_menu.Append(wx.ID_EXIT, _menu_label("menu.exit") + "\tCtrl+Q")
        menubar.Append(file_menu, _menu_label("menu.file"))
    
        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, _menu_label("menu.about") + "\tShift+F1")
        help_menu.Append(wx.ID_HELP, _menu_label("menu.help_item") + "\tF1")
        help_menu.Append(ID_UPDATE, _menu_label("menu.check_updates") + "\tCtrl+U")
        help_menu.Append(ID_CHANGELOG, _menu_label("menu.changelog") + "\tCtrl+F1")
        feedback_menu = wx.Menu()
        feedback_menu.Append(ID_FEEDBACK_EMAIL, _menu_label("menu.feedback.email"))
        feedback_menu.Append(ID_FEEDBACK_TELEGRAM, _menu_label("menu.feedback.telegram"))
        help_menu.AppendSubMenu(feedback_menu, _menu_label("menu.feedback"))
        menubar.Append(help_menu, _menu_label("menu.help"))
        self.SetMenuBar(menubar)
    

    def _init_ui(self):
        self._build_menu_bar()

        self.notebook = wx.Notebook(self, style=wx.NB_TOP)
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_page_changed)

        # The QSO form can exceed the available notebook height when fields are enabled.
        # A vertical scroller keeps every control reachable on small windows and
        # after display scaling changes, without changing the tab/focus order.
        self.add_panel = wx.ScrolledWindow(
            self.notebook, style=wx.VSCROLL | wx.TAB_TRAVERSAL
        )
        self.add_panel.SetScrollRate(0, 20)
        self._init_add_qso_ui(self.add_panel)
        self.notebook.AddPage(self.add_panel, tr("tab.add_qso"))

        self.journal_panel = wx.Panel(self.notebook)
        self._init_journal_ui(self.journal_panel)
        self.notebook.AddPage(self.journal_panel, tr("tab.journal"))
        self._ui_language = get_resolved_language()

        # The notebook is the main content area and must expand with the frame.
        # Without a frame sizer, wxWidgets may leave it at its default/best size,
        # which makes the form appear compressed in the upper-left corner.
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(main_sizer)

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

    def refresh_language(self):
        """Refresh existing main-window labels after translations are reloaded."""
        language = get_resolved_language()
        if getattr(self, "_ui_language", None) == language:
            return False

        self._ui_language = language
        self.SetTitle(tr("app.title"))
        self._build_menu_bar()
        self.notebook.SetPageText(0, tr("tab.add_qso"))
        self.notebook.SetPageText(1, tr("tab.journal"))

        # Journal controls are kept alive so search, sorting, filters, selection,
        # and export marks are not lost when the language changes.
        if hasattr(self, "journal_search_label"):
            self.journal_search_label.SetLabel(tr("journal.search"))
            self.journal_search.SetHint(tr("journal.search.hint"))
            self.journal_sort_label.SetLabel(tr("journal.sort"))
            self.journal_sort_direction_label.SetLabel(
                tr("journal.sort.direction")
            )
            self.journal_sort.SetName(tr("journal.sort"))
            self.journal_sort_direction.SetName(tr("journal.sort.direction"))
            self._build_sort_choices()
            self._update_filter_indicators()

        # Update column captions without resetting user-adjusted column widths.
        column_keys = ["journal.export_mark"]
        column_keys.extend(
            title_key
            for field_name, (title_key, _width) in zip(QSO_FIELD_NAMES, JOURNAL_COLUMNS)
            if field_name != "datetime"
        )
        column_keys.append(JOURNAL_COLUMNS[-1][0])
        for index, key in enumerate(column_keys):
            if index >= self.journal_list.GetColumnCount():
                break
            item = wx.ListItem()
            item.SetText(tr(key))
            item.SetWidth(self.journal_list.GetColumnWidth(index))
            self.journal_list.SetColumn(index, item)

        self.Layout()
        return True

    def apply_visible_fields(self):
        # Preserve an active edit as well as an unfinished new-QSO draft.
        editing_in_progress = self.controller.is_editing()
        editing_qso_data = (
            self.controller._read_qso_from_gui() if editing_in_progress else None
        )
        restore_draft_after_rebuild = (
            not editing_in_progress and bool(getattr(self, "_draft_dirty", False))
        )
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
        if editing_in_progress and editing_qso_data:
            self.gui_bridge.populate_form(editing_qso_data)
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
        # Recalculate the page and notebook geometry after rebuilding controls.
        self.add_panel.Layout()
        self.add_panel.FitInside()
        self.notebook.Layout()
        self.Layout()
        apply_theme(self, self.settings_manager.get_option("theme", "system"))
