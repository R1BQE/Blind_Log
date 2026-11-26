"""Keyboard and polling integration for the optional CAT subsystem."""
import threading
import wx

from localization.i18n import tr
from logger import log_error
from services.transceiver import (
    TransceiverController, frequency_to_mhz, normalize_mode_for_log,
)


class TransceiverMixin:
    def _init_transceiver(self):
        self._transceiver = TransceiverController()
        self._transceiver_request_pending = False
        self._transceiver_last_frequency = None
        self._transceiver_last_mode = None
        self._transceiver_last_error = None
        self._transceiver_poll_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_transceiver_poll, self._transceiver_poll_timer)
        self._configure_transceiver()

    def _configure_transceiver(self):
        if hasattr(self, "_transceiver_poll_timer"):
            self._transceiver_poll_timer.Stop()
        if not hasattr(self, "_transceiver"):
            self._transceiver = TransceiverController()
        try:
            self._transceiver.configure(self.settings_manager.settings)
            if (self.settings_manager.get_bool("use_hamlib", False)
                    and self.settings_manager.get_bool("transceiver_auto_poll", False)):
                self._transceiver_poll_timer.Start(1000)
        except Exception as error:
            log_error(f"Could not configure transceiver: {error}")
            self.gui_bridge.show_notification(
                tr("transceiver.connection_error").format(error=error)
            )

    def _stop_transceiver(self):
        timer = getattr(self, "_transceiver_poll_timer", None)
        if timer is not None:
            timer.Stop()
        controller = getattr(self, "_transceiver", None)
        if controller is not None:
            controller.stop()

    def _on_transceiver_poll(self, event=None):
        if self._transceiver_request_pending or not self._transceiver.is_configured():
            return
        self._transceiver_request_pending = True
        self._request_transceiver_data("snapshot", polling=True)

    def on_transceiver_frequency(self, event=None):
        if not self._transceiver.is_configured():
            self.gui_bridge.show_notification(tr("transceiver.not_enabled"))
            return
        self._request_transceiver_data("frequency", announce=True)

    def on_transceiver_mode(self, event=None):
        if not self._transceiver.is_configured():
            self.gui_bridge.show_notification(tr("transceiver.not_enabled"))
            return
        self._request_transceiver_data("mode", announce=True)

    def _request_transceiver_data(self, kind, announce=False, polling=False):
        if not self._transceiver.is_configured():
            if polling:
                self._transceiver_request_pending = False
            elif announce:
                self.gui_bridge.show_notification(tr("transceiver.not_enabled"))
            return

        def worker():
            try:
                result = (self._transceiver.get_frequency() if kind == "frequency"
                          else self._transceiver.get_mode() if kind == "mode"
                          else self._transceiver.get_snapshot())
                error = None
            except Exception as caught:
                result, error = None, str(caught)
            wx.CallAfter(self._finish_transceiver_request, kind, result, error, announce, polling)
        threading.Thread(target=worker, daemon=True).start()

    def _finish_transceiver_request(self, kind, result, error, announce=False, polling=False):
        if polling:
            self._transceiver_request_pending = False
        if error:
            if error != self._transceiver_last_error:
                self._transceiver_last_error = error
                if announce or polling:
                    self.gui_bridge.show_notification(
                        tr("transceiver.connection_error").format(error=error)
                    )
            return
        if self._transceiver_last_error is not None:
            self._transceiver_last_error = None
            if polling:
                self.gui_bridge.show_notification(tr("transceiver.connection_restored"))
        if kind == "frequency":
            self._apply_transceiver_frequency(result, announce, polling)
        elif kind == "mode":
            self._apply_transceiver_mode(result, announce, polling)
        else:
            self._apply_transceiver_frequency(result["frequency_hz"], False, polling)
            self._apply_transceiver_mode(result, False, polling)

    def _apply_transceiver_frequency(self, frequency_hz, announce=False, polling=False):
        value = frequency_to_mhz(frequency_hz)
        previous = self._transceiver_last_frequency
        control = self.controls.get("freq")
        if control is not None and control.IsShown():
            current = control.GetValue().strip()
            safe = (not polling or (
                not control.HasFocus() and (not current or current == previous)
            ))
            if safe:
                self._suppress_draft_changes = True
                try:
                    control.SetValue(value)
                finally:
                    self._suppress_draft_changes = False
        self._transceiver_last_frequency = value
        if announce or (polling and previous is not None and previous != value):
            self.gui_bridge.show_notification(
                tr("transceiver.frequency_announcement").format(frequency=value)
            )

    def _apply_transceiver_mode(self, data, announce=False, polling=False):
        mode, bandwidth = str(data.get("mode", "")).upper(), int(data.get("bandwidth", 0) or 0)
        previous = self._transceiver_last_mode
        control = self.controls.get("mode")
        mapped = normalize_mode_for_log(mode)
        if control is not None and mapped:
            current = control.GetStringSelection()
            safe = (not polling or (
                not control.HasFocus() and (
                    previous is None or not current
                    or current == normalize_mode_for_log(previous)
                )
            ))
            if safe:
                self._suppress_draft_changes = True
                try:
                    control.SetStringSelection(mapped)
                finally:
                    self._suppress_draft_changes = False
        self._transceiver_last_mode = mode
        if announce or (polling and previous is not None and previous != mode):
            width = (tr("transceiver.bandwidth_unknown") if bandwidth <= 0
                     else f"{bandwidth} {tr('transceiver.hz')}")
            self.gui_bridge.show_notification(
                tr("transceiver.mode_announcement").format(mode=mode, bandwidth=width)
            )
