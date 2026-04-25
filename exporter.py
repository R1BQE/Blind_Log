import wx
from datetime import datetime
from i18n import tr

class Exporter:
    def __init__(self, qso_manager, settings_manager):
        self.qso_manager = qso_manager
        self.settings_manager = settings_manager

    def on_export(self, event):
        parent = getattr(self.qso_manager, 'parent', None)
        with wx.FileDialog(parent, tr("export.save_adif"), wildcard="ADIF files (*.adi)|*.adi",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return False  # Пользователь отменил сохранение

            # Получение пути для сохранения файла
            pathname = fileDialog.GetPath()
            return self.export_to_adif(pathname)

    def export_to_adif(self, filepath):
        # Убедиться, что настройки загружены
        if not hasattr(self.settings_manager, 'settings'):
            raise ValueError(tr("error.settings_not_loaded"))

        # Получение данных из настроек
        operator = self.settings_manager.settings.get('call', '')
        my_name = self.settings_manager.settings.get('operator_name', '')
        my_qth = self.settings_manager.settings.get('my_qth', '')
        my_city = self.settings_manager.settings.get('my_city', '')
        my_rig = self.settings_manager.settings.get('my_rig', '')
        my_lat = self.settings_manager.settings.get('my_lat', '')
        my_lon = self.settings_manager.settings.get('my_lon', '')

        try:
            with open(filepath, 'w', encoding='cp1251') as file:
                # Запись заголовка ADIF
                file.write(f"#   Created:  {datetime.now().strftime('%d-%m-%Y  %H:%M:%S')}\n")
                file.write("<ADIF_VER:3>2.0\n<EOH>\n")

                # Запись данных QSO — только видимые поля
                visible = self.settings_manager.get_visible_fields()
                for qso in self.qso_manager.qso_list:
                    parts = []
                    parts.append(f"<OPERATOR:{len(operator)}>{operator}")
                    # CALL is always present
                    parts.append(f"<CALL:{len(qso.get('call',''))}>{qso.get('call','')}")

                    # Date/time handling
                    dt_raw = qso.get('datetime', '')
                    dt_compact = dt_raw.replace('-', '').replace(':', '').replace(' ', '')
                    qso_date = dt_compact[:8] if len(dt_compact) >= 8 else ''
                    qso_time = dt_compact[8:12] if len(dt_compact) > 8 else ''
                    if visible.get('date', True):
                        parts.append(f"<QSO_DATE:{len(qso_date)}>{qso_date}")
                    if visible.get('time', True):
                        parts.append(f"<TIME_ON:{len(qso_time)}>{qso_time}")

                    if visible.get('freq', True) and qso.get('freq'):
                        parts.append(f"<FREQ:{len(qso.get('freq'))}>{qso.get('freq')}")
                    if visible.get('mode', True) and qso.get('mode'):
                        parts.append(f"<MODE:{len(qso.get('mode'))}>{qso.get('mode')}")
                    if visible.get('rst_sent', True) and qso.get('rst_sent'):
                        parts.append(f"<RST_SENT:{len(qso.get('rst_sent'))}>{qso.get('rst_sent')}")
                    if visible.get('rst_received', True) and qso.get('rst_received'):
                        parts.append(f"<RST_RCVD:{len(qso.get('rst_received'))}>{qso.get('rst_received')}")
                    if visible.get('qth', True) and qso.get('qth'):
                        parts.append(f"<GRIDSQUARE:{len(qso.get('qth'))}>{qso.get('qth')}")
                    if visible.get('band', True) and qso.get('band'):
                        parts.append(f"<BAND:{len(qso.get('band'))}>{qso.get('band')}")
                    if visible.get('name', True) and qso.get('name'):
                        parts.append(f"<NAME:{len(qso.get('name'))}>{qso.get('name')}")
                    if visible.get('city', True) and qso.get('city'):
                        parts.append(f"<QTH:{len(qso.get('city'))}>{qso.get('city')}")
                    if visible.get('comment', True) and qso.get('comment'):
                        parts.append(f"<COMMENT:{len(qso.get('comment'))}>{qso.get('comment')}")

                    # My station info (always include if present)
                    if my_name:
                        parts.append(f"<MY_NAME:{len(my_name)}>{my_name}")
                    if my_qth:
                        parts.append(f"<MY_QTH:{len(my_qth)}>{my_qth}")
                    if my_city:
                        parts.append(f"<MY_CITY:{len(my_city)}>{my_city}")
                    if my_rig:
                        parts.append(f"<MY_RIG:{len(my_rig)}>{my_rig}")
                    if my_lat:
                        parts.append(f"<MY_LAT:{len(my_lat)}>{my_lat}")
                    if my_lon:
                        parts.append(f"<MY_LON:{len(my_lon)}>{my_lon}")

                    parts.append("<EOR>\n")
                    file.write(''.join(parts))

            wx.MessageBox(tr("success.export"), tr("export.title"), wx.OK | wx.ICON_INFORMATION)
            try:
                if hasattr(self.qso_manager, 'auto_temp') and self.qso_manager.auto_temp:
                    self.qso_manager.clear_temp()
            except Exception:
                pass
            return True
        except Exception as e:
            wx.MessageBox(tr("error.export").format(error=e), tr("error.title"), wx.OK | wx.ICON_ERROR)
            return False