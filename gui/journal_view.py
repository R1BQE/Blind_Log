"""Journal list rendering and its context-menu behavior."""

import wx

from common.constants import JOURNAL_COLUMNS, QSO_FIELD_NAMES
from localization.i18n import tr
from logger import log_error


class JournalViewMixin:
    def _init_journal_ui(self, panel):
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.journal_list = wx.ListCtrl(
            panel,
            style=wx.LC_REPORT|wx.LC_HRULES|wx.LC_VRULES,
            size=(-1, 600)
        )
        
        sizer.Add(self.journal_list, 1, wx.EXPAND|wx.ALL, 5)
        panel.SetSizer(sizer)

        # Context menu for journal list (Application key, Shift+F10, right click)
        self.journal_list.Bind(wx.EVT_CONTEXT_MENU, self.on_journal_context_menu)

    def _init_journal_columns(self):
        # Жёсткое разделение: журнал ВСЕГДА содержит ВСЕ поля, независимо от видимости формы
        try:
            while self.journal_list.GetColumnCount() > 0:
                self.journal_list.DeleteColumn(0)
        except Exception as e:
            log_error(f"Failed to reset journal columns: {e}")
        
        # Создаём ВСЕ столбцы, без проверки видимости
        journal_columns = []
        idx = 0
        for (field_name, (title_key, width)) in zip(QSO_FIELD_NAMES, JOURNAL_COLUMNS):
            if field_name == 'datetime':
                continue
            # ВСЕГДА добавляем столбец, независимо от видимости в форме
            self.journal_list.InsertColumn(idx, tr(title_key), width=width)
            journal_columns.append(field_name)
            idx += 1
        
        # Добавляем комбинированную дата/время в конце
        dt_title_key, dt_width = JOURNAL_COLUMNS[-1]
        self.journal_list.InsertColumn(idx, tr(dt_title_key), width=dt_width)
        journal_columns.append('datetime')
        
        # Сохраняем порядок колонок локально в GUI (для использования в _update_journal_from_manager)
        self.journal_columns = journal_columns


    def on_journal_context_menu(self, event):
        """Контекстное меню журнала по Application/Shift+F10/правой кнопке мыши."""
        menu = wx.Menu()
        edit_item = menu.Append(wx.ID_ANY, tr("button.edit") + "	Ctrl+E")
        del_item = menu.Append(wx.ID_ANY, tr("button.delete") + "	Del")
        menu.Bind(wx.EVT_MENU, self.on_edit_qso, edit_item)
        menu.Bind(wx.EVT_MENU, self.on_delete_qso, del_item)
        self.PopupMenu(menu)
        menu.Destroy()


    def _update_journal_from_manager(self):
        """Обновить отображение журнала через контроллер."""
        # Reset saved flag since journal has changed
        self._journal_saved = False
        self.journal_list.DeleteAllItems()
        for idx, qso in enumerate(self.controller.get_qso_list()):
            self.journal_list.InsertItem(idx, "")
            for col, field in enumerate(getattr(self, 'journal_columns', [])):
                val = qso.get(field, '')
                self.journal_list.SetItem(idx, col, val)