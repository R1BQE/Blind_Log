"""Draft operations exposed through the application controller."""

from constants import BANDS, MODES, DEFAULT_BAND_INDEX, DEFAULT_MODE_INDEX
from utils import Result
from logger import log_error


class ControllerDraftMixin:
    def is_editing(self):
        """Return whether the journal currently has a QSO open for editing."""
        return self.qso_manager.is_editing()

    @staticmethod
    def _draft_is_meaningful(fields):
        meaningful = any(
            str(fields.get(key, "")).strip()
            for key in ("call", "name", "city", "qth", "freq", "comment")
        )
        meaningful = meaningful or any(
            str(fields.get(key, "")).strip() not in ("", "59")
            for key in ("rst_received", "rst_sent")
        )
        meaningful = meaningful or fields.get("band", "") != BANDS[DEFAULT_BAND_INDEX]
        meaningful = meaningful or fields.get("mode", "") != MODES[DEFAULT_MODE_INDEX]
        return meaningful

    def save_draft(self, fields):
        """Save a meaningful unfinished form, or clear an effectively empty draft."""
        if self.is_editing():
            return Result(False, error="Cannot save a draft while editing a journal entry")
        try:
            if not self._draft_is_meaningful(fields):
                result = self.qso_manager.clear_draft()
                if result.success:
                    result.data = {"saved": False}
                return result
            result = self.qso_manager.save_draft(fields)
            if result.success:
                result.data = {"saved": True}
            return result
        except Exception as error:
            log_error(f"QSO draft save failed in controller: {error}")
            return Result(False, error=str(error))

    def load_draft(self):
        """Load the unfinished form draft through the controller."""
        try:
            return self.qso_manager.load_draft()
        except Exception as error:
            log_error(f"QSO draft load failed in controller: {error}")
            return None

    def clear_draft(self):
        """Clear the unfinished form draft through the controller."""
        try:
            return self.qso_manager.clear_draft()
        except Exception as error:
            log_error(f"QSO draft clear failed in controller: {error}")
            return Result(False, error=str(error))
