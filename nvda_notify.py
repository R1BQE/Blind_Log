# nvda_notify.py
"""
Module for speaking messages through screen readers using accessible-output3.
Supports NVDA, JAWS, Window Eyes, System Access, Supernova and other screen readers.
"""
import wx
from logger import log_feedback, log_error

try:
    from accessible_output3.outputs.auto import Auto
    _speaker = Auto()
    _available = True
except Exception as e:
    log_error(f"accessible-output3 initialization error: {e}")
    _speaker = None
    _available = False


def nvda_notify(message: str, interrupt: bool = True):
    """
    Speak a message through the active screen reader.
    Falls back to wx.adv.NotificationMessage if no screen reader is available.
    """
    log_feedback(message)
    print(f"NVDA_NOTIFY: {message}")

    if _available and _speaker:
        try:
            _speaker.speak(message, interrupt=interrupt)
        except Exception as e:
            log_error(f"accessible-output3 speak error: {e}")
            _fallback_notify(message)
    else:
        _fallback_notify(message)


def _fallback_notify(message: str):
    """Fallback to wx notification if screen reader is unavailable."""
    try:
        wx.adv.NotificationMessage("Blind_Log", message).Show()
    except Exception as e:
        log_error(f"Fallback notification error: {e}")


# Backward compatibility: nvda_controller.speak(message) still works
class _CompatController:
    def speak(self, message: str, interrupt: bool = True):
        nvda_notify(message, interrupt=interrupt)


nvda_controller = _CompatController()
