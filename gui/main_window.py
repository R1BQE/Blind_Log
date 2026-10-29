import wx
import webbrowser
from datetime import datetime
from updater import check_update, Result
from controller import ApplicationController
from .bridge import GUIBridgeImpl
from .draft import DraftMixin
from .journal_view import JournalViewMixin
from .qso_form import QSOFormMixin
from .qso_actions import QSOActionsMixin
from exporter import Exporter
from utils import resource_path, get_version_info
from i18n import tr, get_resolved_language
from logger import log_ui_state, log_error
import welcome_dialog
from .ids import (
    ID_UPDATE, ID_CHANGELOG, ID_ADD_QSO, ID_EDIT_QSO, ID_DEL_QSO,
    ID_EXPORT_QSO, ID_IMPORT_ADIF, ID_FOCUS_CALL, ID_FOCUS_NAME,
    ID_FOCUS_CITY, ID_FOCUS_QTH, ID_FOCUS_FREQ, ID_FOCUS_RST_REC,
    ID_FOCUS_RST_SENT, ID_CYCLE_MODE, ID_CYCLE_BAND, ID_FOCUS_COMMENT,
    ID_FOCUS_DATE, ID_FOCUS_TIME, ID_CANCEL_EDIT, ID_QRZ_LOOKUP,
    ID_FEEDBACK_EMAIL, ID_FEEDBACK_TELEGRAM,
)

class Blind_log(wx.Frame, DraftMixin, JournalViewMixin, QSOFormMixin, QSOActionsMixin):
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
        
        # Exporter — чистый слой экспорта без GUI зависимостей
        self.exporter = Exporter(self.qso_manager, self.settings_manager)
        
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

    def _reset_datetime_override(self):
        """Reset manual datetime override state."""
        self._datetime_manual_override = False
        self._journal_saved = False  # True after successful export, reset on any journal change

    def _set_datetime_change_suppression(self, enabled):
        """Suppress or allow programmatic datetime control changes."""
        self._suppress_datetime_change_events = bool(enabled)

    def on_datetime_control_change(self, event):
        """Mark manual datetime entry so auto-update will stop."""
        if not self._suppress_datetime_change_events:
            self._datetime_manual_override = True
        event.Skip()

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

    def speak(self, text):
        """Озвучить текст через NVDA"""
        try:
            import nvda_notify
            nvda_notify.nvda_controller.speak(text)
        except Exception as e:
            log_error(f"Failed to speak text via NVDA: {e}")

    def focus_field(self, key, label_key):
        """Установить фокус на поле или озвучить, что оно скрыто"""
        if key not in self.controls:
            # Поле скрыто
            label = tr(label_key)
            self.speak(tr("field.hidden").format(field=label))
            return
        
        widget = self.controls[key]
        widget.SetFocus()

    def _init_accelerator(self):
        # Используем кастомные IDs для ускорителей, чтобы они работали даже после перестроения UI
        accel_entries = [
            (wx.ACCEL_NORMAL, wx.WXK_RETURN, ID_ADD_QSO),
            (wx.ACCEL_CTRL, ord('E'), ID_EDIT_QSO),
            (wx.ACCEL_CTRL, ord('S'), ID_EXPORT_QSO),
            (wx.ACCEL_CTRL, ord('O'), ID_IMPORT_ADIF),
            (wx.ACCEL_NORMAL, wx.WXK_DELETE, ID_DEL_QSO),
            (wx.ACCEL_SHIFT, wx.WXK_F1, wx.ID_ABOUT),
            (wx.ACCEL_NORMAL, wx.WXK_F1, wx.ID_HELP),
            (wx.ACCEL_CTRL, wx.WXK_F1, ID_CHANGELOG),
            (wx.ACCEL_CTRL, ord('U'), ID_UPDATE),
            # Новые горячие клавиши для полей
            (wx.ACCEL_ALT, ord('C'), ID_FOCUS_CALL),
            (wx.ACCEL_ALT, ord('N'), ID_FOCUS_NAME),
            (wx.ACCEL_ALT, ord('T'), ID_FOCUS_CITY),
            (wx.ACCEL_ALT, ord('Q'), ID_FOCUS_QTH),
            (wx.ACCEL_ALT, ord('F'), ID_FOCUS_FREQ),
            (wx.ACCEL_ALT, ord('R'), ID_FOCUS_RST_REC),
            (wx.ACCEL_ALT, ord('S'), ID_FOCUS_RST_SENT),
            (wx.ACCEL_ALT, ord('M'), ID_CYCLE_MODE),
            (wx.ACCEL_ALT, ord('B'), ID_CYCLE_BAND),
            (wx.ACCEL_ALT, ord('O'), ID_FOCUS_COMMENT),
            (wx.ACCEL_ALT, ord('D'), ID_FOCUS_DATE),
            (wx.ACCEL_ALT, ord('I'), ID_FOCUS_TIME),
            (wx.ACCEL_NORMAL, wx.WXK_ESCAPE, ID_CANCEL_EDIT),
            (wx.ACCEL_CTRL, wx.WXK_RETURN, ID_QRZ_LOOKUP),
        ]
        accel_tbl = wx.AcceleratorTable([wx.AcceleratorEntry(*entry) for entry in accel_entries])
        self.SetAcceleratorTable(accel_tbl)

        # Unbind старые binds перед новыми
        for id_ in [ID_FOCUS_CALL, ID_FOCUS_NAME, ID_FOCUS_CITY, ID_FOCUS_QTH, ID_FOCUS_FREQ,
                    ID_FOCUS_RST_REC, ID_FOCUS_RST_SENT, ID_CYCLE_MODE, ID_CYCLE_BAND,
                    ID_FOCUS_COMMENT, ID_FOCUS_DATE, ID_FOCUS_TIME]:
            self.Unbind(wx.EVT_MENU, id=id_)

        # Binds для горячих клавиш полей
        # Обычные поля: проверяем видимость и озвучиваем "скрыто"
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('call', "label.callsign"), id=ID_FOCUS_CALL)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('name', "label.name"), id=ID_FOCUS_NAME)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('city', "label.city"), id=ID_FOCUS_CITY)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('qth', "label.qth"), id=ID_FOCUS_QTH)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('freq', "label.freq"), id=ID_FOCUS_FREQ)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('rst_received', "label.rst_received"), id=ID_FOCUS_RST_REC)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('rst_sent', "label.rst_sent"), id=ID_FOCUS_RST_SENT)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('comment', "label.comment"), id=ID_FOCUS_COMMENT)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('date', "label.date"), id=ID_FOCUS_DATE)
        self.Bind(wx.EVT_MENU, lambda evt: self.focus_field('time', "label.time"), id=ID_FOCUS_TIME)
        
        # Отмена редактирования по Escape
        self.Bind(wx.EVT_MENU, self.on_cancel_edit, id=ID_CANCEL_EDIT)
        # Поиск по QRZ по Ctrl+Enter
        self.Bind(wx.EVT_MENU, self._on_qrz_lookup_accel, id=ID_QRZ_LOOKUP)

        # ComboBox: всегда работают, независимо от видимости
        self.Bind(wx.EVT_MENU, lambda evt: self.cycle_choice('mode'), id=ID_CYCLE_MODE)
        self.Bind(wx.EVT_MENU, lambda evt: self.cycle_choice('band'), id=ID_CYCLE_BAND)

    def cycle_choice(self, key):
        choice = self.controls[key]
        current = choice.GetSelection()
        count = choice.GetCount()
        if count > 0:
            new_index = (current + 1) % count
            choice.SetSelection(new_index)
            # Озвучиваем новое значение через NVDA
            value = choice.GetString(new_index)
            label_key = f"field.{key}"
            label = tr(label_key)
            import nvda_notify
            nvda_notify.nvda_controller.speak(f"{label}: {value}")
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

        dlg = wx.Dialog(self, title=tr("changelog.title"), size=(600, 500))
        vbox = wx.BoxSizer(wx.VERTICAL)
        text_ctrl = wx.TextCtrl(dlg, value=changelog_text, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        vbox.Add(text_ctrl, 1, wx.EXPAND|wx.ALL, 10)
        btn = wx.Button(dlg, label=tr("changelog.button.close"))
        btn.Bind(wx.EVT_BUTTON, lambda evt: dlg.Close())
        vbox.Add(btn, 0, wx.ALIGN_CENTER|wx.ALL, 10)
        dlg.SetSizer(vbox)
        dlg.ShowModal()
        dlg.Destroy()

    def on_page_changed(self, event):
        selected_page = self.notebook.GetSelection()
        if (selected_page == 0):
            log_ui_state("Switched to QSO addition tab")
            if self.controller.qso_manager.editing_index is None:
                self._reset_datetime_override()
                self._set_datetime_change_suppression(True)
                try:
                    date_value, time_value = self.controller.get_default_datetime_components()
                    if date_value:
                        date_obj = wx.DateTime()
                        if date_obj.ParseISODate(date_value):
                            self.controls['date'].SetValue(date_obj)
                    if time_value:
                        time_obj = wx.DateTime()
                        if time_obj.ParseTime(time_value):
                            self.controls['time'].SetValue(time_obj)
                except Exception:
                    pass
                finally:
                    self._set_datetime_change_suppression(False)
            self.controls['call'].SetFocus()
        elif (selected_page == 1):
            log_ui_state("Switched to journal tab")
            # Reset editing state if user manually switched to journal tab
            # This prevents accidental overwrite of a record being edited
            if self.controller.qso_manager.editing_index is not None:
                self.controller.qso_manager.editing_index = None
                self.gui_bridge.clear_form()
            self.journal_list.SetFocus()
        event.Skip()

    def on_settings(self, event):
        # Открыть диалог настроек через контроллер
        log_ui_state("Settings dialog opened")
        if self.controller.open_settings_dialog():
            try:
                self.apply_visible_fields()
            except Exception as e:
                log_error(f"Failed to apply visible fields after settings change: {e}")

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

    def on_export(self, event=None):
        """Запустить диалог экспорта и сохранить ADIF через Exporter."""
        # Generate default filename: callsign_date_time.adi
        operator = self.settings_manager.get_option('call', '').strip().lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_name = f"{operator}_{timestamp}.adi" if operator else f"{timestamp}.adi"

        with wx.FileDialog(self, tr("export.save_adif"), wildcard="ADIF files (*.adi)|*.adi",
                           defaultFile=default_name,
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return Result(False)

            pathname = fileDialog.GetPath()
            result = self.exporter.export_to_adif(pathname)
            if result.success:
                self._journal_saved = True
                self.gui_bridge.show_notification(tr("success.export"))
            elif result.error:
                self.gui_bridge.show_error(tr("error.title"), result.error)
            return result

    def on_import_adif(self, event=None):
        """Открыть файл ADIF и импортировать QSO в журнал.
        Шаги:
          1. Проверка наличия библиотеки adif-io.
          2. Диалог выбора файла.
          3. Диалог выбора режима (заменить / добавить / отмена).
          4. Вызов controller.import_adif_file.
          5. Восстановление фокуса на журнале.
        """
        # 1. Проверка наличия зависимости
        if not self.controller.is_adif_available():
            wx.MessageBox(
                tr("import.adif_unavailable"),
                tr("error.title"),
                wx.OK | wx.ICON_ERROR
            )
            return

        # 2. Выбор файла
        with wx.FileDialog(
 # type: ignore
            self,
            tr("import.open_adif"),
            wildcard="ADIF files (*.adi)|*.adi",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return Result(False)
            filepath = fileDialog.GetPath()

        # 2. Выбор режима импорта
        mode_dlg = wx.MessageDialog(
            self,
            tr("import.choose_mode"),
            tr("import.title"),
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
        )
        try:
            mode_dlg.SetYesNoCancelLabels(
                tr("import.replace_journal"),
                tr("import.append_journal"),
                tr("dialog.cancel"),
            )
            mode = mode_dlg.ShowModal()
        finally:
            mode_dlg.Destroy()

        if mode == wx.ID_CANCEL:
            return Result(False)
        import_mode = 'replace' if mode == wx.ID_YES else 'append'

        # 3. Импорт через контроллер (он же сделает update_journal_display + NVDA-уведомление)
        result = self.controller.import_adif_file(filepath, mode=import_mode)

        # 4. Восстановление фокуса на журнале (там, где пользователь был до импорта)
        if hasattr(self, 'notebook') and hasattr(self, 'journal_list'):
            try:
                self.notebook.SetSelection(1)
                self.journal_list.SetFocus()
            except Exception as e:
                log_error(f"Failed to restore focus after import: {e}")

        return result

    def on_about(self, event):
        """
        Обработчик для пункта меню "О программе".
        """
        log_ui_state("About dialog opened")
        version_info = get_version_info()

        # Создание диалога "О программе"
        about_dialog = wx.Dialog(self, title=tr("about.title"), size=(400, 300))
        about_sizer = wx.BoxSizer(wx.VERTICAL)

        # Текст с информацией о программе
        about_text = wx.StaticText(
            about_dialog,
            label=f"{version_info['description']}\n\n"
                  f"Author: {version_info['author']}\n"
                  f"Version: {version_info['version']}"
        )
        about_text.Wrap(380)
        about_sizer.Add(about_text, 1, wx.ALL | wx.EXPAND, 10)

        # Кнопка для перехода на сайт программы
        site_button = wx.Button(about_dialog, label=tr("about.button.site"))
        site_button.Bind(wx.EVT_BUTTON, lambda evt: webbrowser.open("https://github.com/r1oaz/Blind_Log"))
        about_sizer.Add(site_button, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        # Кнопка "Закрыть"
        close_button = wx.Button(about_dialog, label=tr("about.button.close"))
        close_button.Bind(wx.EVT_BUTTON, lambda evt: about_dialog.Close())
        about_sizer.Add(close_button, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        about_dialog.SetSizer(about_sizer)
        about_dialog.ShowModal()
        about_dialog.Destroy()

    def _init_time_timer(self):
        """Инициализировать таймер обновления текущего времени в форме QSO."""
        if hasattr(self, '_time_update_timer'):
            try:
                self._time_update_timer.Stop()
            except Exception:
                pass
        else:
            self._time_update_timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self._on_time_tick, self._time_update_timer)

        if 'time' in self.controls:
            self._time_update_timer.Start(1000)
        else:
            self._time_update_timer.Stop()

    def _on_time_tick(self, event):
        if 'time' not in self.controls:
            return

        # Не обновляем время, когда редактируется существующая запись.
        if self.controller and hasattr(self.controller, 'qso_manager') and getattr(self.controller.qso_manager, 'editing_index', None) is not None:
            return

        # Не обновляем время, если пользователь вручную изменял дату/время.
        if self._datetime_manual_override:
            return

        # Только обновляем время, если добавление нового QSO активно
        if self.notebook.GetSelection() != 0:
            return

        try:
            date_value, time_value = self.controller.get_default_datetime_components()
            self._suppress_draft_changes = True
            if time_value:
                time_obj = wx.DateTime()
                if time_obj.ParseTime(time_value):
                    self.controls['time'].SetValue(time_obj)
            if 'date' in self.controls and date_value:
                date_obj = wx.DateTime()
                if date_obj.ParseISODate(date_value):
                    self.controls['date'].SetValue(date_obj)
        except Exception as e:
            log_error(f"Failed to update current time tick: {e}")
        finally:
            self._suppress_draft_changes = False

    def on_help(self, event):
        # Открытие файла справки в зависимости от выбранного языка
        help_file = 'help.htm' if get_resolved_language() == 'ru' else 'help_en.htm'
        help_path = resource_path(help_file)
        webbrowser.open(help_path)

    def on_feedback_email(self, event):
        webbrowser.open(f"mailto:{welcome_dialog.EMAIL_ADDRESS}")

    def on_feedback_telegram(self, event):
        webbrowser.open(welcome_dialog.TELEGRAM_URL)

    def on_check_updates(self, event):
        check_update(self)  # вызываем функцию и передаём главное окно
