"""Централизованное логирование Blind_Log."""

import logging
import os
import tempfile

_enabled = False
_log_dir = None


def _get_log_dir():
    """Prefer logs beside the executable; use the per-user directory if read-only."""
    try:
        from common.utils import get_app_path
        candidate = os.path.join(get_app_path(), "logs")
        os.makedirs(candidate, exist_ok=True)
        probe = os.path.join(candidate, ".write-test")
        with open(probe, "w", encoding="ascii") as stream:
            stream.write("ok")
        os.remove(probe)
        return candidate
    except (OSError, ImportError):
        base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        candidate = os.path.join(base, "BlindLog", "logs")
        os.makedirs(candidate, exist_ok=True)
        return candidate


def init_logger(settings_manager=None, log_path=None):
    """Configure application logging without preventing the app from starting."""
    global _enabled, _log_dir
    try:
        _enabled = (
            settings_manager is not None
            and str(settings_manager.get_option("log_enabled", "0")).lower()
            in ("1", "true", "yes")
        )
    except (AttributeError, TypeError, ValueError):
        _enabled = False

    try:
        _log_dir = _get_log_dir()
        target = log_path or os.path.join(_log_dir, "application.log")
        if _enabled:
            logging.basicConfig(
                filename=target,
                level=logging.DEBUG,
                format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                encoding="utf-8",
                force=True,
            )
        else:
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
                try:
                    handler.close()
                except OSError:
                    pass
    except OSError:
        _enabled = False


def _write_update_log(level, message, exc_info=False):
    """Updater diagnostics are kept separately from the optional app log."""
    try:
        directory = _log_dir or _get_log_dir()
        path = os.path.join(directory, "updater.log")
        logger = logging.getLogger("blind_log.updater.file")
        if not any(getattr(handler, "baseFilename", None) == os.path.abspath(path)
                   for handler in logger.handlers):
            handler = logging.FileHandler(path, encoding="utf-8")
            handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s"
            ))
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
            logger.propagate = False
        logger.log(level, message, exc_info=exc_info)
    except OSError:
        pass


def log_updater_action(message: str):
    _write_update_log(logging.INFO, "[ACTION] %s" % message)


def log_updater_error(message: str):
    _write_update_log(logging.ERROR, "[ERROR] %s" % message)


def log_updater_exception(message: str):
    _write_update_log(logging.ERROR, "[EXCEPTION] %s" % message, exc_info=True)


def log_updater_debug(message: str):
    _write_update_log(logging.DEBUG, "[DEBUG] %s" % message)


def log_user_action(message: str):
    if _enabled:
        logging.getLogger("blind_log.user").info("[USER_ACTION] %s", message)


def log_ui_state(message: str):
    if _enabled:
        logging.getLogger("blind_log.ui").info("[UI_STATE] %s", message)


def log_feedback(message: str):
    if _enabled:
        logging.getLogger("blind_log.feedback").info("[FEEDBACK] %s", message)


def log_error(message: str):
    if _enabled:
        logging.getLogger("blind_log").error("[ERROR] %s", message)


def log_exception(message: str):
    """Записать неожиданную ошибку вместе с traceback из текущего except."""
    if _enabled:
        logging.getLogger("blind_log").exception("[EXCEPTION] %s", message)


def log_debug(message: str):
    if _enabled:
        logging.getLogger("blind_log").debug("[DEBUG] %s", message)
