import json
import locale
import os
import sys

_translations = {}
_default_translations = {}
_current_lang = None


def _load_translation_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def load_translations(lang_code=None):
    global _translations, _default_translations, _current_lang

    base_path = os.path.join(os.path.dirname(__file__), "locales")

    # Загружаем английский (база)
    _default_translations = _load_translation_file(os.path.join(base_path, "en.json"))

    if lang_code and lang_code != "auto":
        _current_lang = lang_code
        _translations = _load_translation_file(os.path.join(base_path, f"{lang_code}.json"))
    else:
        _current_lang = "auto"
        # Определяем язык системы
        lang = locale.getlocale()[0] or ""

        if lang and lang.startswith("ru"):
            _translations = _load_translation_file(os.path.join(base_path, "ru.json"))
        else:
            _translations = {}

def _windows_ui_language():
    """Определяет язык интерфейса Windows через GetUserDefaultUILanguage.

    Возвращает 'ru'/'en' или None, если определить не удалось. Этот API
    читает язык интерфейса пользователя напрямую и не зависит от
    состояния локали процесса (wx.Locale может менять её после старта).
    """
    try:
        import ctypes
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        # Младшие 10 бит LANGID — primary language ID; 0x19 = LANG_RUSSIAN
        return 'ru' if lang_id & 0x3FF == 0x19 else 'en'
    except Exception:
        return None


def get_resolved_language():
    """Возвращает эффективный код языка интерфейса: 'ru' или 'en'.

    Явная настройка языка (не 'auto') имеет приоритет. При 'auto' язык
    определяется по системе: на Windows — через _windows_ui_language(),
    в остальных случаях — через locale.getlocale().
    """
    if _current_lang and _current_lang != 'auto':
        return _current_lang

    if sys.platform == 'win32':
        win_lang = _windows_ui_language()
        if win_lang:
            return win_lang

    lang = locale.getlocale()[0] or ''
    return 'ru' if lang.lower().startswith('ru') else 'en'


def get_available_languages():
    """Возвращает список кодов языков на основе файлов в папке locales/.
    Всегда начинается с 'auto', затем идут коды в алфавитном порядке."""
    base_path = os.path.join(os.path.dirname(__file__), "locales")
    codes = []
    try:
        for fname in sorted(os.listdir(base_path)):
            if fname.endswith(".json"):
                codes.append(fname[:-5])  # убираем .json
    except OSError:
        codes = ["en"]
    return ["auto"] + codes


def tr(key):
    if key in _translations:
        return _translations[key]
    return _default_translations.get(key, key)