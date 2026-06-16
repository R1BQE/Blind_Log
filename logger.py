"""
Централизованная система событийного логирования для Blind_Log.

Обеспечивает структурированное логирование ключевых событий приложения
с префиксами для удобного анализа и восстановления цепочки действий.
"""

import logging as log

# Глобальная переменная для проверки включения логирования
_enabled = False

def init_logger(settings_manager):
    """
    Инициализация логгера с проверкой настроек.

    Args:
        settings_manager: экземпляр SettingsManager
    """
    global _enabled
    try:
        _enabled = settings_manager.get_option('log_enabled', '0') == '1'
    except Exception:
        _enabled = False

def log_user_action(message: str):
    """
    Логирование действий пользователя (нажатия, команды, операции).

    Args:
        message: сообщение для логирования
    """
    if _enabled:
        log.info(f"[USER_ACTION] {message}")

def log_ui_state(message: str):
    """
    Логирование изменений интерфейса (фокус, окна, режимы).

    Args:
        message: сообщение для логирования
    """
    if _enabled:
        log.info(f"[UI_STATE] {message}")

def log_feedback(message: str):
    """
    Логирование сообщений, которые пользователь слышит через NVDA или UI.

    Args:
        message: сообщение для логирования
    """
    if _enabled:
        log.info(f"[FEEDBACK] {message}")

def log_error(message: str):
    """
    Логирование ошибок и исключений.

    Args:
        message: сообщение для логирования
    """
    if _enabled:
        log.error(f"[ERROR] {message}")

def log_debug(message: str):
    """
    Логирование технической отладки.

    Args:
        message: сообщение для логирования
    """
    if _enabled:
        log.debug(f"[DEBUG] {message}")