"""ADIF export commands exposed through the application controller."""

from exporter import Exporter
from utils import Result
from logger import log_error


class ControllerExportMixin:
    def _get_exporter(self):
        exporter = getattr(self, "_exporter", None)
        if exporter is None:
            exporter = Exporter(self.qso_manager, self.settings_manager)
            self._exporter = exporter
        return exporter

    def export_to_adif(self, filepath):
        """Export the journal to an ADIF file without exposing Exporter to the GUI."""
        try:
            return self._get_exporter().export_to_adif(filepath)
        except Exception as error:
            log_error(f"ADIF export failed in controller: {error}")
            return Result(False, error=str(error))
