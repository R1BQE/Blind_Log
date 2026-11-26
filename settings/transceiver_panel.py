"""Accessible settings page for the optional Hamlib integration."""
import threading
import time
import wx

from localization.i18n import tr
from services.transceiver import (
    TransceiverController, download_latest_hamlib, get_installed_version,
    is_hamlib_installed, list_hamlib_models, list_serial_ports,
)
from common.accessibility import install_checkbox_accessibility


class TransceiverSettingsPanel(wx.Panel):
    def __init__(self, parent, settings_manager):
        super().__init__(parent, style=wx.TAB_TRAVERSAL)
        self.settings_manager = settings_manager
        self._model_ids = []
        self._download_in_progress = False
        self._build_ui()
        self.load_settings()

    def _build_ui(self):
        root = wx.BoxSizer(wx.VERTICAL)
        install_box = wx.StaticBoxSizer(wx.VERTICAL, self, tr("transceiver.group.install"))
        self.status_label = wx.StaticText(self, label="")
        self.download_button = wx.Button(self, label=tr("transceiver.download"))
        install_box.Add(self.status_label, 0, wx.ALL, 5)
        install_box.Add(self.download_button, 0, wx.ALL, 5)
        root.Add(install_box, 0, wx.EXPAND | wx.ALL, 6)

        connection_box = wx.StaticBoxSizer(wx.VERTICAL, self, tr("transceiver.group.connection"))
        self.use_checkbox = wx.CheckBox(self, label=tr("transceiver.use"))
        install_checkbox_accessibility(self.use_checkbox, self)
        connection_box.Add(self.use_checkbox, 0, wx.ALL, 5)
        self.connection_type = wx.Choice(self, choices=[
            tr("transceiver.connection.local"), tr("transceiver.connection.remote")
        ])
        self.host_text = wx.TextCtrl(self)
        self.port_text = wx.TextCtrl(self)
        self.model_choice = wx.Choice(self)
        self.com_choice = wx.Choice(self)
        self.baud_choice = wx.Choice(self, choices=[
            "4800", "9600", "19200", "38400", "57600", "115200"
        ])
        self.auto_poll_checkbox = wx.CheckBox(self, label=tr("transceiver.auto_poll"))
        install_checkbox_accessibility(self.auto_poll_checkbox, self)

        def add_row(label_key, control):
            row = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(self, label=tr(label_key))
            label.SetMinSize((self.FromDIP(155), -1))
            row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            row.Add(control, 1, wx.EXPAND)
            connection_box.Add(row, 0, wx.EXPAND | wx.ALL, 4)

        add_row("transceiver.connection_type", self.connection_type)
        add_row("transceiver.host", self.host_text)
        add_row("transceiver.port", self.port_text)
        add_row("transceiver.model", self.model_choice)
        add_row("transceiver.com_port", self.com_choice)
        add_row("transceiver.baudrate", self.baud_choice)
        connection_box.Add(self.auto_poll_checkbox, 0, wx.ALL, 5)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.refresh_button = wx.Button(self, label=tr("transceiver.refresh_models"))
        self.test_button = wx.Button(self, label=tr("transceiver.test_connection"))
        buttons.Add(self.refresh_button, 0, wx.RIGHT, 8)
        buttons.Add(self.test_button, 0)
        connection_box.Add(buttons, 0, wx.ALL, 5)
        root.Add(connection_box, 0, wx.EXPAND | wx.ALL, 6)
        self.SetSizer(root)

        self.download_button.Bind(wx.EVT_BUTTON, self.on_download)
        self.use_checkbox.Bind(wx.EVT_CHECKBOX, self.on_use_toggle)
        self.connection_type.Bind(wx.EVT_CHOICE, self.on_connection_type_change)
        self.refresh_button.Bind(wx.EVT_BUTTON, self.on_refresh_models)
        self.test_button.Bind(wx.EVT_BUTTON, self.on_test_connection)

    def load_settings(self):
        installed, version = is_hamlib_installed(), get_installed_version()
        self.status_label.SetLabel(
            tr("transceiver.installed").format(
                version=version or tr("transceiver.version_unknown")
            ) if installed else tr("transceiver.not_installed")
        )
        self.use_checkbox.SetValue(self.settings_manager.get_bool("use_hamlib", False))
        self.connection_type.SetSelection(
            1 if self.settings_manager.get_option("transceiver_connection", "local") == "remote" else 0
        )
        self.host_text.SetValue(self.settings_manager.get_option("transceiver_host", "127.0.0.1"))
        self.port_text.SetValue(self.settings_manager.get_option("transceiver_port", "4532"))
        self.baud_choice.SetStringSelection(self.settings_manager.get_option("transceiver_baudrate", "9600"))
        self.auto_poll_checkbox.SetValue(self.settings_manager.get_bool("transceiver_auto_poll", False))
        self._populate_ports(self.settings_manager.get_option("transceiver_com_port", ""))
        if installed:
            try:
                self._populate_models(self.settings_manager.get_option("transceiver_model_id", ""))
            except Exception:
                self.model_choice.SetItems([])
        self._update_enabled_state()

    def _populate_ports(self, selected=""):
        values = [item[0] for item in list_serial_ports()]
        if selected and selected not in values:
            values.insert(0, selected)
        self.com_choice.SetItems(values)
        if selected in values:
            self.com_choice.SetStringSelection(selected)
        elif values:
            self.com_choice.SetSelection(0)

    def _populate_models(self, selected=""):
        models = list_hamlib_models()
        self._model_ids = [item[0] for item in models]
        self.model_choice.SetItems([f"{mid} — {name}" for mid, name in models])
        for index, model_id in enumerate(self._model_ids):
            if model_id == str(selected):
                self.model_choice.SetSelection(index)
                return
        if models:
            self.model_choice.SetSelection(0)

    def _update_enabled_state(self):
        installed = is_hamlib_installed()
        enabled = installed and self.use_checkbox.GetValue()
        local = enabled and self.connection_type.GetSelection() == 0
        self.use_checkbox.Enable(installed)
        self.connection_type.Enable(enabled)
        self.host_text.Enable(enabled and not local)
        self.port_text.Enable(enabled)
        self.model_choice.Enable(local)
        self.com_choice.Enable(local)
        self.baud_choice.Enable(local)
        self.auto_poll_checkbox.Enable(enabled)
        self.refresh_button.Enable(local)
        self.test_button.Enable(enabled)
        self.download_button.SetLabel(
            tr("transceiver.reinstall") if installed else tr("transceiver.download")
        )

    def on_use_toggle(self, event=None):
        self._update_enabled_state()

    def on_connection_type_change(self, event=None):
        self._update_enabled_state()

    def on_refresh_models(self, event=None):
        try:
            selected = self._model_ids[self.model_choice.GetSelection()] if self.model_choice.GetSelection() >= 0 else ""
            self._populate_models(selected)
            self._populate_ports(self.com_choice.GetStringSelection())
        except Exception as error:
            wx.MessageBox(tr("transceiver.models_error").format(error=error),
                          tr("error.title"), wx.OK | wx.ICON_ERROR, self)

    def is_busy(self):
        return self._download_in_progress

    def _set_dialog_busy(self, busy):
        dialog = self.GetParent().GetParent()
        for name in ("save_btn", "cancel_btn"):
            control = getattr(dialog, name, None)
            if control is not None:
                control.Enable(not busy)

    def on_download(self, event=None):
        self._download_in_progress = True
        self._set_dialog_busy(True)
        self.download_button.Disable()
        self.status_label.SetLabel(tr("transceiver.downloading"))

        def worker():
            try:
                result = download_latest_hamlib()
                wx.CallAfter(self._download_finished, result, None)
            except Exception as error:
                wx.CallAfter(self._download_finished, None, str(error))
        threading.Thread(target=worker, daemon=True).start()

    def _download_finished(self, result, error):
        self._download_in_progress = False
        self._set_dialog_busy(False)
        self.download_button.Enable()
        if error:
            self.status_label.SetLabel(tr("transceiver.download_error").format(error=error))
            self._update_enabled_state()
            return
        self.status_label.SetLabel(tr("transceiver.installed").format(version=result["version"]))
        try:
            self._populate_models()
            self._populate_ports()
        except Exception as model_error:
            self.status_label.SetLabel(
                tr("transceiver.installed_models_error").format(
                    version=result["version"], error=model_error
                )
            )
        self._update_enabled_state()

    def get_settings(self):
        index = self.model_choice.GetSelection()
        model_id = self._model_ids[index] if 0 <= index < len(self._model_ids) else ""
        return {
            "use_hamlib": "1" if self.use_checkbox.GetValue() else "0",
            "transceiver_connection": "remote" if self.connection_type.GetSelection() == 1 else "local",
            "transceiver_host": self.host_text.GetValue().strip() or "127.0.0.1",
            "transceiver_port": self.port_text.GetValue().strip() or "4532",
            "transceiver_model_id": model_id,
            "transceiver_com_port": self.com_choice.GetStringSelection(),
            "transceiver_baudrate": self.baud_choice.GetStringSelection() or "9600",
            "transceiver_auto_poll": "1" if self.auto_poll_checkbox.GetValue() else "0",
        }

    def on_test_connection(self, event=None):
        settings = self.get_settings()
        settings["use_hamlib"] = "1"
        self.test_button.Disable()

        def worker():
            controller = TransceiverController()
            try:
                controller.configure(settings)
                last_error = None
                snapshot = None
                for _attempt in range(20):
                    try:
                        snapshot = controller.get_snapshot()
                        break
                    except Exception as caught:
                        last_error = caught
                        if controller.process is not None and controller.process.poll() is not None:
                            break
                        time.sleep(0.25)
                if snapshot is None:
                    raise last_error or RuntimeError("No response from rigctld")
                result, error = snapshot, None
            except Exception as caught:
                result, error = None, str(caught)
            finally:
                controller.stop()
            wx.CallAfter(self._test_finished, result, error)
        threading.Thread(target=worker, daemon=True).start()

    def _test_finished(self, result, error):
        self.test_button.Enable()
        if error:
            self.status_label.SetLabel(tr("transceiver.test_failed").format(error=error))
        else:
            self.status_label.SetLabel(tr("transceiver.test_ok").format(
                frequency=result["frequency_hz"], mode=result["mode"],
                bandwidth=result["bandwidth"]
            ))
