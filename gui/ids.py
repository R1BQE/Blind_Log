"""Stable wx IDs used by the main window and its keyboard accelerators."""

import wx

# Создаем кастомные ID для пунктов меню
ID_UPDATE = wx.NewIdRef()
ID_CHANGELOG = wx.NewIdRef()
ID_ADD_QSO = wx.NewIdRef()
ID_EDIT_QSO = wx.NewIdRef()
ID_DEL_QSO = wx.NewIdRef()
ID_EXPORT_QSO = wx.NewIdRef()
ID_IMPORT_ADIF = wx.NewIdRef()

# IDs для горячих клавиш полей
ID_FOCUS_CALL = wx.NewIdRef()
ID_FOCUS_NAME = wx.NewIdRef()
ID_FOCUS_CITY = wx.NewIdRef()
ID_FOCUS_QTH = wx.NewIdRef()
ID_FOCUS_FREQ = wx.NewIdRef()
ID_FOCUS_RST_REC = wx.NewIdRef()
ID_FOCUS_RST_SENT = wx.NewIdRef()
ID_CYCLE_MODE = wx.NewIdRef()
ID_CYCLE_BAND = wx.NewIdRef()
ID_FOCUS_COMMENT = wx.NewIdRef()
ID_FOCUS_DATE = wx.NewIdRef()
ID_FOCUS_TIME = wx.NewIdRef()
ID_CANCEL_EDIT = wx.NewIdRef()
ID_LOOKUP_CALLSIGN = wx.NewIdRef()
ID_UNDO_JOURNAL = wx.NewIdRef()
ID_CLEAR_DRAFT = wx.NewIdRef()
ID_FEEDBACK_EMAIL = wx.NewIdRef()
ID_FEEDBACK_TELEGRAM = wx.NewIdRef()

# Journal navigation shortcuts
ID_JOURNAL_SEARCH = wx.NewIdRef()
ID_JOURNAL_SORT = wx.NewIdRef()
ID_JOURNAL_FILTER = wx.NewIdRef()
