"""Main application window assembled from focused GUI mixins."""

import wx
from controller import ApplicationController
from i18n import tr
from .bridge import GUIBridgeImpl
from .draft import DraftMixin
from .journal_view import JournalViewMixin
from .qso_form import QSOFormMixin
from .qso_actions import QSOActionsMixin
from .import_export import ImportExportMixin
from .keyboard import KeyboardMixin
from .menu_actions import MenuActionsMixin
from .window_layout import WindowLayoutMixin
from .window_events import WindowEventsMixin


class Blind_log(
    wx.Frame,
    WindowLayoutMixin,
    WindowEventsMixin,
    KeyboardMixin,
    MenuActionsMixin,
    DraftMixin,
    JournalViewMixin,
    QSOFormMixin,
    QSOActionsMixin,
    ImportExportMixin,
):
    def __init__(self, *args, settings_manager=None, qso_manager=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL
        wx.Frame.__init__(self, *args, **kwds)
        
        self.controls = {}
        self.SetTitle(tr("app.title"))
        self.settings_manager = settings_manager  # Сохраняем экземпляр SettingsManager
        if qso_manager is None:
            raise ValueError("Blind_log requires qso_manager instance")
        self.qso_manager = qso_manager
        self._datetime_manual_override = False
        self._journal_saved = False
        self._suppress_datetime_change_events = False
        self._suppress_draft_changes = False
        self._draft_dirty = False
        self._draft_save_call = None
        
        # Создаём GUIBridge для связи controller с GUI
        self.gui_bridge = GUIBridgeImpl(self)
        
        # Создаём ApplicationController - это единственный, кто вызывает методы QSOManager
        self.controller = ApplicationController(self.qso_manager, self.settings_manager, self.gui_bridge)
        
        self._init_ui()
        self._init_journal_columns()
        # Применяем видимость полей при старте (rebuild add panel and columns)
        self.apply_visible_fields()
        self._restore_draft()
        # Устанавливаем ускорители после финальной сборки контролов (add_btn может быть пересоздан)
        self._init_accelerator()
        self._init_time_timer()
        self.Layout()
        self.Centre()
        # Добавляем обработчик закрытия окна
        self.Bind(wx.EVT_CLOSE, self.on_close)
