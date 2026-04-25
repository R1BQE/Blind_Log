import json
import locale
import os

_translations = {}
_default_translations = {}
_current_lang = None

def set_language(lang_code):
    global _translations, _default_translations, _current_lang

    _current_lang = lang_code

    base_path = os.path.join(os.path.dirname(__file__), "locales")

    # Загружаем английский (база)
    with open(os.path.join(base_path, "en.json"), "r", encoding="utf-8") as f:
        _default_translations = json.load(f)

    # Загружаем выбранный язык
    if lang_code != "auto":
        try:
            with open(os.path.join(base_path, f"{lang_code}.json"), "r", encoding="utf-8") as f:
                _translations = json.load(f)
        except:
            _translations = {}
    else:
        _translations = {}

def load_translations(lang_code=None):
    global _translations, _default_translations, _current_lang

    base_path = os.path.join(os.path.dirname(__file__), "locales")

    # Загружаем английский (база)
    with open(os.path.join(base_path, "en.json"), "r", encoding="utf-8") as f:
        _default_translations = json.load(f)

    if lang_code and lang_code != "auto":
        _current_lang = lang_code
        try:
            with open(os.path.join(base_path, f"{lang_code}.json"), "r", encoding="utf-8") as f:
                _translations = json.load(f)
        except:
            _translations = {}
    else:
        _current_lang = "auto"
        # Определяем язык системы
        lang = locale.getdefaultlocale()[0]

        if lang and lang.startswith("ru"):
            try:
                with open(os.path.join(base_path, "ru.json"), "r", encoding="utf-8") as f:
                    _translations = json.load(f)
            except:
                _translations = {}
        else:
            _translations = {}

def tr(key):
    if key in _translations:
        return _translations[key]
    return _default_translations.get(key, key)