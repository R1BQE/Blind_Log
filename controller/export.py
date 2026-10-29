"""ADIF export commands exposed through the application controller."""

from adif.exporter import Exporter
from common.utils import Result
from logger import log_error


class ControllerExportMixin:
    def _get_exporter(self):
        exporter = getattr(self, "_exporter", None)
        if exporter is None:
            exporter = Exporter(self.qso_manager, self.settings_manager)
            self._exporter = exporter
        return exporter

    def export_to_adif(self, filepath, qsos=None):
        """Export the whole journal or a supplied list of QSO records."""
        try:
            return self._get_exporter().export_to_adif(filepath, qsos=qsos)
        except Exception as error:
            log_error(f"ADIF export failed in controller: {error}")
            return Result(False, error=str(error))
