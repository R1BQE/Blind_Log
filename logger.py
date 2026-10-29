"""Централизованное логирование Blind_Log."""

import logging

_enabled = False


def init_logger(settings_manager=None, log_path="blind_log.log"):
    """Настроить единый файловый логгер приложения.

    При ошибке настройки логирования приложение продолжает запуск, но ошибка
    настройки не маскируется под успешно включённое логирование.
    """
    global _enabled
    try:
        _enabled = (
            settings_manager is not None
            and str(settings_manager.get_option("log_enabled", "0")).lower()
            in ("1", "true", "yes")
        )
    except (AttributeError, TypeError, ValueError):
        _enabled = False

    if _enabled:
        logging.basicConfig(
            filename=log_path,
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
