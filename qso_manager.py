import wx
import logging
import nvda_notify
import os
import json
import utils
import threading
from datetime import datetime, timedelta
from qrz_lookup import QRZLookup
from transliterator import transliterate_russian

class QSOManager:
    def __init__(self, parent=None, settings_manager=None):
        self.parent = parent
        if settings_manager is None:
            raise ValueError("SettingsManager не передан в QSOManager")
        self.settings_manager = settings_manager
        self._init_qrz_lookup()
        self.controls = {}
        self.qso_list = []
        self.editing_index = None  # Индекс редактируемой записи
        # автосохранение сеанса
        self.auto_temp = self.settings_manager.get_option('auto_temp', '0') == '1'
        # temp-файл рядом с приложением
        base = os.path.join(utils.get_app_path(), '')
        self.temp_file = os.path.join(base, 'blind_log_temp.json')

    def _refresh_temp_setting(self):
        self.auto_temp = self.settings_manager.get_option('auto_temp', '0') == '1'

    def set_controls(self, controls):
        self.controls = controls
        # после привязки контролов возможно потребуется подчитать автосохранение
        self._refresh_temp_setting()

    def _init_qrz_lookup(self):
        qrz_username = self.settings_manager.settings.get("qrz_username", "")
        qrz_password = self.settings_manager.settings.get("qrz_password", "")
        use_qrz = self.settings_manager.settings.get("use_qrz_lookup", '1') == '1'
        self.qrz_lookup = QRZLookup(qrz_username, qrz_password) if use_qrz else None
        if use_qrz and self.qrz_lookup and not self.qrz_lookup.login():
            wx.MessageBox(
                "Ошибка авторизации на QRZ.ru. Проверьте логин и пароль для XML API.",
                "Ошибка",
                wx.OK | wx.ICON_ERROR
            )

    def reload_settings(self):
        self.settings_manager.load_settings()
        self._init_qrz_lookup()
        self._refresh_temp_setting()

    def add_qso(self, event):
        """Добавление QSO: читаем только видимые поля; требуем только CALL."""
        visible = self.settings_manager.get_visible_fields()

        call_ctrl = self.controls.get('call')
        call_val = call_ctrl.GetValue().strip().upper() if call_ctrl else ""

        if not call_val:
            self._show_error("Заполните обязательное поле: Позывной")
            if call_ctrl:
                call_ctrl.SetFocus()
            return

        # Frequency - ВСЕГДА читать (даже если скрыта в UI)
        freq_ctrl = self.controls.get('freq')
        freq_value = (freq_ctrl.GetValue().strip().replace(",", ".") if freq_ctrl else "")

        # Date/time: compute using current timezone if controls hidden/missing
        now = self._get_current_time_with_timezone()
        date_ctrl = self.controls.get('date')
        time_ctrl = self.controls.get('time')
        if visible.get('date', True) or visible.get('time', True):
            # use provided parts where visible, fallback to now for missing parts
            if date_ctrl and visible.get('date', True):
                d = date_ctrl.GetValue()
                date_part = d.FormatISODate()
            else:
                date_part = now.strftime('%Y-%m-%d')
            if time_ctrl and visible.get('time', True):
                t = time_ctrl.GetValue()
                time_part = t.Format('%H:%M')
            else:
                time_part = now.strftime('%H:%M')
            datetime_str = f"{date_part} {time_part}"
        else:
            datetime_str = now.strftime('%Y-%m-%d %H:%M')

        # Build qso record, reading ВСЕГДА все значения, даже если они скрыты в UI
        # (данные должны сохраняться в журнал независимо от видимости полей в форме)
        def read_str(key, default=""):
            # НЕ проверяем видимость - читаем значение ВСЕГДА
            ctrl = self.controls.get(key)
            if not ctrl:
                return default
            # Handle different control types: TextCtrl, Choice, etc.
            try:
                if hasattr(ctrl, 'GetValue'):
                    val = ctrl.GetValue()
                elif hasattr(ctrl, 'GetStringSelection'):
                    val = ctrl.GetStringSelection()
                elif hasattr(ctrl, 'GetSelection') and hasattr(ctrl, 'GetString'):
                    sel = ctrl.GetSelection()
                    val = ctrl.GetString(sel) if sel != wx.NOT_FOUND else ''
                else:
                    val = ''
            except Exception:
                try:
                    val = ctrl.GetStringSelection()
                except Exception:
                    val = ''
            return (val or '').strip()

        qso_data = {
            'call': call_val,
            'name': read_str('name', '').title(),
            'city': read_str('city', '').title(),
            'qth': read_str('qth', '').upper(),
            'band': read_str('band', ''),
            'mode': read_str('mode', ''),
            'freq': freq_value,
            'rst_received': read_str('rst_received', ''),
            'rst_sent': read_str('rst_sent', ''),
            'comment': read_str('comment', ''),
            'datetime': datetime_str,
        }

        # Транслитерация полей, кроме позывного
        qso_data['name'] = transliterate_russian(qso_data['name'])
        qso_data['city'] = transliterate_russian(qso_data['city'])
        qso_data['comment'] = transliterate_russian(qso_data['comment'])

        if self.editing_index is not None:
            self.qso_list[self.editing_index] = qso_data
            self.editing_index = None
        else:
            self.qso_list.append(qso_data)
        if self.auto_temp:
            self.save_temp()

        self._update_journal()
        self._clear_fields()
        if call_ctrl:
            call_ctrl.SetFocus()
        self._show_notification("QSO добавлен в журнал")

    def edit_qso(self, event):
        selected_index = self.journal_list.GetFirstSelected()
        if selected_index == -1:
            self._show_error("Выберите запись для редактирования")
            return
        
        # Переключаемся на вкладку "Добавить QSO" для удобства пользователя
        self.parent.notebook.SetSelection(0)
        
        qso_data = self.qso_list[selected_index]
        # Устанавливаем значения только в тех контролах, которые присутствуют
        if 'call' in self.controls:
            self.controls['call'].SetValue(qso_data.get('call', ''))
        if 'name' in self.controls:
            self.controls['name'].SetValue(qso_data.get('name', ''))
        if 'city' in self.controls:
            self.controls['city'].SetValue(qso_data.get('city', ''))
        if 'qth' in self.controls:
            self.controls['qth'].SetValue(qso_data.get('qth', ''))
        if 'band' in self.controls and hasattr(self.controls['band'], 'SetStringSelection'):
            try:
                self.controls['band'].SetStringSelection(qso_data.get('band', ''))
            except Exception:
                pass
        if 'mode' in self.controls and hasattr(self.controls['mode'], 'SetStringSelection'):
            try:
                self.controls['mode'].SetStringSelection(qso_data.get('mode', ''))
            except Exception:
                pass
        if 'freq' in self.controls:
            self.controls['freq'].SetValue(qso_data.get('freq', ''))
        if 'rst_received' in self.controls:
            self.controls['rst_received'].SetValue(qso_data.get('rst_received', ''))
        if 'rst_sent' in self.controls:
            self.controls['rst_sent'].SetValue(qso_data.get('rst_sent', ''))
        if 'comment' in self.controls:
            self.controls['comment'].SetValue(qso_data.get('comment', ''))
        
        self.editing_index = selected_index  # Сохранение индекса редактируемой записи
        self.controls['call'].SetFocus()  # Установка фокуса на поле "Позывной"

    # --- автотемп методы ---
    def save_temp(self):
        try:
            with open(self.temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.qso_list, f, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Ошибка сохранения temp: {e}")

    def load_temp(self):
        if not os.path.exists(self.temp_file):
            return None
        try:
            with open(self.temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception as e:
            logging.error(f"Ошибка загрузки temp: {e}")
            return None

    def clear_temp(self):
        if os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except Exception as e:
                logging.error(f"Ошибка удаления temp: {e}")

    def del_qso(self, event):
        selected_index = self.journal_list.GetFirstSelected()
        if selected_index == -1:
            self._show_error("Выберите запись для удаления")
            return
        
        self.qso_list.pop(selected_index)
        if self.auto_temp:
            self.save_temp()
        self._update_journal()
        self.journal_list.SetFocus()  # Установка фокуса на список записей
        self._show_notification("QSO удален из журнала")

    def _update_journal(self):
        # Обновление журнала согласно self.journal_columns (список полей в нужном порядке)
        self.journal_list.DeleteAllItems()
        for idx, qso in enumerate(self.qso_list):
            # Вставляем пустую строку и заполняем колонки по списку
            self.journal_list.InsertItem(idx, "")
            for col, field in enumerate(getattr(self, 'journal_columns', [])):
                val = qso.get(field, '')
                # Форматирование: datetime остаётся как есть
                self.journal_list.SetItem(idx, col, val)

    def _clear_fields(self):
        """
        Очищает все поля ввода, кроме RST-принято, RST-передано и Частоты.
        """
        controls_to_clear = [
            'call', 'name', 'city', 'qth', 'comment'
        ]
        for key in controls_to_clear:
            if key in self.controls:
                self.controls[key].SetValue("")

        # Устанавливаем дату и время с учетом часового пояса, если контролы присутствуют
        current_time = self._get_current_time_with_timezone()
        if 'date' in self.controls:
            try:
                self.controls['date'].SetValue(wx.DateTime.FromDMY(current_time.day, current_time.month - 1, current_time.year))
            except Exception:
                pass
        if 'time' in self.controls:
            try:
                self.controls['time'].SetValue(wx.DateTime.FromHMS(current_time.hour, current_time.minute, 0))
            except Exception:
                pass

    def _show_error(self, message):
        dlg = wx.MessageDialog(self.parent, message, "Ошибка ввода", wx.OK|wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def _show_notification(self, message):
        nvda_notify.nvda_notify(message)

    def _get_timezone_offset(self):
        """
        Получает часовой пояс из настроек и возвращает его в виде смещения в часах.
        """
        timezone = self.settings_manager.settings.get('timezone', 'UTC')
        if timezone == 'UTC':
            return 0  # Если выбран UTC, возвращаем смещение 0
        try:
            # Преобразуем custom_timezone в целое число
            return int(self.settings_manager.settings.get('custom_timezone', '0'))
        except ValueError:
            # Если значение некорректное, показываем ошибку и возвращаем 0
            self._show_error("Некорректное значение часового пояса. Используется UTC.")
            return 0

    def _get_current_time_with_timezone(self):
        """
        Возвращает текущее время с учетом настроек часового пояса.
        """
        timezone_offset = self._get_timezone_offset()
        current_time = datetime.utcnow() + timedelta(hours=timezone_offset)
        return current_time

    def _initialize_rst_fields(self):
        """
        Устанавливает значения по умолчанию для полей RST-принято и RST-передано.
        """
        if 'rst_received' in self.controls:
            self.controls['rst_received'].SetValue("59")
        if 'rst_sent' in self.controls:
            self.controls['rst_sent'].SetValue("59")
            

    def on_callsign_enter(self, event):
        """Обработчик события нажатия Enter в поле позывного."""
        if not self.qrz_lookup:
            nvda_notify.nvda_notify("Поиск по QRZ.ru отключён в настройках.")
            return
        callsign = self.controls['call'].GetValue().strip().upper()
        if not callsign:
            return
        try:
            result = self.qrz_lookup.lookup_call(callsign)
            if result:
                # Вставляем значения из QRZ.ru только если они не пустые
                if 'name' in self.controls:
                    self.controls['name'].SetValue(result.get("name", ""))
                if 'city' in self.controls:
                    self.controls['city'].SetValue(result.get("city", ""))
                nvda_notify.nvda_notify(f"Данные для {callsign} успешно загружены")
                print(f"QRZ: Данные для {callsign} успешно загружены: {result}")
                logging.info(f"QRZ: Данные для {callsign} успешно загружены: {result}")
            else:
                nvda_notify.nvda_notify(f"Позывной {callsign} не найден в базе QRZ.ru")
                print(f"QRZ: Позывной {callsign} не найден в базе QRZ.ru")
                logging.warning(f"QRZ: Позывной {callsign} не найден в базе QRZ.ru")
        except Exception as e:
            nvda_notify.nvda_notify(f"Ошибка поиска позывного: {e}")
            print(f"Ошибка поиска позывного: {e}")
            logging.error(f"Ошибка поиска позывного: {e}")