import json
import locale
import os

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
        lang = locale.getdefaultlocale()[0] if locale.getdefaultlocale() else None

        if lang and lang.startswith("ru"):
            _translations = _load_translation_file(os.path.join(base_path, "ru.json"))
        else:
            _translations = {}

def tr(key):
    if key in _translations:
        return _translations[key]
    return _default_translations.get(key, key)